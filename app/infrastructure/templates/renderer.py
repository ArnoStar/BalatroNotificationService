import html
from pathlib import Path
from string import Template

from app.application.ports.email_renderer import EmailRenderer
from app.domain.entities.email_message import EmailMessage
from app.domain.value_object.confirmation_code import CodePurpose, ConfirmationCode
from app.domain.value_object.email import Email

_HERE = Path(__file__).parent

# the words of each purpose: subject ({code} in it), heading, intro, outro
_CONFIRMATION_CODE = {
    CodePurpose.VERIFY_EMAIL: (
        "{code} is your {site} confirmation code",
        "Confirm your email",
        "Enter this code to finish creating your account:",
        "If you didn't create an account, ignore this email.",
    ),
    CodePurpose.RESET_PASSWORD: (
        "{code} is your {site} password reset code",
        "Reset your password",
        "Enter this code to choose a new password:",
        "If you didn't ask to reset your password, ignore this email: "
        "your password stays the same.",
    ),
}


class TemplateRenderer(EmailRenderer):
    """The emails from the templates next to this file (``string.Template``:
    ``$name``). Every value put in the HTML is escaped."""

    def __init__(self, site_name: str, site_url: str) -> None:
        self.site_name = site_name
        self.site_url = site_url
        self._text = Template((_HERE / "confirmation_code.txt").read_text())
        self._html = Template((_HERE / "confirmation_code.html").read_text())

    def confirmation_code(
        self,
        to: Email,
        purpose: CodePurpose,
        code: ConfirmationCode,
        minutes_left: int,
    ) -> EmailMessage:
        subject, heading, intro, outro = _CONFIRMATION_CODE[purpose]
        values = {
            "heading": heading,
            "intro": intro,
            "outro": outro,
            "code": code.value,
            "minutes_text": f"{minutes_left} minute{'s' if minutes_left != 1 else ''}",
            "site_name": self.site_name,
            "site_name_upper": self.site_name.upper(),
            "site_url": self.site_url,
        }
        return EmailMessage(
            to=to,
            subject=subject.format(code=code.value, site=self.site_name),
            text=self._text.substitute(values),
            html=self._html.substitute(
                {key: html.escape(value) for key, value in values.items()}
            ),
        )
