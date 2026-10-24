from typing import Protocol

from app.domain.entities.email_message import EmailMessage
from app.domain.value_object.confirmation_code import CodePurpose, ConfirmationCode
from app.domain.value_object.email import Email


class EmailRenderer(Protocol):
    """The emails' words and looks (templates)."""

    def confirmation_code(
        self,
        to: Email,
        purpose: CodePurpose,
        code: ConfirmationCode,
        minutes_left: int,
    ) -> EmailMessage: ...
