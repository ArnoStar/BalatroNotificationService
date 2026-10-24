class NotificationError(Exception):
    """An error of a use case, with a stable ``code``."""

    code = "notification_error"
    message = "notification error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
