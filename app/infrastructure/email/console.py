import logging

from app.application.ports.email_sender import EmailSender
from app.domain.entities.email_message import EmailMessage

log = logging.getLogger("notification.email")


class ConsoleEmailSender(EmailSender):
    """Development: the email (its text part) goes to the log."""

    async def send(self, message: EmailMessage) -> None:
        log.warning(
            "email to %s: %s\n%s", message.to.value, message.subject, message.text
        )
