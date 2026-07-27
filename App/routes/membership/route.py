from fastapi import APIRouter, Depends, status, HTTPException
from ...Database.db import get_async_session, Memberships
from sqlalchemy.ext.asyncio import AsyncSession
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

    return {
        "status": "success", 
        "count": len(all_memberships), 
        "data": all_memberships
    }