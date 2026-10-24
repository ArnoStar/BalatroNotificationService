import logging
import math
from datetime import timedelta

from app.application.dtos.confirmation_code import SendConfirmationCodeInput, SendResult
from app.application.ports.clock import Clock
from app.application.ports.email_renderer import EmailRenderer
from app.application.ports.email_sender import EmailSender

log = logging.getLogger(__name__)


class SendConfirmationCode:
    """Emails a confirmation code the identity service made (to confirm an
    email, or to reset a password). A code that expired before it could be
    sent (the mail server was down for a while) is dropped: it would not work."""

    def __init__(
        self,
        renderer: EmailRenderer,
        email_sender: EmailSender,
        clock: Clock,
    ) -> None:
        self.renderer = renderer
        self.email_sender = email_sender
        self.clock = clock

    async def execute(self, dto: SendConfirmationCodeInput) -> SendResult:
        expires_at = dto.created_at + timedelta(minutes=dto.expires_in_minutes)
        seconds_left = (expires_at - self.clock.now()).total_seconds()

        if seconds_left <= 0:
            log.warning(
                "message %s: the code expired before it was sent", dto.message_id
            )
            return SendResult.EXPIRED

        message = self.renderer.confirmation_code(
            to=dto.to,
            purpose=dto.purpose,
            code=dto.code,
            minutes_left=max(1, math.ceil(seconds_left / 60)),
        )
        await self.email_sender.send(message)
        log.info("message %s: %s code sent", dto.message_id, dto.purpose)
        return SendResult.SENT
