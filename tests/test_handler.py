import json
from datetime import timedelta
from typing import Any

import pytest

from app.application.exceptions.delivery import InvalidMessage
from app.application.use_cases.send_confirmation_code import SendConfirmationCode
from app.infrastructure.templates.renderer import TemplateRenderer
from app.presentation.messaging.handler import MessageHandler
from tests.conftest import NOW, FixedClock, Outbox


def message(**changes: Any) -> bytes:
    """A message as the identity service publishes it."""
    body = {
        "type": "confirmation_code",
        "version": 1,
        "id": "3f1c…",
        "to": "Player@Example.com",
        "purpose": "verify_email",
        "code": "042137",
        "created_at": NOW.isoformat(),
        "expires_in_minutes": 10,
        **changes,
    }
    return json.dumps({k: v for k, v in body.items() if v is not None}).encode()


@pytest.fixture
def handler(outbox: Outbox, clock: FixedClock) -> MessageHandler:
    renderer = TemplateRenderer("Balatro", "https://example.com")
    return MessageHandler(SendConfirmationCode(renderer, outbox, clock))


@pytest.mark.anyio
async def test_a_confirmation_code(handler: MessageHandler, outbox: Outbox) -> None:
    await handler("email.confirmation_code", message(), "3f1c…")
    [email] = outbox.sent
    assert email.to.value == "player@example.com"
    assert "042137" in email.text


@pytest.mark.anyio
async def test_unknown_fields_are_ignored(
    handler: MessageHandler, outbox: Outbox
) -> None:
    await handler("email.confirmation_code", message(locale="fr"), None)
    assert len(outbox.sent) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"[1, 2]",
        b"\xff\xfe",
        message(type="newsletter"),
        message(version=2),
        message(purpose="welcome"),
        message(code="12345"),
        message(code="abcdef"),
        message(to="not an email"),
        message(created_at="2026-10-25T12:00:00"),  # no timezone
        message(expires_in_minutes=0),
        message(id=None),
    ],
)
async def test_invalid_messages(handler: MessageHandler, body: bytes) -> None:
    with pytest.raises(InvalidMessage):
        await handler("email.confirmation_code", body, None)


@pytest.mark.anyio
async def test_an_expired_message_is_dropped(
    handler: MessageHandler, outbox: Outbox, clock: FixedClock
) -> None:
    clock.at = NOW + timedelta(hours=1)
    await handler("email.confirmation_code", message(), None)  # (no error: done)
    assert outbox.sent == []
