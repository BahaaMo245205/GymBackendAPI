from App.routes.users.helper import (
    get_current_user,
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
from fastapi import APIRouter, Query, Depends, HTTPException, Body, status
from App.routes.users.model import ChangePassword, InformationUser
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
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
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    user_id = current_user.get("ID")

    query = select(UserProfile).where(UserProfile.UserID == user_id)
    result = await session.execute(query)
    db_userprofile = result.scalar_one_or_none()

    if not db_userprofile:
        return {
            "UserName": current_user.get("UserName"),
            "Gmail": current_user.get("Email"),
            "Profile": None,
        }

    return {
        "UserName": current_user.get("UserName"),
        "Gmail": current_user.get("Email"),
        "Profile": {
            "Age": db_userprofile.Age,
            "Phone": db_userprofile.Phone,
            "Address": db_userprofile.Address,
            "Gender": db_userprofile.gender,
            "Is_active": db_userprofile.is_active,
        },
    }


# @router_user.post("/me/AddProfile")
# async def AddProfile(
#     IdUser: str,
#     UserInformation: InformationUser,
#     session: AsyncSession = Depends(get_async_session),
# ):

#     try:
#         if not IdUser:
#             raise HTTPException(status_code=400, detail="Id user is required")

#         add_informationUser = UserProfile(
#             phone=UserInformation.phone.strip(),
#             gender=UserInformation.Gender.strip().title(),
#             address=UserInformation.Address,
#             role=UserInformation.Role.title().strip(),
#             age=int(UserInformation.Age),
#             userid=IdUser,
#         )

#         session.add(add_informationUser)
#         await session.commit()

#         await session.refresh(add_informationUser)

#         return add_informationUser
#     except Exception as e:
#         await session.rollback()
#         raise HTTPException(500, detail=f"Error : {e}")


@router_user.put("/me/update")
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
        AddProfileUser = UserProfile(
            phone=user_data.phone.strip(),
            gender=user_data.Gender.strip().title(),
            address=user_data.Address,
            age=int(user_data.Age),
            userid=IdUser,
        )
        session.add(AddProfileUser)
        await session.commit()
        await session.refresh(AddProfileUser)
        return {"message": "Profile created successfully", "profile": AddProfileUser}

    profile.Phone = user_data.phone.strip()
    profile.gender = user_data.Gender.strip().title()
    profile.Address = user_data.Address
    profile.Age = user_data.Age

    await session.commit()
    await session.refresh(profile)

    return {"message": "Profile updated successfully", "profile": profile}


@router_user.put("/me/ChangePassword")
async def ChangePasswords(
    passwords: ChangePassword,
    current_user: dict | str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if passwords.NewPassword != passwords.ConfirmPassword:
        raise HTTPException(status_code=400, detail="كلمات المرور غير متطابقة")

    result = await session.execute(
        select(Users).where(Users.UserID == current_user.get("ID"))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود")

    if not validate_password(user.password, passwords.OldPassword):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="كلمة المرور القديمة غير صحيحة")

    user.password = generate_password_hash(passwords.NewPassword)

    await session.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router_user.get("/me/subscriptions", status_code=status.HTTP_200_OK)
async def get_my_subscriptions(
    session: AsyncSession = Depends(get_async_session),
    current_user_id: str = Depends(get_current_user),
):
    query = select(Subscriptions).where(Subscriptions.UserID == current_user_id)
    result = await session.execute(query)
    db_subscriptions = result.scalars().all()

    if not db_subscriptions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، لا توجد اشتراكات مسجلة لهذا الحساب حالياً.",
        )

    return {
        "status": "success",
        "count": len(db_subscriptions),
        "subscriptions": db_subscriptions,
    }


@router_user.get("/me/bookings", status_code=status.HTTP_200_OK)
async def get_my_bookings(
    current_user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Booking).where(Booking.UserID == current_user_id)
    result = await session.execute(query)
    db_bookings = result.scalars().all()

    if not db_bookings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، ليس لديك أي حجوزات مسجلة حتى الآن.",
        )

    return {"status": "success", "count": len(db_bookings), "bookings": db_bookings}


@router_user.post("/refresh")
async def refresh_session(refresh_token: str = Body(..., embed=True)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")

        if not user_email:
            raise HTTPException(status_code=401, detail="توكن غير صالح")

        new_access_payload = {
            "sub": user_email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
        }
        new_access_token = jwt.encode(
            new_access_payload, SECRET_KEY, algorithm=ALGORITHM
        )

        return {"access_token": new_access_token, "token_type": "bearer"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail="انتهت الجلسة بالكامل، سجل دخول تاني يا بطل"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="التوكن ده مضروب🚨")
