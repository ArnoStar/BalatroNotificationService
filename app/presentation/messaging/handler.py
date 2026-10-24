import json
from typing import Any

from pydantic import ValidationError

from app.application.dtos.confirmation_code import SendConfirmationCodeInput
from app.application.exceptions.delivery import InvalidMessage
from app.application.use_cases.send_confirmation_code import SendConfirmationCode
from app.domain.exceptions import DomainError
from app.domain.value_object.confirmation_code import CodePurpose, ConfirmationCode
from app.domain.value_object.email import Email
from app.presentation.messaging.schemas import ConfirmationCodeMessageV1


class MessageHandler:
    """Turns a message into a use case's input, by its ``type``. A message that
    can't be understood raises InvalidMessage (it is set aside, not retried)."""

    def __init__(self, send_confirmation_code: SendConfirmationCode) -> None:
        self.send_confirmation_code = send_confirmation_code

    async def __call__(
        self, routing_key: str, body: bytes, message_id: str | None
    ) -> None:
        data = self._json(body)
        kind = data.get("type")
        if kind == "confirmation_code":
            await self.send_confirmation_code.execute(self._confirmation_code(data))
        else:
            raise InvalidMessage(f"unknown message type {kind!r} ({routing_key})")

    @staticmethod
    def _json(body: bytes) -> dict[str, Any]:
        try:
            data = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidMessage("the body isn't JSON") from exc
        if not isinstance(data, dict):
            raise InvalidMessage("the body isn't a JSON object")
        return data

    @staticmethod
    def _confirmation_code(data: dict[str, Any]) -> SendConfirmationCodeInput:
        try:
            message = ConfirmationCodeMessageV1.model_validate(data)
            return SendConfirmationCodeInput(
                message_id=message.id,
                to=Email(message.to),
                purpose=CodePurpose(message.purpose),
                code=ConfirmationCode(message.code),
                created_at=message.created_at,
                expires_in_minutes=message.expires_in_minutes,
            )
        except ValidationError as exc:
            fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
            raise InvalidMessage(
                f"invalid confirmation_code message: {fields}"
            ) from exc
        except DomainError as exc:
            raise InvalidMessage(exc.message) from exc
