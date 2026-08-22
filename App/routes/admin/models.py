from datetime import datetime

from pydantic import BaseModel, Field


class MembershipDetails(BaseModel):
    Price: float = Field(..., gt=0, title="سعر الباقة")
    duration_months: int = Field(..., gt=0, title="عدد أشهر الباقة")
    walk_machine: bool = Field(default=False, title="هل تتضمن جهاز المشي؟")
    deduct: float = Field(default=0, title="قيمة الخصم")
    description: str = Field(None, title="وصف الباقة")


class UserStatusUpdate(BaseModel):
    is_disabled: bool


class ClassCreateSchema(BaseModel):
    ClassName: str = Field(..., title="اسم الحصة")
    TypeClass: str = Field(..., title="نوع الحصة")
    Price: int = Field(..., gt=0, title="سعر الحصة")
    Date: datetime = Field(..., title="تاريخ الحصة")
    Start_time: str = Field(..., title="وقت البداية")
    End_time: str = Field(..., title="وقت النهاية")
    Trainer_id: str = Field(..., title="معرف المدرب المسؤول")


class ClassUpdateSchema(BaseModel):
    ClassName: str | None = None
    TypeClass: str | None = None
    Price: int | None = Field(None, gt=0)
    Date: datetime | None = None
    Start_time: str | None = None
    End_time: str | None = None
    Trainer_id: str | None = None
    Is_active: bool | None = None


class RoleUpdateSchema(BaseModel):
    new_role: str = Field(
        ..., title="الصلاحية الجديدة للمستخدم", examples=["Admin", "Trainer", "Member"]
    )
