"""The consumer against a real RabbitMQ (RABBITMQ_TEST_URL, e.g.
amqp://guest:guest@localhost:5672/). It deletes and redeclares this service's
queues: never point it at a broker in use."""

import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import aio_pika
import pytest

from app.application.exceptions.delivery import DeliveryFailed
from app.application.use_cases.send_confirmation_code import SendConfirmationCode
from app.infrastructure.clock import SystemClock
from app.infrastructure.rabbitmq import topology
from app.infrastructure.rabbitmq.consumer import RabbitMqConsumer
from app.infrastructure.templates.renderer import TemplateRenderer
from app.presentation.messaging.handler import MessageHandler
from tests.conftest import Outbox

URL = os.environ.get("RABBITMQ_TEST_URL")
pytestmark = [
    pytest.mark.rabbitmq,
    pytest.mark.skipif(not URL, reason="needs RABBITMQ_TEST_URL"),
    pytest.mark.anyio,
]


@pytest.fixture
async def broker() -> AsyncIterator[aio_pika.abc.AbstractChannel]:
    assert URL
    connection = await aio_pika.connect_robust(URL)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    for queue in (topology.QUEUE, topology.RETRY_QUEUE, topology.FAILED_QUEUE):
        await channel.queue_delete(queue)
    yield channel
    await connection.close()


async def start(outbox: Outbox, max_attempts: int = 2) -> RabbitMqConsumer:
    assert URL
    handler = MessageHandler(
        SendConfirmationCode(
            TemplateRenderer("Balatro", "https://example.com"), outbox, SystemClock()
        )
    )
    consumer = RabbitMqConsumer(
        URL, handler, retry_delay_seconds=1, max_attempts=max_attempts
    )
    await consumer.start()
    return consumer


async def publish(channel: aio_pika.abc.AbstractChannel, body: bytes) -> None:
    """As the identity service does (declare the exchange, mandatory)."""
    exchange = await channel.declare_exchange(
        topology.EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
    )
    await exchange.publish(
        aio_pika.Message(
            body=body,
            content_type="application/json",
            message_id=str(uuid.uuid4()),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=topology.CONFIRMATION_CODE,
        mandatory=True,
    )


def code_message(code: str = "042137") -> bytes:
    return json.dumps(
        {
            "type": "confirmation_code",
            "version": 1,
            "id": str(uuid.uuid4()),
            "to": "player@example.com",
            "purpose": "verify_email",
            "code": code,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_in_minutes": 10,
        }
    ).encode()


async def until(condition: object, seconds: float = 10) -> None:
    for _ in range(int(seconds * 20)):
        if condition():  # type: ignore[operator]
            return
        await asyncio.sleep(0.05)
    raise AssertionError("timed out")


async def failed_messages(
    channel: aio_pika.abc.AbstractChannel,
) -> list[aio_pika.abc.AbstractIncomingMessage]:
    queue = await channel.declare_queue(topology.FAILED_QUEUE, durable=True)
    found = []
    while (message := await queue.get(fail=False)) is not None:
        await message.ack()
        found.append(message)
    return found


async def test_a_code_is_sent(broker: aio_pika.abc.AbstractChannel) -> None:
    outbox = Outbox()
    consumer = await start(outbox)
    try:
        await publish(broker, code_message())
        await until(lambda: outbox.sent)
        assert "042137" in outbox.sent[0].text
    finally:
        await consumer.close()


async def test_retried_then_sent(broker: aio_pika.abc.AbstractChannel) -> None:
    outbox = Outbox(fail=DeliveryFailed())
    consumer = await start(outbox, max_attempts=5)
    try:
        await publish(broker, code_message())
        await asyncio.sleep(0.5)
        assert outbox.sent == []
        outbox.fail = None  # the mail server is back
        await until(lambda: outbox.sent, seconds=5)
    finally:
        await consumer.close()


async def test_set_aside_after_the_last_attempt(
    broker: aio_pika.abc.AbstractChannel,
) -> None:
    outbox = Outbox(fail=DeliveryFailed())
    consumer = await start(outbox, max_attempts=2)
    try:
        await publish(broker, code_message())
        await asyncio.sleep(3)
        [message] = await failed_messages(broker)
        assert "failed 2 times" in str(message.headers["x-failure-reason"])
        assert message.headers["x-original-routing-key"] == topology.CONFIRMATION_CODE
        assert json.loads(message.body)["code"] == "042137"
    finally:
        await consumer.close()


async def test_an_invalid_message_is_set_aside_at_once(
    broker: aio_pika.abc.AbstractChannel,
) -> None:
    outbox = Outbox()
    consumer = await start(outbox)
    try:
        await publish(broker, b'{"type": "confirmation_code", "version": 9}')
        await asyncio.sleep(0.5)
        [message] = await failed_messages(broker)
        assert "invalid" in str(message.headers["x-failure-reason"])
        assert outbox.sent == []
    finally:
        await consumer.close()


async def test_nothing_bound_is_refused_to_the_publisher(
    broker: aio_pika.abc.AbstractChannel,
) -> None:
    # (the queues were just deleted and no consumer declared them)
    with pytest.raises(aio_pika.exceptions.DeliveryError):
        await publish(broker, code_message())
