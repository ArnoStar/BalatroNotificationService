from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.value_object.confirmation_code import CodePurpose, ConfirmationCode
from app.domain.value_object.email import Email


@dataclass(frozen=True)
class SendConfirmationCodeInput:
    message_id: str
    to: Email
    purpose: CodePurpose
    code: ConfirmationCode
    created_at: datetime
    expires_in_minutes: int


class SendResult(StrEnum):
    SENT = "sent"
    EXPIRED = "expired"  # the code stopped working before it could be sent
