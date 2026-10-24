from dataclasses import dataclass

from app.domain.value_object.email import Email


@dataclass(frozen=True)
class EmailMessage:
    """An email ready to send: a plain text body, and the same as HTML."""

    to: Email
    subject: str
    text: str
    html: str
