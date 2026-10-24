"""The messages other services send (docs/messages.md). Field names are the
JSON names; a new version is a new model, the old one keeps working."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ConfirmationCodeMessageV1(BaseModel):
    """``email.confirmation_code``: email a code the identity service made."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["confirmation_code"]
    version: Literal[1]
    id: str = Field(min_length=1, max_length=100)
    to: str = Field(min_length=3, max_length=320)
    purpose: Literal["verify_email", "reset_password"]
    code: str = Field(min_length=6, max_length=6)
    created_at: AwareDatetime
    expires_in_minutes: int = Field(ge=1, le=24 * 60)
