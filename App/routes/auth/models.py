from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Self


class RegisterSchema(BaseModel):
    username: str = Field(..., min_length=4, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterSchemaOut(BaseModel):
    username: str = Field(..., min_length=4, max_length=50)
    email: EmailStr


class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @model_validator(mode="after")
    def verify_new_passwords_match(self) -> Self:
        if self.new_password != self.confirm_password:
            raise ValueError("🚨 New passwords do not match!")
        return self
