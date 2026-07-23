from ...Database.db import get_async_session, Classes, Users, UserProfile, Booking
from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .helper import *

classes_router = APIRouter(prefix="/v1/api/classes", tags=["Classes"])


@classes_router.get("/", status_code=status.HTTP_200_OK)
async def get_all_classes(session: AsyncSession = Depends(get_async_session)):
    query = select(Classes).where(Classes.Is_active == True)
    result = await session.execute(query)
    all_classes = result.scalars().all()

    if not all_classes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، لا توجد أي حصص تدريبية متاحة حالياً في الجيم.",
        )

    return {"status": "success", "count": len(all_classes), "data": all_classes}


@classes_router.post("/{class_id}/book", status_code=status.HTTP_201_CREATED)
async def book_class(
    class_id: str,  # تم التعديل ليكون String (UUID) متوافق مع جدول الحصص
    current_user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    # 1. التأكد أن الحصة موجودة أصلاً وفعالة
    class_query = select(Classes).where(
        Classes.ClassesID == class_id, Classes.Is_active == True
    )
    class_result = await session.execute(class_query)
    target_class = class_result.scalar_one_or_none()

    if not target_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، هذه الحصة غير موجودة أو تم إلغاؤها.",
        )

    existing_booking_query = select(Booking).where(
        Booking.UserID == current_user_id, Booking.ClassID == class_id
    )
    existing_result = await session.execute(existing_booking_query)
    already_booked = existing_result.scalar_one_or_none()

    if already_booked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="أنت مسجل بالفعل في هذه الحصة مسبقاً!",
        )

    new_booking = Booking(UserID=current_user_id, ClassesID=class_id, Is_active=True)

    try:
        session.add(new_booking)
        await session.commit()
        await session.refresh(new_booking)

        return {
            "status": "success",
            "message": "تم حجز الحصة بنجاح",
            "booking_id": new_booking.BookingID,
            "class_name": target_class.ClassName,
        }

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إتمام الحجز: {str(e)}",
        )


@classes_router.delete("/{class_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_class_booking(
    class_id: str,
    current_user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Booking).where(
        Booking.UserID == current_user_id,
        Booking.ClassID == class_id,
        Booking.Is_active == True,
    )
    result = await session.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، لا يوجد حجز نشط لك لهذه الحصة لكي تقوم بإلغائه.",
        )

    try:
        await session.delete(booking)

        # booking.Is_active = False

        await session.commit()

        return {
            "status": "success",
            "message": "تم إلغاء حجز الحصة بنجاح وتحرير مكانك.",
        }

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إلغاء الحجز: {str(e)}",
        )
