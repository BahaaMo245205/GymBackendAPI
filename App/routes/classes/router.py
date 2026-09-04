import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import get_current_user
from ...Database.db import Booking, Classes, Users, get_async_session
from ...redis import redis_client

logger = logging.getLogger(__name__)
classes_router = APIRouter(prefix="/v1/api/classes", tags=["Classes"])

DbSession = Depends(get_async_session)
CurrentUser = Depends(get_current_user)


@classes_router.get("/", status_code=status.HTTP_200_OK)
async def get_all_classes(session: AsyncSession = DbSession):
    cash_key = "all_classes"
    cash = await redis_client.get(cash_key)
    if cash:
        logger.info("تم تحميل جميع الكلاسات بنجاح من Redis")
        return {
            "status": "success",
            "classes": json.loads(cash),
        }

    query = (
        select(Classes, Users)
        .join(Users, Users.UserID == Classes.Trainer_id)
        .where(Classes.Is_active == True)
    )
    result = await session.execute(query)
    rows = result.all()

    get_all_class = [
        {
            "ClassesID": c.ClassesID,
            "ClassName": c.ClassName,
            "Date": str(c.Date),
            "End_time": c.End_time,
            "Start_time": c.Start_time,
            "Price": c.Price,
            "Trainer_id": c.Trainer_id,
            "TrainerName": u.UserName if u else None,
            "Is_active": c.Is_active,
            "TypeClass": c.TypeClass,
        }
        for c, u in rows
    ]
    logger.info("جلب جميع الكلاسات بنجاح")
    await redis_client.set(cash_key, json.dumps(get_all_class), ex=3600)
    return {"status": "success", "count": len(get_all_class), "data": get_all_class}


@classes_router.post("/{class_id}/booking", status_code=status.HTTP_201_CREATED)
async def book_class(
    class_id: str,
    current_user_id: dict = CurrentUser,
    session: AsyncSession = DbSession,
):
    cash_key = "user:bookings:" + current_user_id.get("ID")
    await redis_client.delete(cash_key)

    class_query = select(Classes).where(
        Classes.ClassesID == class_id, Classes.Is_active == True
    )
    class_result = await session.execute(class_query)
    target_class = class_result.scalar_one_or_none()

    if not target_class:
        await redis_client.delete(cash_key)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، هذه الحصة غير موجودة أو تم إلغاؤها.",
        )

    existing_booking_query = select(Booking).where(
        Booking.UserID == current_user_id.get("ID"), Booking.ClassID == class_id
    )
    existing_result = await session.execute(existing_booking_query)
    already_booked = existing_result.scalar_one_or_none()

    if already_booked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="أنت مسجل بالفعل في هذه الحصة مسبقاً!",
        )

    new_booking = Booking(
        userid=current_user_id.get("ID"),
        classid=class_id,
        is_active=True,
        date=datetime.now(),
    )

    try:
        session.add(new_booking)
        await session.commit()
        await session.refresh(new_booking)
        logger.info("تم إتمام الحجز بنجاح")
        return {
            "status": "success",
            "message": "تم حجز الحصة بنجاح",
            "booking_id": new_booking.BookingID,
            "class_name": target_class.ClassName,
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"حدث خطأ أثناء إتمام الحجز: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إتمام الحجز: {e!s}",
        )


@classes_router.delete("/{class_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_class_booking(
    class_id: str,
    current_user: dict = CurrentUser,
    session: AsyncSession = DbSession,
):
    user_id = current_user.get("ID") or current_user.get("UserID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info(f"Cancel booking | user={user_id} | class_or_booking={class_id}")

    result = await session.execute(
        select(Booking).where(
            Booking.UserID == user_id,
            Booking.ClassID == class_id,
            Booking.Is_active == False,
        )
    )
    booking = result.scalar_one_or_none()

    if not booking:
        result = await session.execute(
            select(Booking).where(
                Booking.UserID == user_id,
                Booking.BookingID == class_id,
                Booking.Is_active == False,
            )
        )
        booking = result.scalar_one_or_none()

    if not booking:
        logger.warning(f"No pending booking found | user={user_id} | id={class_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، لا يوجد حجز قيد التفعيل لإلغائه.",
        )

    logger.info(
        f"Booking found | BookingID={booking.BookingID} | "
        f"ClassID={booking.ClassID} | Is_active={booking.Is_active}"
    )

    try:
        await session.delete(booking)
        await session.commit()

        try:
            await redis_client.delete(f"user:bookings:{user_id}")
        except Exception:
            logging.exception("Exception occurred")


        return {
            "status": "success",
            "message": "تم إلغاء الحجز بنجاح",
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"Cancel booking error: {e}")
        raise HTTPException(status_code=500, detail="تعذر إلغاء الحجز")
