"""The exchanges and queues (declared by this service when it starts):

    notifications (direct)       the other services publish here
      └─ email.confirmation_code → notification.email
    notification.email           consumed; a message rejected for now goes to
      └─ (dead letter)           → notifications.retry
    notifications.retry (direct)
      └─ email.confirmation_code → notification.email.retry
    notification.email.retry     waits RETRY_DELAY_SECONDS (message TTL), then
      └─ (dead letter)           → notifications, its routing key unchanged
    notification.email.failed    messages set aside: invalid, or failed
                                 MAX_ATTEMPTS times (look, fix, move them back)

A publisher declares only ``notifications`` (durable, direct) and publishes
with ``mandatory``: if this service never ran, nothing is bound and the
publisher learns it. Changing a queue's arguments needs the queue deleted
first (RabbitMQ refuses to redeclare it differently).
"""

from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

EXCHANGE = "notifications"
RETRY_EXCHANGE = "notifications.retry"
QUEUE = "notification.email"
RETRY_QUEUE = "notification.email.retry"
FAILED_QUEUE = "notification.email.failed"

CONFIRMATION_CODE = "email.confirmation_code"
ROUTING_KEYS = (CONFIRMATION_CODE,)


async def declare(
    channel: AbstractChannel, retry_delay_seconds: int
) -> tuple[AbstractQueue, AbstractExchange]:
    """Declares everything; returns the queue to consume, and the default
    exchange (to set messages aside in the failed queue)."""
    exchange = await channel.declare_exchange(
        EXCHANGE, ExchangeType.DIRECT, durable=True
    )
    retry_exchange = await channel.declare_exchange(
        RETRY_EXCHANGE, ExchangeType.DIRECT, durable=True
    )
    queue = await channel.declare_queue(
        QUEUE, durable=True, arguments={"x-dead-letter-exchange": RETRY_EXCHANGE}
    )
    retry_queue = await channel.declare_queue(
        RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": retry_delay_seconds * 1000,
            "x-dead-letter-exchange": EXCHANGE,
        },
    )
    await channel.declare_queue(FAILED_QUEUE, durable=True)
    for key in ROUTING_KEYS:
        await queue.bind(exchange, routing_key=key)
        await retry_queue.bind(retry_exchange, routing_key=key)
    return queue, channel.default_exchange
