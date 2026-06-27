from pydantic import BaseModel, Field, EmailStr
from typing import Union


class InformationUser(BaseModel):
    Age: Union[int, None] = Field(max_length=2)
    Address: Union[str, None] = Field(min_length=16)
    phone: Union[str, None] = Field(min_length=10, max_length=11)
    image: Union[str, None]


class ChangePassword(BaseModel):
    OldPassword: Union[str, None]
    NewPassword: Union[str, None] = Field(..., min_length=8)
    ConfirmPassword: Union[str, None] = Field(..., min_length=8)
