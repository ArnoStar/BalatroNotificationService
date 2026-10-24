from enum import StrEnum
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailBackend(StrEnum):
    CONSOLE = "console"  # writes the emails to the log (development)
    SMTP = "smtp"


class Settings(BaseSettings):
    """Every setting is an environment variable of the same name in upper
    case (or a line of ``.env``). See ``.env.example``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # where the messages come from (the compose file's rabbitmq)
    rabbitmq_url: str = "amqp://balatro:balatro@localhost:5672/"
    # messages handled at the same time
    rabbitmq_prefetch: int = 10
    # a message that failed for now waits this long, at most this many times,
    # then goes to the failed queue
    retry_delay_seconds: int = 30
    max_attempts: int = 5

    email_backend: EmailBackend = EmailBackend.CONSOLE
    email_from: str = "Balatro <no-reply@localhost>"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    # "starttls" (port 587), "ssl" (port 465) or "none"
    smtp_security: str = "starttls"

    # in the emails: the site's name and address (the portal)
    site_name: str = "Balatro"
    site_url: str = "http://localhost:5174"

    @field_validator("smtp_username", "smtp_password", mode="before")
    @classmethod
    def _empty_is_none(cls, value: Any) -> Any:
        return None if value == "" else value

    @field_validator("site_url")
    @classmethod
    def _no_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


def get_settings() -> Settings:
    return Settings()
