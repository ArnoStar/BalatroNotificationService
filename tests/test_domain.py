import pytest

from app.domain.exceptions import InvalidCode, InvalidEmail
from app.domain.value_object.confirmation_code import ConfirmationCode
from app.domain.value_object.email import Email


def test_email() -> None:
    assert Email(" Player@Example.COM ").value == "player@example.com"
    for bad in ["", "player", "a@b", "a b@example.com", "a@example.com\r\nBcc: x@y.z"]:
        with pytest.raises(InvalidEmail):
            Email(bad)


def test_code() -> None:
    assert ConfirmationCode("012345").value == "012345"
    assert "012345" not in repr(ConfirmationCode("012345"))
    for bad in ["12345", "1234567", "12a456", " 123456"]:
        with pytest.raises(InvalidCode):
            ConfirmationCode(bad)
