import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...app import logger
from ...Database.db import Memberships, Subscriptions, get_async_session
from ...redis_client import redis_client
from .helper import get_current_user

router_membership = APIRouter(prefix="/v1/api/membership", tags=["Membership"])


@router_membership.get("/all", status_code=status.HTTP_200_OK)
async def get_memberships(session: AsyncSession = Depends(get_async_session)):
    cashed_key = "all_memberships"

    try:
        cashed = await redis_client.get(cashed_key)
        if cashed:
            logger.info("تم تحميل جميع الاشتراكات بنجاح من Redis ")
            memberships_data = json.loads(cashed)
            logger.info("جلب الاشتركات من Redis")
            return {
                "status": "success",
                "count": len(memberships_data),
                "memberships": memberships_data,
            }
    except Exception as e:
        logger.error(f"Redis get error: {e}")

    query = select(Memberships).where(Memberships.is_active == 1)
    result = await session.execute(query)
    all_memberships = result.scalars().all()

    if not all_memberships:
        logger.info("لا يوجد اي أشتركات")
        raise HTTPException(
            detail="لا يوجد اي أشتركات", status_code=status.HTTP_404_NOT_FOUND
        )

    memberships_list = [
        {
            "id": m.MembershipsID,
            "price": m.Price,
            "duration_months": m.duration_months,
            "walk_machine": m.walk_machine,
            "is_active": m.is_active,
        }
        for m in all_memberships
    ]

    try:
        await redis_client.set(cashed_key, json.dumps(memberships_list), ex=300)
    except Exception as e:
        logger.error(f"Redis set error: {e}")

    logger.info("تم جلب جميع الاشتراكات بنجاح من الداتابيز 🗄️")
    return {
        "status": "success",
        "count": len(all_memberships),
        "memberships": memberships_list,
    }


@router_membership.post("/subscription/{id}", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("ID") or current_user.get("UserID")
    if not user_id:
        raise HTTPException(status_code=401, detail="المستخدم غير معروف")

    try:
        await redis_client.delete(f"user:subscriptions:{user_id}")
    except Exception as e:
        logger.error(f"Redis delete error: {e}")

    result = await session.execute(
        select(Memberships).where(Memberships.MembershipsID == id)
    )
    memberships_db = result.scalar_one_or_none()

    if not memberships_db:
        logger.info(f"Membership not found | id={id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الباقة المطلوبة غير موجودة.",
        )

    result = await session.execute(
        select(Subscriptions).where(
            Subscriptions.UserID == user_id,
            Subscriptions.EndDate > datetime.now(),
            Subscriptions.status == "active",
        )
    )
    active_sub = result.scalars().first()

    if active_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لديك اشتراك ساري بالفعل. لا يمكن التسجيل في باقة جديدة الآن.",
        )

    add_subscription = Subscriptions(
        userid=user_id,
        membershipsid=id,
        startdate=datetime.now(),
        enddate=datetime.now() + timedelta(days=memberships_db.duration_months * 30),
        status="active",
    )

    try:
        session.add(add_subscription)
        await session.commit()
        await session.refresh(add_subscription)

        logger.info(
            f"Subscription created | user={user_id} | membership={id} | "
            f"sub={add_subscription.SubscriptionsID}"
        )

        return {
            "status": "success",
            "message": "تم الاشتراك بنجاح يا بطل! 🏋️‍♂️",
            "subscription_id": add_subscription.SubscriptionsID,
            "start_date": add_subscription.StartDate,
            "end_date": add_subscription.EndDate,
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"Subscription error | user={user_id} | error={e}")
        raise HTTPException(
            status_code=500,
            detail="حدث خطأ أثناء إنشاء الاشتراك",
        )
