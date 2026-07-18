from ...Database.db import Memberships, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path
from .models import MembershipDetails
from fastapi.requests import Request
from sqlalchemy import select
from .helper import *

router_admin = APIRouter(prefix="/v1/api/admin", tags=["Admins"])


@router_admin.post("/Membership_Management", status_code=status.HTTP_201_CREATED)
async def membership_management(
    membership_details: MembershipDetails,
    session: AsyncSession = Depends(get_async_session),
):
    add_membership = Memberships(
        price=membership_details.Price,
        duration_months=membership_details.duration_months,
        cardio_device=membership_details.walk_machine,
        discount_amount=membership_details.deduct,
        description=membership_details.description,
    )

    try:
        session.add(add_membership)
        await session.commit()
        await session.refresh(add_membership)

        return {
            "status": "success",
            "message": "تم إضافة الباقة بنجاح",
            "data": add_membership,
        }

    except Exception as e:
        await session.rollback()
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حفظ الباقة في قاعدة البيانات",
        )


@router_admin.patch("/memberships/{membership_id}", status_code=status.HTTP_200_OK)
async def update_membership(
    membership_id: int = Path(..., title="ID الخاص بالباقة"),
    update_data: MembershipDetails = None,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Memberships).where(Memberships.MembershipsID == membership_id)
    result = await session.execute(query)
    db_membership = result.scalar_one_or_none()

    if not db_membership:
        raise HTTPException(status_code=404, detail="الباقة دي مش موجودة!")

    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_membership, key, value)

    try:
        await session.commit()
        await session.refresh(db_membership)
        return {
            "status": "success",
            "message": "تم تحديث الباقة بنجاح",
            "data": db_membership,
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail="مشكلة في تحديث البيانات")


@router_admin.delete("/memberships/{membership_id}", status_code=status.HTTP_200_OK)
async def delete_membership(
    membership_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Memberships).where(Memberships.MembershipsID == membership_id)
    result = await session.execute(query)
    db_membership = result.scalar_one_or_none()

    if not db_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الباقة دي مش موجودة، اتأكد من الـ ID",
        )

    try:
        await session.delete(db_membership)
        await session.commit()
        return {"status": "success", "message": "تم حذف الباقة نهائياً من السيستم"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء محاولة الحذف",
        )


@router_admin.post("/Role")
async def Role(): ...


@router_admin.get("/Reports")
async def Reports():
    """This rourts for extracting reports"""


@router_admin.post("/users/{user_id}/status")
async def user(user_id: int): ...


@router_admin.post("/classes")
async def classes(): ...


@router_admin.post("/Check_Role")
async def check_role(currunt_user_role: str = Depends(get_current_user_role)):
    if not currunt_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مش قادرين نحدد صلاحيتك، سجل دخولك الأول",
        )

    elif currunt_user_role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="معاك صلاحية بس مش أدمن، المنطقة دي ممنوعة عليك!",
        )

    return {
        "status": "success",
        "message": "أهلاً بك يا أدمن، يمكنك التحكم في النظام",
        "role": currunt_user_role,
    }
