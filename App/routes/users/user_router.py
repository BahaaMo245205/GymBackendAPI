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
    Body,
    File,
)
from App.routes.users.model import ChangePassword, InformationUser
from sqlalchemy.ext.asyncio import AsyncSession
from ...app import logger, redis_client
from sqlalchemy import select, update
from dotenv import load_dotenv
from typing import Annotated
from pathlib import Path
from jose import jwt
import datetime
import json
import uuid
import os

router_user = APIRouter(prefix="/v1/api/user", tags=["User"])


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "static" / "profiles"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


@router_user.get("/me")
async def ProfileUser(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    user_id = current_user.get("ID") or current_user.get("UserID")
    cache_key = f"user:profile:{user_id}"

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(
                f"Profile cache hit | user_id={user_id}, cache_key={cache_key} , {cached}"
            )
            return json.loads(cached)

        query = select(UserProfile).where(UserProfile.UserID == user_id)
        result = await session.execute(query)
        db_userprofile = result.scalar_one_or_none()

        query_image = select(Users).where(Users.UserID == user_id)
        result_image = await session.execute(query_image)
        db_image = result_image.scalar_one_or_none()

        if not db_userprofile:
            payload = {
                "UserName": current_user.get("UserName"),
                "Gmail": current_user.get("Email"),
                "Role": current_user.get("Role") or current_user.get("user-role"),
                "profile_image": db_image.profile_image if db_image else None,
                "Profile": None,
            }
            await redis_client.set(cache_key, json.dumps(payload), ex=3600)
            return payload

        payload = {
            "UserName": current_user.get("UserName"),
            "Gmail": current_user.get("Email"),
            "Role": current_user.get("Role") or current_user.get("user-role"),
            "profile_image": db_image.profile_image if db_image else None,
            "Is_active": db_image.is_active,
            "Profile": {
                "Age": db_userprofile.Age,
                "Phone": db_userprofile.Phone,
                "Address": db_userprofile.Address,
                "Gender": db_userprofile.gender,
            },
        }

        await redis_client.set(cache_key, json.dumps(payload), ex=3600)
        logger.info(f"Profile loaded from DB and cached | user_id={user_id}")

        return payload

    except Exception as e:
        logger.error(f"Error get profile | user_id={user_id} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router_user.put("/me/update")
async def UpdateProfile(
    user_data: InformationUser,
    IdUser:dict=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await redis_client.delete(f"user:profile:{IdUser.get("ID")}")
    result = await session.execute(
        select(UserProfile).where(UserProfile.UserID == IdUser.get("ID"))
    )
    profile = result.scalar_one_or_none()

    logger.info(f"Profile cache deleted | user_id={IdUser.get("ID")}")

    if not profile:
        AddProfileUser = UserProfile(
            phone=user_data.phone.strip(),
            gender=user_data.Gender.strip().title(),
            address=user_data.Address,
            age=int(user_data.Age),
            userid=IdUser.get("ID"),
        )
        session.add(AddProfileUser)
        await session.commit()
        await session.refresh(AddProfileUser)
        logger.info("تم إنشاء الملف الشخصي بنجاح")
        return {"message": "Profile created successfully", "profile": AddProfileUser}

    profile.Phone = user_data.phone.strip()
    profile.gender = user_data.Gender.strip().title()
    profile.Address = user_data.Address
    profile.Age = user_data.Age

    await session.commit()
    await session.refresh(profile)
    logger.info("تم تحديث الملف الشخصي بنجاح")
    return {"message": "Profile updated successfully", "profile": profile}


@router_user.put("/me/ChangePassword")
async def ChangePasswords(
    passwords: ChangePassword,
    current_user: dict | str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if passwords.NewPassword != passwords.ConfirmPassword:
        logger.warning("كلمات المرور غير متطابقة")
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
    logger.info("تم تغيير كلمة المرور بنجاح")
    await session.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router_user.get("/me/subscriptions", status_code=status.HTTP_200_OK)
async def get_my_subscriptions(
    session: AsyncSession = Depends(get_async_session),
    current_user_id: dict = Depends(get_current_user),
):
    cashed_key = f"user:subscriptions:{current_user_id.get('ID')}"
    cashed = await redis_client.get(cashed_key)
    if cashed:
        logger.info("تم تحميل جميع الاشتراكات بنجاح من Redis")
        return {
            "status": "success",
            "subscriptions": json.loads(cashed),
        }

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
    all_db_subscriptions = [
        {
            "StartDate": str(sub.StartDate),
            "EndDate": str(sub.EndDate),
            "status": sub.status,
        }
        for sub in db_subscriptions
    ]
    await redis_client.set(
        cashed_key,
        json.dumps(all_db_subscriptions),
        ex=3600,
    )
    logger.info("تم تحميل جميع الاشتراكات بنجاح")
    return {
        "status": "success",
        "subscriptions": db_subscriptions,
    }


@router_user.get("/me/bookings", status_code=status.HTTP_200_OK)
async def get_my_bookings(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    
    user_id = current_user.get("ID") or current_user.get("UserID")
    cache_key = f"user:bookings:{user_id}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"Bookings cache hit | user_id={user_id}")
            bookings_data = json.loads(cached)
            return {
                "status": "success",
                "count": len(bookings_data),
                "bookings": bookings_data,
            }

        query = (
            select(Booking, Classes)
            .join(Classes, Classes.ClassesID == Booking.ClassID)
            .where(Booking.UserID == user_id)
        )
        result = await session.execute(query)
        rows = result.all()

        bookings_data = []
        for booking, class_obj in rows:
            bookings_data.append(
                {
                    "BookingID": getattr(booking, "BookingID", None),
                    "ClassID": booking.ClassID,
                    "status": getattr(booking, "status", "active"),
                    "ClassName": class_obj.ClassName,
                    "TypeClass": class_obj.TypeClass,
                    "Price": class_obj.Price,
                    "Date": str(class_obj.Date) if class_obj.Date else None,
                    "Start_time": class_obj.Start_time,
                    "End_time": class_obj.End_time,
                    "Trainer_id": class_obj.Trainer_id,
                }
            )

        await redis_client.set(cache_key, json.dumps(bookings_data), ex=3600)
        logger.info(f"Bookings loaded from DB | user_id={user_id} | count={len(bookings_data)}")

        return {
            "status": "success",
            "count": len(bookings_data),
            "bookings": bookings_data,
        }

    except Exception as e:
        logger.error(f"Error get bookings | user_id={user_id} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router_user.post("/refresh")
async def refresh_session(
    refresh_token: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        payload = jwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("ID")
        ip_address = payload.get("ip-address")

        if not user_id:
            raise HTTPException(status_code=401, detail="توكن غير صالح")

        result = await session.execute(
            select(Users).where(Users.UserID == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="المستخدم غير موجود")


        new_access_payload = {
            "ID": user.UserID,
            "Email": getattr(user, "Email", None) or getattr(user, "email", None),
            "UserName": getattr(user, "UserName", None) or getattr(user, "username", None),
            "Role": getattr(user, "Role", None) or getattr(user, "role", "User"),
            "ip-address": ip_address,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
        }

        if not new_access_payload["Email"]:
            raise HTTPException(status_code=401, detail="بيانات المستخدم غير مكتملة")

        new_access_token = jwt.encode(
            new_access_payload,
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        logger.info(f"Session refreshed | user_id={user.UserID}")
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }

    except jwt.ExpiredSignatureError:
        logger.warning("Refresh token expired")
        raise HTTPException(
            status_code=401,
            detail="انتهت الجلسة بالكامل، سجل دخول مرة أخرى",
        )
    except jwt.InvalidTokenError:
        logger.warning("Invalid refresh token")
        raise HTTPException(status_code=401, detail="التوكن غير صالح")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        raise HTTPException(status_code=401, detail="توكن غير صالح")

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"امتداد الصورة غير مدعوم. {current_user.get('ID')}")
        raise HTTPException(status_code=400, detail="امتداد الصورة غير مدعوم.")

    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            logger.warning("حجم الصورة كبير Jacket")
            await session.rollback()
            raise HTTPException(
                status_code=400, detail="حجم الصورة كبير جدًا (الحد 5MB)."
            )

        with open(file_path, "wb") as buffer:
            buffer.write(content)
            logger.info("تم حفظ الصورة بنجاح")

        await session.execute(
            update(Users)
            .where(Users.UserID == user_id)
            .values(profile_image=unique_filename)
        )
        await session.commit()
        logger.info("تم تحميل الصورة بنجاح")

        image_url = f"/static/profiles/{unique_filename}"

        logger.info("تم رفع الصورة بنجاح")
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
