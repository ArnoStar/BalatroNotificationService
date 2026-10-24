from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from app.application.exceptions.delivery import DeliveryFailed, InvalidMessage
from app.domain.entities.email_message import EmailMessage

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@dataclass
class Outbox:
    """An email sender that keeps the emails; ``fail`` makes it fail."""

    sent: list[EmailMessage] = field(default_factory=list)
    fail: Exception | None = None

    async def send(self, message: EmailMessage) -> None:
        if self.fail is not None:
            raise self.fail
        self.sent.append(message)


@dataclass
class FixedClock:
    at: datetime = NOW

    def now(self) -> datetime:
        return self.at


@pytest.fixture
def outbox() -> Outbox:
    return Outbox()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


__all__ = ["NOW", "DeliveryFailed", "FixedClock", "InvalidMessage", "Outbox"]
