import os
from urllib.parse import urlencode

import httpx
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi_mail import ConnectionConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import get_current_user, retrieve_client_ip, is_password_strong

from App.Database.db import Users, get_async_session
from App.routes.auth.helper import (
    create_access_token,
    generate_password_hash,
    validate_password,
    verify_reset_token,
)
from App.routes.auth.models import (
    ForgotPasswordSchema,
    LoginSchema,
    RegisterSchema,
    ResetPasswordSchema,
)


from ...Tasks.task import send_forgot_password_email, deliver_welcome_message

from ...limiter import limiter

import logging

logger = logging.getLogger(__name__)
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "http://localhost:8000/v1/api/auth/google/callback"

auth_router = APIRouter(prefix="/v1/api/auth", tags=["Auth"])
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_PORT=465,
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
)


@auth_router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login(
    login_user: LoginSchema,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """تسجيل الدخول والتحقق من الهوية"""

    result = await session.execute(select(Users).where(Users.email == login_user.email))
    db_user = result.scalar_one_or_none()

    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="البريد الإلكتروني أو كلمة المرور غير صحيحة!",
    )

    if not db_user:
        raise invalid_credentials_exception

    is_password_correct = validate_password(
        hashedPassword=db_user.password,
        password=login_user.password,
    )
    if not is_password_correct:
        raise invalid_credentials_exception

    if hasattr(db_user, "is_active") and not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الحساب محظور. تواصل مع الإدارة.",
        )

    access_token, refresh_token = create_access_token(
        data={
            "ID": db_user.UserID,
            "Email": db_user.email,
            "UserName": db_user.UserName,
            "ip-address": retrieve_client_ip(request),
            "Role": db_user.Role,
        }
    )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="فشل إنشاء التوكن",
        )

    logger.info(f"Login success | user_id={db_user.UserID} | email={db_user.email}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "UserName": db_user.UserName,
        "token_type": "bearer",
    }


@auth_router.post("/register", status_code=201)
@limiter.limit("10/minute")
async def register(
    request: Request,
    register: RegisterSchema,
    session: AsyncSession = Depends(get_async_session),
):
    """تسجيل مستخدم جديد"""

    try:
        query = select(Users).where(Users.email == register.email)
        existing_user = await session.execute(query)
        existing_user_record = existing_user.scalar_one_or_none()
        if existing_user_record:
            raise HTTPException(
                status_code=400, detail="🚨 هذا البريد الإلكتروني مسجل بالفعل!"
            )

        username = register.username.title().strip()
        email = register.email.strip()
        password = register.password.strip()

        if not is_password_strong(password):
            raise HTTPException(status_code=400, detail="🚨 كلمة المرور ضعيفة!")

        if not username and not email and not password:
            raise HTTPException(status_code=401, detail="Please input all data !")

        add_user = Users(username, email, generate_password_hash(password), role="User")
        session.add(add_user)
        await session.commit()
        await session.refresh(add_user)

        logger.info("تم تسجيل الحساب بنجاح يا برنس!")
        deliver_welcome_message.delay(email)
        return {"status": "success", "message": "تم تسجيل الحساب بنجاح يا برنس!"}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error : {e}")
        raise HTTPException(status_code=500, detail=f"Error : {e}")


@auth_router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordSchema):
    send_forgot_password_email.delay(body.email)
    logger.info("إذا كان البريد الإلكتروني مسجلاً، فستتلقى رابطاً لإعادة التعيين.")
    return {
        "status": "success",
        "message": "إذا كان البريد الإلكتروني مسجلاً، فستتلقى رابطاً لإعادة التعيين.",
    }


@auth_router.post("/reset-password")
async def reset_password(
    token: str = Query(..., alias="token"),
    data: ResetPasswordSchema = None,
    session: AsyncSession = Depends(get_async_session),
):

    email = verify_reset_token(token)
    if not email:
        logger.error("🚨 الرابط غير صالح أو انتهت صلاحيته!")
        raise HTTPException(
            status_code=400, detail="🚨 الرابط غير صالح أو انتهت صلاحيته!"
        )

    query = select(Users).where(Users.email == email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        logger.error("المستخدم غير موجود")
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if not is_password_strong(data.new_password):
        logger.error("🚨 كلمة المرور ضعيفة!")
        raise HTTPException(status_code=400, detail="🚨 كلمة المرور ضعيفة!\nالكلمة المرور يجب ان يحتوي على 8 أحرف على الأقل")


    user.password = generate_password_hash(data.new_password)
    await session.commit()

    logger.info("تم تغيير كلمة المرور بنجاح يا برنس!")
    return {"status": "success", "message": "تم تغيير كلمة المرور بنجاح يا برنس!"}


@auth_router.get("/loginGoogle")
async def login_Google():
    """This's path for testing"""
    query_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    url = f"{os.getenv("GOOGLE_AUTH_ENDPOINT")}?{urlencode(query_params)}"
    return RedirectResponse(url)


@auth_router.get("/google/callback")
async def google_callback(
    code: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization Code مفقود")

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            logger.error("فشل التحقق من الكود مع جوجل: %s", token_response.text)
            raise HTTPException(status_code=400, detail="فشل التحقق من الكود مع جوجل")

        google_tokens = token_response.json()
        google_access_token = google_tokens.get("access_token")

        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
        )
        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=400, detail="فشل سحب بيانات المستخدم من جوجل"
            )

        google_user = user_info_response.json()

    email = (google_user.get("email") or "").strip()
    username = (google_user.get("name") or email.split("@")[0]).strip()

    if not email:
        raise HTTPException(status_code=400, detail="الإيميل غير متوفر من جوجل")

    result = await session.execute(select(Users).where(Users.email == email))
    db_user = result.scalar_one_or_none()
    


    if not db_user:
        random_password = generate_password_hash(os.urandom(16).hex())
        db_user = Users(
            username=username.title(),
            email=email,
            password=random_password,
            role="User",
            profile_image=google_user.get("picture"),
        )
        try:
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
            logger.info("تم إنشاء حساب جوجل جديد: %s", email)
            deliver_welcome_message.delay(email)
        except Exception as e:
            await session.rollback()
            logger.error("خطأ أثناء تسجيل حساب جوجل: %s", e)
            raise HTTPException(status_code=500, detail="خطأ أثناء تسجيل حساب جوجل")

    # else:
    #     return RedirectResponse(url="http://localhost:5500/Frontend/email-exists.html", status_code=302)
        
    app_access_token, app_refresh_token = create_access_token(
        {
            "ID": db_user.UserID,
            "UserName": getattr(db_user, "UserName", None)
            or getattr(db_user, "username", username),
            "Email": email,
            "ip-address": retrieve_client_ip(request),
            "Role": getattr(db_user, "Role", None) or getattr(db_user, "role", "User"),
        }
    )

    logger.info("تم تسجيل الدخول بواسطة جوجل بنجاح: %s", email)

    redirect_url = (
        f"http://localhost:5500/Frontend/login.html"
        f"?access_token={app_access_token}&refresh_token={app_refresh_token}"
    )
    return RedirectResponse(url=redirect_url)


@auth_router.get("/check", status_code=status.HTTP_200_OK)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {
        "Info": current_user,
        "message": "Welcome to your profile!",
    }
