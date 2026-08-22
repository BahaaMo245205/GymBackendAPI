
from pydantic import BaseModel, Field


class InformationUser(BaseModel):
    Age: int | None
    Address: str | None = Field(min_length=16)
    phone: str | None = Field(min_length=10, max_length=11)
    Gender: str | None


class ChangePassword(BaseModel):
    OldPassword: str = Field(...)
    NewPassword: str = Field(..., min_length=7)
    ConfirmPassword: str = Field(..., min_length=7)
