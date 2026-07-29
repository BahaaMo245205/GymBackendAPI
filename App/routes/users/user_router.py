from App.routes.users.helper import (
    generate_password_hash,
    validate_password,
    get_current_user,
)
from App.Database.db import (
    get_async_session,
    Subscriptions,
    UserProfile,
    Booking,
    Classes,
    Users,
)
from fastapi import (
    HTTPException,
    UploadFile,
    APIRouter,
    Depends,
    status,
    Query,
    Body,
    File,
)
from App.routes.users.model import ChangePassword, InformationUser
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from sqlalchemy import select, update
from typing import Annotated
from pathlib import Path
from jose import jwt
import datetime
import uuid
import os

router_user = APIRouter(prefix="/v1/api/user", tags=["User"])


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

BASE_DIR = Path(__file__).resolve().parent.parent.parent 
UPLOAD_DIR = BASE_DIR  / "static" / "profiles"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


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
        "Role": current_user.get("Role"),
        "Profile": {
            "Age": db_userprofile.Age,
            "Phone": db_userprofile.Phone,
            "Address": db_userprofile.Address,
            "Gender": db_userprofile.gender,
            "Is_active": db_userprofile.is_active,
        },
    }

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود"
        )

    if not validate_password(user.password, passwords.OldPassword):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="كلمة المرور القديمة غير صحيحة",
        )

    user.password = generate_password_hash(passwords.NewPassword)

    await session.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router_user.get("/me/subscriptions", status_code=status.HTTP_200_OK)
async def get_my_subscriptions(
    session: AsyncSession = Depends(get_async_session),
    current_user_id: dict = Depends(get_current_user),
):
    query = select(Subscriptions).where(
        Subscriptions.UserID == current_user_id.get("ID")
    )
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
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    user_id = current_user.get("ID") or current_user.get("UserID")

    query = (
        select(Booking, Classes)
        .join(Classes, Classes.ClassesID == Booking.ClassID)
        .where(Booking.UserID == user_id)
    )
    result = await session.execute(query)
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عفواً، ليس لديك أي حجوزات مسجلة حتى الآن.",
        )

    bookings_data = []
    for booking, class_obj in rows:
        bookings_data.append(
            {
                "BookingID": (
                    booking.BookingID if hasattr(booking, "BookingID") else None
                ),
                "ClassID": booking.ClassID,
                "status": getattr(booking, "status", "active"),
                "ClassName": class_obj.ClassName,
                "TypeClass": class_obj.TypeClass,
                "Price": class_obj.Price,
                "Date": class_obj.Date,
                "Start_time": class_obj.Start_time,
                "End_time": class_obj.End_time,
                "Trainer_id": class_obj.Trainer_id,
            }
        )

    return {
        "status": "success",
        "count": len(bookings_data),
        "bookings": bookings_data,
    }


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


@router_user.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="الملف المرفوع ليس صورة صالحة.")

    user_id = current_user.get("ID") or current_user.get("UserID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="امتداد الصورة غير مدعوم.")

    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:  
            raise HTTPException(status_code=400, detail="حجم الصورة كبير جدًا (الحد 5MB).")

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        await session.execute(
            update(Users)
            .where(Users.UserID == user_id)
            .values(profile_image=unique_filename)
        )
        await session.commit()

        image_url = f"/static/profiles/{unique_filename}"

        return {
            "status": "success",
            "message": "تم رفع الصورة بنجاح",
            "image_url": image_url,
            "filename": unique_filename,
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {e}")
