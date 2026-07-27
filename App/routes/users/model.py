from pydantic import BaseModel, Field, EmailStr
from typing import Union


class InformationUser(BaseModel):
    Age: Union[int, None]
    Address: Union[str, None] = Field(min_length=16)
    phone: Union[str, None] = Field(min_length=10, max_length=11)
    Gender: Union[str, None] 
    
class ChangePassword(BaseModel):
    OldPassword: str = Field(...)
    NewPassword: str = Field(..., min_length=7)
    ConfirmPassword: str = Field(..., min_length=7)