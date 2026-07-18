from App.routes.users.helper import (
    get_current_user_id,
    retrieve_client_ip,
    generate_password_hash,
    validate_password,
)
from App.Database.db import (
    get_async_session,
    Users,
    UserProfile,
    Subscriptions,
    Booking,
)
from App.routes.users.model import ChangePassword, InformationUser
from fastapi import APIRouter, Query, Depends, HTTPException,Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Union
from dotenv import load_dotenv
from sqlalchemy import select
from jose import jwt
import datetime
import os

router_user = APIRouter(prefix="/v1/api/user", tags=["User"])


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

@router_user.get("/me")
async def ProfileUser(
    IdUser: Annotated[Union[str, None], Query(...)],
    session: AsyncSession = Depends(get_async_session),
):
    query = select(UserProfile).where(UserProfile.UserID == IdUser)
    result = await session.execute(query)
    db_userprofile = result.scalar_one_or_none()

    query1 = select(Users).where(Users.UserID == IdUser)
    result = await session.execute(query1)
    db_user = result.scalar_one_or_none()

    return {
        "UserName": db_user.UserName,
        "Gmail": db_user.email,
        "Profile": {
            "Phone": db_userprofile.Phone,
            "Address": db_userprofile.Address,
            "Gender": db_userprofile.gender,
            "Role": db_userprofile.Role,
            "Is_active": db_userprofile.is_active,
        },
    }


@router_user.post("/me/AddProfile")
async def AddProfile(
    IdUser: str,
    UserInformation: InformationUser,
    session: AsyncSession = Depends(get_async_session),
):

    try:
        if not IdUser:
            raise HTTPException(status_code=400, detail="Id user is required")

        add_informationUser = UserProfile(
            phone=UserInformation.phone.strip(),
            gender=UserInformation.Gender.strip().title(),
            address=UserInformation.Address,
            role=UserInformation.Role.title().strip(),
            age=int(UserInformation.Age),
            userid=IdUser,
        )

        session.add(add_informationUser)
        await session.commit()

        await session.refresh(add_informationUser)

        return add_informationUser
    except Exception as e:
        await session.rollback()
        raise HTTPException(500, detail=f"Error : {e}")


@router_user.put("/me/UpdateProfile")
async def UpdateProfile(
    IdUser: Annotated[str, Query(...)],
    user_data: InformationUser,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(UserProfile).where(UserProfile.UserID == IdUser)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.Phone = user_data.phone.strip()
    profile.gender = user_data.Gender.strip().title()
    profile.Address = user_data.Address
    profile.Role = user_data.Role.title().strip()
    profile.Age = user_data.Age

    await session.commit()
    await session.refresh(profile)

    return {"message": "Profile updated successfully", "profile": profile}


@router_user.put("/me/ChangePassword")
async def ChangePasswords(
    passwords: ChangePassword,
    IdUser: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    if passwords.NewPassword != passwords.ConfirmPassword:
        raise HTTPException(status_code=400, detail="كلمات المرور غير متطابقة")

    result = await session.execute(select(Users).where(Users.UserID == IdUser))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    if not validate_password(user.password, passwords.NewPassword):
        raise HTTPException(status_code=400, detail="كلمة المرور القديمة غير صحيحة")

    user.password = generate_password_hash(passwords.NewPassword)

    await session.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router_user.put("/me/subscriptions")
async def subscriptions(
    IdUser: str=Depends(get_current_user_id), session: AsyncSession = Depends(get_async_session)
):
    query = select(Subscriptions).where(Subscriptions.UserID == IdUser)
    result = await session.execute(query)
    db_subscriptions = result.scalar_one_or_none()
    
    return None


@router_user.put("/me/bookings")
async def bookings():
    return None


@router_user.post("/refresh")
async def refresh_session(refresh_token: str = Body(..., embed=True)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        
        if not user_email:
            raise HTTPException(status_code=401, detail="توكن غير صالح")
            
        new_access_payload = {"sub": user_email, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}
        new_access_token = jwt.encode(new_access_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        return {"access_token": new_access_token, "token_type": "bearer"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="انتهت الجلسة بالكامل، سجل دخول تاني يا بطل")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="التوكن ده مضروب🚨")