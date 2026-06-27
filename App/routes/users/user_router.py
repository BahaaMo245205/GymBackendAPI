from fastapi import APIRouter

router_user = APIRouter(prefix="/v1/api/user", tags=["User"])


@router_user.get("/me")
async def ProfileUser():
    return {"Massage": "Hello Profile"}


@router_user.put("/me/UpdateProfile")
async def UpdateProfile():
    return None


@router_user.put("/me/ChangePassword")
async def ChangePassword():
    return None


@router_user.put("/me/subscriptions")
async def subscriptions():
    return None


@router_user.put("/me/bookings")
async def bookings():
    return None
