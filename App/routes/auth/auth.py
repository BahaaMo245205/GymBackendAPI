from App.routes.auth.models import (
    ForgotPasswordSchema,
    ResetPasswordSchema,
    RegisterSchema,
    LoginSchema,
)
from App.routes.auth.helper import (
    generate_password_hash,
    create_access_token,
    create_reset_token,
    verify_reset_token,
    retrieve_client_ip,
    validate_password,
    get_current_user,
)
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Query
from App.Database.db import get_async_session, Users,UserProfile
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import RedirectResponse
from fastapi.requests import Request
from urllib.parse import urlencode
from dotenv import load_dotenv
from sqlalchemy import select
import httpx
import os

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "http://localhost:8000/v1/api/auth/google/callback"

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

auth_router = APIRouter(prefix="/v1/api/auth", tags=["Auth"])
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_PORT=587,
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


@auth_router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    login_user: LoginSchema,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """تسجيل الدخول والتحقق من الهوية بأمان تام"""

    query = select(Users).where(Users.email == login_user.email)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="🚨 البريد الإلكتروني أو كلمة المرور غير صحيحة!",
    )

    if not db_user:
        raise invalid_credentials_exception

    is_password_correct = validate_password(
        hashedPassword=db_user.password, password=login_user.password
    )

    if not is_password_correct:
        raise invalid_credentials_exception

    access_token, refresh_token = create_access_token(
        data={
            "sub": {
                "ID":db_user.UserID,
                "Email": db_user.email,
                "UserName": db_user.UserName,
                "ip-address": retrieve_client_ip(request),
            }
        }
    )
    if not access_token:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error access token",
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@auth_router.post("/register", status_code=201)
async def register(
    register: RegisterSchema, session: AsyncSession = Depends(get_async_session)
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
        confirm_password = register.confirm_password.strip()

        if not username and not email and not password and not confirm_password:
            raise HTTPException(status_code=401, detail="Please input all data !")

        add_user = Users(username, email, generate_password_hash(password))
        session.add(add_user)
        await session.commit()
        await session.refresh(add_user)

        return {"status": "success", "message": "تم تسجيل الحساب بنجاح يا برنس!"}

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error : {e}")


@auth_router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordSchema, session: AsyncSession = Depends(get_async_session)
):
    query = select(Users).where(Users.email == data.email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return {
            "status": "success",
            "message": "إذا كان البريد الإلكتروني مسجلاً، فستتلقى رابطاً لإعادة التعيين.",
        }

    token = create_reset_token(user.email)
    reset_link = f"http://localhost:3000/reset-password?token={token}"

    message = MessageSchema(
        subject="Gym System - Reset Your Password",
        recipients=[user.email],
        body=f"{token}",
        subtype=MessageType.html,
    )

    fm = FastMail(config=conf)
    await fm.send_message(message)

    return {
        "status": "success",
        "message": "إذا كان البريد الإلكتروني مسجلاً، فستتلقى رابطاً لإعادة التعيين.",
    }


@auth_router.post("/reset-password")
async def reset_password(
    data: ResetPasswordSchema,
    token: str = Query(),
    session: AsyncSession = Depends(get_async_session),
):

    email = verify_reset_token(token)
    if not email:
        raise HTTPException(
            status_code=400, detail="🚨 الرابط غير صالح أو انتهت صلاحيته!"
        )

    query = select(Users).where(Users.email == email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    user.password = generate_password_hash(data.new_password)
    await session.commit()

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
    code: str, request: Request, session: AsyncSession = Depends(get_async_session)
):
    if not code:
        raise HTTPException(status_code=400, detail="🚨 الـ Authorization Code مفقود!")

    token_url: str = "https://oauth2.googleapis.com/token"
    token_data: dict = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="🚨 فشل التحقق من الكود مع سيرفرات جوجل",
            )

        tokens: dict = token_response.json()
        access_token: str = tokens.get("access_token")

        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        user_info_response = await client.get(user_info_url, headers=headers)
        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="🚨 فشل سحب بيانات المستخدم من جوجل",
            )

        google_user: dict = user_info_response.json()
        print(google_user)

    email: str = google_user.get("email")
    username: str = google_user.get("name")
    

    query = select(Users).where(Users.email == email)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        random_password: str = generate_password_hash(os.urandom(16).hex())

        db_user = Users(
            username=username.title().strip(),
            email=email.strip(),
            password=random_password.strip(),
        )

        try:
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
        except Exception:
            await session.rollback()
            raise HTTPException(
                status_code=500, detail="خطأ أثناء تسجيل حساب جوجل في الداتابيز"
            )

        access_token , refresh_token = create_access_token(
            {
                "id":db_user.UserID,
                "username": db_user.UserName,
                "email": db_user.email,
                "ip-address": retrieve_client_ip(request),
            }
        )

    return {
        "status": "success",
        "message": "تم تسجيل الدخول بواسطة جوجل بنجاح!",
        "token": access_token,
    }


@auth_router.get("/check")
async def read_users_me(current_user: str = Depends(get_current_user)):
    return {"user_email": current_user, "message": "Welcome to your profile!"}
