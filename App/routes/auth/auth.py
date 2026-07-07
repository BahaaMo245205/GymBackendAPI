from App.routes.auth.models import (
    ForgotPasswordSchema,
    LoginSchema,
    RegisterSchema,
    ResetPasswordSchema,
    RegisterSchemaOut,
)
from App.routes.auth.helper import (
    generate_password_hash,
    validate_password,
    create_reset_token,
    verify_reset_token,
)
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi import APIRouter, Depends, HTTPException, status,Query
from App.Database.db import get_async_session, Users
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from sqlalchemy import select
import os

load_dotenv()

auth_router = APIRouter(prefix="/v1/api/auth", tags=["Auth"])
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_PORT=587,
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True, 
    MAIL_SSL_TLS=False,  
    USE_CREDENTIALS=True
)

@auth_router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    login_user: LoginSchema, session: AsyncSession = Depends(get_async_session)
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

    # is_password_correct = validate_password(
    #     hashed_password=db_user.password, password=login_user.password
    # )

    if not validate_password(
        hashedPassword=db_user.password, password=login_user.password
    ):
        raise invalid_credentials_exception

    return {
        "status": "success",
        "message": "تم تسجيل الدخول بنجاح يا برنس!",
        "username": db_user.UserName,
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

        username = register.username
        email = register.email
        password = register.password
        confirm_password = register.confirm_password

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
    token:str=Query(),
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


@auth_router.post("/google/callback")
def google_callback():
    pass
