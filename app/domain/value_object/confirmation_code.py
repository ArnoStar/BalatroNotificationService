import re
from dataclasses import dataclass
from enum import StrEnum

from app.domain.exceptions import InvalidCode

_CODE = re.compile(r"^\d{6}$")


class CodePurpose(StrEnum):
    """Why a code is sent (the identity service's purposes)."""

    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"


@dataclass(frozen=True)
class ConfirmationCode:
    """The six digits the identity service made. This service only shows it."""

    value: str

    def __post_init__(self) -> None:
        if not _CODE.match(self.value):
            raise InvalidCode("a confirmation code is six digits")

    def __repr__(self) -> str:
        return "ConfirmationCode(***)"
