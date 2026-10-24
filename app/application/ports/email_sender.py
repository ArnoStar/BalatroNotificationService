from typing import Protocol

from app.domain.entities.email_message import EmailMessage


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None:
        """Raises DeliveryFailed (try again later) or UndeliverableEmail."""
        ...
