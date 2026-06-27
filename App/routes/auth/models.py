from pydantic import BaseModel, Field, EmailStr
from typing import Union


class Register(BaseModel):
    username: Union[str, None] = Field(..., min_length=4)
    email: Union[str, EmailStr]
    password: Union[str] = Field(..., min_length=8)


class login(BaseModel):
    email: Union[str, None]
    password: Union[str, None]


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    NewPassword: Union[str:None]
    ConfirmPassword: Union[str:None]
