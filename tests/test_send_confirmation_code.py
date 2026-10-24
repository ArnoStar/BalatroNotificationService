from datetime import timedelta

import pytest

from app.application.dtos.confirmation_code import SendConfirmationCodeInput, SendResult
from app.application.exceptions.delivery import DeliveryFailed
from app.application.use_cases.send_confirmation_code import SendConfirmationCode
from app.domain.value_object.confirmation_code import CodePurpose, ConfirmationCode
from app.domain.value_object.email import Email
from app.infrastructure.templates.renderer import TemplateRenderer
from tests.conftest import NOW, FixedClock, Outbox


def use_case(outbox: Outbox, clock: FixedClock) -> SendConfirmationCode:
    return SendConfirmationCode(
        TemplateRenderer("Balatro", "https://balatro.example"), outbox, clock
    )


def dto(purpose: CodePurpose = CodePurpose.VERIFY_EMAIL) -> SendConfirmationCodeInput:
    return SendConfirmationCodeInput(
        message_id="m1",
        to=Email("player@example.com"),
        purpose=purpose,
        code=ConfirmationCode("042137"),
        created_at=NOW,
        expires_in_minutes=10,
    )


@pytest.mark.anyio
async def test_sends_the_code(outbox: Outbox, clock: FixedClock) -> None:
    assert await use_case(outbox, clock).execute(dto()) is SendResult.SENT
    [email] = outbox.sent
    assert email.to.value == "player@example.com"
    assert email.subject == "042137 is your Balatro confirmation code"
    assert "042137" in email.text and "042137" in email.html
    assert "10 minutes" in email.text


@pytest.mark.anyio
async def test_says_how_long_is_left(outbox: Outbox, clock: FixedClock) -> None:
    clock.at = NOW + timedelta(minutes=9, seconds=30)  # (retried for a while)
    await use_case(outbox, clock).execute(dto(CodePurpose.RESET_PASSWORD))
    [email] = outbox.sent
    assert "1 minute." in email.text
    assert email.subject == "042137 is your Balatro password reset code"
    assert "ignore this email" in email.text


@pytest.mark.anyio
async def test_an_expired_code_is_not_sent(outbox: Outbox, clock: FixedClock) -> None:
    clock.at = NOW + timedelta(minutes=10)
    assert await use_case(outbox, clock).execute(dto()) is SendResult.EXPIRED
    assert outbox.sent == []


@pytest.mark.anyio
async def test_a_failed_delivery_is_raised(outbox: Outbox, clock: FixedClock) -> None:
    outbox.fail = DeliveryFailed()
    with pytest.raises(DeliveryFailed):
        await use_case(outbox, clock).execute(dto())
