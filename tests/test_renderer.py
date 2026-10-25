from app.domain.value_object.confirmation_code import CodePurpose, ConfirmationCode
from app.domain.value_object.email import Email
from app.infrastructure.templates.renderer import TemplateRenderer


def test_html_escapes_the_values() -> None:
    renderer = TemplateRenderer("<b>Jimbo's</b>", "https://example.com/?a=1&b=2")
    email = renderer.confirmation_code(
        Email("player@example.com"),
        CodePurpose.VERIFY_EMAIL,
        ConfirmationCode("123456"),
        5,
    )
    assert "<b>Jimbo" not in email.html
    assert "&lt;B&gt;JIMBO&#x27;S&lt;/B&gt;" in email.html
    assert 'href="https://example.com/?a=1&amp;b=2"' in email.html
    assert "<b>Jimbo's</b>" in email.text  # (plain text: as it is)
    assert "5 minutes" in email.html


def test_every_purpose_has_its_words() -> None:
    renderer = TemplateRenderer("Balatro", "https://example.com")
    for purpose in CodePurpose:
        email = renderer.confirmation_code(
            Email("p@example.com"), purpose, ConfirmationCode("000001"), 10
        )
        assert email.subject.startswith("000001 is your Balatro")
        assert "$" not in email.text and "$" not in email.html
