from dataclasses import dataclass

from app.domain.exceptions import InvalidEmail

MAX_LENGTH = 320


@dataclass(frozen=True)
class Email:
    """An email address, trimmed and lower case (as the identity service
    stores it)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        local, at, domain = normalized.rpartition("@")
        if (
            not at
            or not local
            or "." not in domain
            or len(normalized) > MAX_LENGTH
            or any(c.isspace() or c in '<>,;"' for c in normalized)
        ):
            raise InvalidEmail("invalid email address")
        object.__setattr__(self, "value", normalized)
