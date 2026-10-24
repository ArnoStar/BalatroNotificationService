import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage as MimeMessage
from email.utils import make_msgid

from app.application.exceptions.delivery import DeliveryFailed, UndeliverableEmail
from app.application.ports.email_sender import EmailSender
from app.domain.entities.email_message import EmailMessage

log = logging.getLogger(__name__)


class SmtpEmailSender(EmailSender):
    """SMTP (standard library, in a worker thread), text and HTML parts. A
    refused recipient is undeliverable for good; anything else (a connection
    error, a 4xx answer) is tried again later."""

    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        security: str = "starttls",
        timeout: float = 15,
    ) -> None:
        if security not in ("starttls", "ssl", "none"):
            raise ValueError("SMTP_SECURITY is starttls, ssl or none")
        self.host = host
        self.port = port
        self.sender = sender
        self.username = username
        self.password = password
        self.security = security
        self.timeout = timeout

    async def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self.sender
        mime["To"] = message.to.value
        mime["Subject"] = message.subject
        mime["Message-ID"] = make_msgid(
            domain=self.sender.rpartition("@")[2].strip("> ") or None
        )
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")
        try:
            await asyncio.to_thread(self._send, mime)
        except smtplib.SMTPRecipientsRefused as exc:
            # 5xx: refused for good (no such mailbox); 4xx: for now
            if all(code >= 500 for code, _ in exc.recipients.values()):
                raise UndeliverableEmail from exc
            raise DeliveryFailed from exc
        except (OSError, smtplib.SMTPException) as exc:
            log.warning("SMTP delivery failed: %r", exc)
            raise DeliveryFailed from exc

    def _send(self, mime: MimeMessage) -> None:
        context = ssl.create_default_context()
        smtp: smtplib.SMTP
        if self.security == "ssl":
            smtp = smtplib.SMTP_SSL(
                self.host, self.port, timeout=self.timeout, context=context
            )
        else:
            smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
        with smtp:
            if self.security == "starttls":
                smtp.starttls(context=context)
            if self.username:
                smtp.login(self.username, self.password or "")
            smtp.send_message(mime)
