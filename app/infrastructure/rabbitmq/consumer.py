import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika.abc import (
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractRobustConnection,
)

from app.application.exceptions.delivery import DeliveryFailed, InvalidMessage
from app.infrastructure.rabbitmq import topology

log = logging.getLogger(__name__)

# what to do with a message: (routing key, body, message id); raises
# InvalidMessage (set aside) or DeliveryFailed (try again later)
Handler = Callable[[str, bytes, str | None], Awaitable[None]]


class RabbitMqConsumer:
    """Consumes ``notification.email`` and gives each message to the handler.

    - handled: acknowledged;
    - ``DeliveryFailed`` (or a bug): rejected, so it waits in the retry queue
      and comes back; after ``max_attempts`` it goes to the failed queue;
    - ``InvalidMessage``: to the failed queue at once.

    Delivery is at least once: a message may be handled twice (a crash before
    the acknowledgement), so an email may be sent twice."""

    def __init__(
        self,
        url: str,
        handler: Handler,
        prefetch: int = 10,
        retry_delay_seconds: int = 30,
        max_attempts: int = 5,
    ) -> None:
        self.url = url
        self.handler = handler
        self.prefetch = prefetch
        self.retry_delay_seconds = retry_delay_seconds
        self.max_attempts = max_attempts
        self._connection: AbstractRobustConnection | None = None
        self._default_exchange: AbstractExchange | None = None
        self._consuming = False

    @property
    def healthy(self) -> bool:
        return (
            self._consuming
            and self._connection is not None
            and not self._connection.is_closed
        )

    async def start(self) -> None:
        """Connects (retrying until RabbitMQ answers), declares the topology
        and starts consuming. The connection reconnects by itself afterwards."""
        delay = 1.0
        while True:
            try:
                self._connection = await aio_pika.connect_robust(self.url)
                break
            except (OSError, aio_pika.exceptions.AMQPError) as exc:
                log.warning("RabbitMQ not reachable (%r), again in %.0f s", exc, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=self.prefetch)
        queue, self._default_exchange = await topology.declare(
            channel, self.retry_delay_seconds
        )
        await queue.consume(self._on_message)
        self._consuming = True
        log.info("consuming %s", topology.QUEUE)

    async def close(self) -> None:
        self._consuming = False
        if self._connection is not None:
            await self._connection.close()

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        routing_key = message.routing_key or ""
        try:
            await self.handler(routing_key, message.body, message.message_id)
        except InvalidMessage as exc:
            log.error("message %s set aside: %s", message.message_id, exc.message)
            await self._set_aside(message, exc.message)
            await message.ack()
        except Exception as exc:  # noqa: BLE001 (DeliveryFailed, or a bug: retry)
            attempts = self.attempts(message) + 1
            if not isinstance(exc, DeliveryFailed):
                log.exception("message %s: unexpected error", message.message_id)
            if attempts >= self.max_attempts:
                log.error(
                    "message %s failed %d times, set aside",
                    message.message_id,
                    attempts,
                )
                await self._set_aside(message, f"failed {attempts} times: {exc!r}")
                await message.ack()
            else:
                log.warning(
                    "message %s failed (attempt %d of %d), again in %d s",
                    message.message_id,
                    attempts,
                    self.max_attempts,
                    self.retry_delay_seconds,
                )
                await message.reject(requeue=False)
        else:
            await message.ack()

    @staticmethod
    def attempts(message: AbstractIncomingMessage) -> int:
        """How many times this message was rejected from the queue already
        (RabbitMQ counts it in the ``x-death`` header)."""
        deaths: Any = (message.headers or {}).get("x-death") or []
        return sum(
            int(death.get("count", 0))
            for death in deaths
            if isinstance(death, dict)
            and death.get("queue") == topology.QUEUE
            and death.get("reason") == "rejected"
        )

    async def _set_aside(self, message: AbstractIncomingMessage, reason: str) -> None:
        assert self._default_exchange is not None
        headers = dict(message.headers or {})
        headers.pop("x-death", None)
        headers["x-failure-reason"] = reason[:500]
        headers["x-original-routing-key"] = message.routing_key or ""
        await self._default_exchange.publish(
            aio_pika.Message(
                body=message.body,
                headers=headers,
                content_type=message.content_type,
                message_id=message.message_id,
                type=message.type,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=topology.FAILED_QUEUE,
        )
