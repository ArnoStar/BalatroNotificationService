class DomainError(Exception):
    """A value that breaks a rule of the domain. ``code`` is stable."""

    code = "invalid_value"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidEmail(DomainError):
    code = "invalid_email"


class InvalidCode(DomainError):
    code = "invalid_code"
