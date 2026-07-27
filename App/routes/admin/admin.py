from .models import (
    MembershipDetails,
    UserStatusUpdate,
    ClassCreateSchema,
    ClassUpdateSchema,
    RoleUpdateSchema,
)
from ...Database.db import (
    Memberships,
    get_async_session,
    UserProfile,
    Classes,
    Booking,
)
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path
from sqlalchemy import select, func
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
        walk_machine=membership_details.walk_machine,
        deduct=membership_details.deduct,
        description=membership_details.description,
        is_active=True,
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
    membership_id: str = Path(..., title="ID الخاص بالباقة"),
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
    membership_id: str,
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


@router_admin.patch("/ChangeRole/{UserID}", status_code=status.HTTP_200_OK)
async def change_user_role(
    UserID: str,
    role_data: RoleUpdateSchema,
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
    current_admin: dict = Depends(get_current_user),
):
    if (
        current_admin.get("id") == UserID
        or current_admin.get("sub", {}).get("id") == UserID
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="عفواً، لا يمكنك تغيير صلاحيات حسابك الشخصي بهذه الطريقة!",
        )

    query = select(UserProfile).where(UserProfile.UserID == UserID)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم المراد تعديل صلاحيته غير موجود في النظام",
        )

    db_user.Role = role_data.new_role

    try:
        await session.commit()
        await session.refresh(db_user)

        return {
            "status": "success",
            "message": f"تم بنجاح تغيير صلاحية المستخدم إلى: {role_data.new_role}",
            "user_id": db_user.UserID,
            "updated_role": db_user.Role,
        }

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تحديث الصلاحية في قاعدة البيانات: {str(e)}",
        )


@router_admin.post("/Role", status_code=status.HTTP_200_OK)
async def get_admin_role_info(current_role: str = Depends(ensure_admin_role)):
    """
    رووت مخصص للتاكد من دور الأدمن أو جلب الصلاحيات الحالية
    """
    return {
        "status": "success",
        "message": "تم التحقق من الصلاحية بنجاح",
        "assigned_role": current_role,
    }


@router_admin.get("/Reports", status_code=status.HTTP_200_OK)
async def get_system_reports(
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
):
    try:
        users_count_query = select(func.count(UserProfile.UserID))
        users_result = await session.execute(users_count_query)
        total_users = users_result.scalar() or 0

        classes_count_query = select(func.count(Classes.ClassesID)).where(
            Classes.Is_active == True
        )
        classes_result = await session.execute(classes_count_query)
        total_classes = classes_result.scalar() or 0

        bookings_count_query = select(func.count(Booking.BookingID)).where(
            Booking.Is_active == True
        )
        bookings_result = await session.execute(bookings_count_query)
        total_bookings = bookings_result.scalar() or 0

        # revenue_query = select(func.sum(Memberships.Price))
        # revenue_result = await session.execute(revenue_query)
        # total_revenue = revenue_result.scalar() or 0

        return {
            "status": "success",
            "message": "تم استخراج تقارير النظام بنجاح",
            "reports": {
                "total_users": total_users,
                "total_active_classes": total_classes,
                "total_active_bookings": total_bookings,
                # "total_revenue": total_revenue
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء استخراج التقارير: {str(e)}",
        )


@router_admin.patch("/users/{user_id}/status", status_code=status.HTTP_200_OK)
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
):
    query = select(UserProfile).where(UserProfile.UserID == user_id)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود في النظام"
        )

    db_user.is_active = status_update.is_disabled

    try:
        await session.commit()
        await session.refresh(db_user)

        status_text = "مفعل" if db_user.is_active else "محظور"

        return {
            "status": "success",
            "message": f"تم تحديث حالة المستخدم بنجاح وأصبح الآن: {status_text}",
            "user_id": db_user.UserID,
            "is_active": db_user.is_active,
        }

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة المستخدم في قاعدة البيانات",
        )


@router_admin.post("/classes", status_code=status.HTTP_201_CREATED)
async def create_new_class(
    class_data: ClassCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
):
    new_class = Classes(
        classname=class_data.ClassName,
        typeclass=class_data.TypeClass,
        price=class_data.Price,
        date=class_data.Date,
        starttime=class_data.Start_time,
        endtime=class_data.End_time,
        trainerid=class_data.Trainer_id,
    )

    try:
        session.add(new_class)
        await session.commit()
        await session.refresh(new_class)

        return {
            "status": "success",
            "message": "تم إنشاء الحصة بنجاح",
            "classes_id": new_class.ClassesID,
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء حفظ الحصة: {str(e)}",
        )


@router_admin.patch("/classes/{class_id}", status_code=status.HTTP_200_OK)
async def update_class(
    class_id: str,
    class_data: ClassUpdateSchema,
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
):
    query = select(Classes).where(Classes.ClassesID == class_id)
    result = await session.execute(query)
    db_class = result.scalar_one_or_none()

    if not db_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الحصة دي مش موجودة في السيستم، اتأكد من الـ ID",
        )

    update_data = class_data.model_dump(exclude_unset=True)  #

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم يتم إرسال أي بيانات للتحديث!",
        )

    for key, value in update_data.items():  #
        setattr(db_class, key, value)  #

    try:
        await session.commit()
        await session.refresh(db_class)

        return {
            "status": "success",
            "message": "تم تحديث بيانات الحصة بنجاح",
            "data": db_class,
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الحصة في قاعدة البيانات",
        )


@router_admin.delete("/classes/{class_id}", status_code=status.HTTP_200_OK)
async def delete_class(
    class_id: str,
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
):
    query = select(Classes).where(Classes.ClassesID == class_id)
    result = await session.execute(query)
    db_class = result.scalar_one_or_none()

    if not db_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="الحصة غير موجودة بالفعل"
        )

    try:
        await session.delete(db_class)
        await session.commit()

        return {"status": "success", "message": "تم حذف الحصة نهائياً من السيستم"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="تعذر حذف الحصة، قد تكون مرتبطة بحجوزات قائمة للمشتركين",
        )


@router_admin.post("/Check_Role", status_code=status.HTTP_200_OK)
async def check_role(role: str = Depends(ensure_admin_role)):
    return {
        "status": "success",
        "message": "أهلاً بك يا أدمن، أنت تمتلك الصلاحيات الكاملة للتحكم في النظام.",
        "role": role,
    }
