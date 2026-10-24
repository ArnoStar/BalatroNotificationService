from app.application.exceptions.base import NotificationError


class DeliveryFailed(NotificationError):
    """For now: the mail server is down or refused for a while. The message is
    tried again later."""

    code = "delivery_failed"
    message = "the email could not be sent now"


class InvalidMessage(NotificationError):
    """For good: the message can't be understood or delivered (bad JSON, an
    unknown version, an address the mail server refuses). It is set aside, not
    tried again."""

    code = "invalid_message"
    message = "the message can't be handled"


class UndeliverableEmail(InvalidMessage):
    code = "undeliverable_email"
    message = "the mail server refuses this address"
