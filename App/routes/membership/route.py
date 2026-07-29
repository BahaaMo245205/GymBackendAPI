from ...Database.db import (
    get_async_session,
    Subscriptions,
    Memberships,
)
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from .helper import get_current_user_id
from sqlalchemy import select

router_membership = APIRouter(prefix="/v1/api/membership", tags=["Membership"])


@router_membership.get("/all", status_code=status.HTTP_200_OK)
async def get_memberships(session: AsyncSession = Depends(get_async_session)):
    query = select(Memberships).where(Memberships.is_active == 1)
    result = await session.execute(query)
    all_memberships = result.scalars().all()

    if not all_memberships:
        raise HTTPException(
            detail="لا يوجد اي أشتركات", status_code=status.HTTP_404_NOT_FOUND
        )

    return {"status": "success", "count": len(all_memberships), "data": all_memberships}


@router_membership.post("/subscription/{id}", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    id: str,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user_id),
):
    query = select(Memberships).where(Memberships.MembershipsID == id)
    result = await session.execute(query)
    memberships_db = result.scalar_one_or_none()

    if not memberships_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="الباقة المطلوبة غير موجوده."
        )

    add_subscription = Subscriptions(
        userid=user_id,
        membershipsid=id,
        startdate=datetime.now(),
        enddate=datetime.now() + timedelta(days=memberships_db.duration_months * 30),
    )

    session.add(add_subscription)
    await session.commit()
    await session.refresh(add_subscription)

    return {
        "message": "تم الاشتراك بنجاح يا بطل! 🏋️‍♂️",
        "subscription_id": add_subscription.SubscriptionsID,
        "start_date": add_subscription.StartDate,
        "end_date": add_subscription.EndDate,
    }
