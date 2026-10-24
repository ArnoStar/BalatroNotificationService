"""The composition root: picks the adapters and builds the use cases."""

from app.application.ports.clock import Clock
from app.application.ports.email_sender import EmailSender
from app.application.use_cases.send_confirmation_code import SendConfirmationCode
from app.infrastructure.clock import SystemClock
from app.infrastructure.config.settings import EmailBackend, Settings
from app.infrastructure.email.console import ConsoleEmailSender
from app.infrastructure.email.smtp import SmtpEmailSender
from app.infrastructure.rabbitmq.consumer import RabbitMqConsumer
from app.infrastructure.templates.renderer import TemplateRenderer
from app.presentation.messaging.handler import MessageHandler


def make_email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend is EmailBackend.SMTP:
        return SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            sender=settings.email_from,
            username=settings.smtp_username,
            password=settings.smtp_password,
            security=settings.smtp_security,
        )
    return ConsoleEmailSender()


class Container:
    def __init__(
        self,
        settings: Settings,
        *,
        email_sender: EmailSender | None = None,
        clock: Clock | None = None,
    ) -> None:
        """``email_sender`` and ``clock`` replace the adapters made from the
        settings (the tests use this)."""
        self.settings = settings
        self.email_sender = email_sender or make_email_sender(settings)
        self.clock = clock or SystemClock()
        self.renderer = TemplateRenderer(settings.site_name, settings.site_url)
        self.send_confirmation_code = SendConfirmationCode(
            self.renderer, self.email_sender, self.clock
        )
        self.handler = MessageHandler(self.send_confirmation_code)
        self.consumer = RabbitMqConsumer(
            settings.rabbitmq_url,
            self.handler,
            prefetch=settings.rabbitmq_prefetch,
            retry_delay_seconds=settings.retry_delay_seconds,
            max_attempts=settings.max_attempts,
        )

    async def start(self) -> None:
        await self.consumer.start()

    async def close(self) -> None:
        await self.consumer.close()
