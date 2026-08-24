import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from celery import Celery
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jose import jwt

from ..routes.auth.helper import create_reset_token

SECRET_KEY = os.getenv("SECRET_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
logger = logging.getLogger(__name__)

load_dotenv()
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


app_celery = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", f"redis://{REDIS_HOST}:6379/0"),
    backend=os.getenv("CELERY_BACKEND_URL", f"redis://{REDIS_HOST}:6379/0"),
)


def create_reset_token(gmail: str | dict) -> str:
    """This functions for forgetting passwords"""
    expire = datetime.now(UTC) + timedelta(minutes=10)
    to_encode = {"exp": expire, "sub": gmail, "action": "reset_password"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _send_email_sync(message: MessageSchema) -> None:
    fm = FastMail(config=conf)
    asyncio.run(fm.send_message(message))


@app_celery.task
def sent_email(
    email_user: str,
    massage: str,
    status: list | None = None,
) -> None:
    if status is None:
        status = ["Unactiv", "Active", "Blocked", "Deleted", "Suspended", "Banned", "Pending", "Rejected", "Cancelled", "Expired", "Completed", "Failed"]
    try:
        message = MessageSchema(
            subject="Gym System - Welcome!",
            recipients=[email_user],
            body=massage,
            subtype=MessageType.html,
        )
        _send_email_sync(message)
        logger.info(f"Welcome email sent | {email_user} | status={status}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Welcome email error: {e}")
        raise


@app_celery.task(name="deliver_welcome_message")
def deliver_welcome_message(user_email: str) -> dict:
    try:
        message = MessageSchema(
            subject="Gym System - Welcome!",
            recipients=[user_email],
            body=f"""
            <h1>Hello {user_email.split('@')[0].title()}</h1>
            <p>Welcome to Gym system</p>
            """,
            subtype=MessageType.html,
        )
        _send_email_sync(message)
        logger.info(f"Welcome email sent | {user_email}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Welcome email error: {e}")
        raise


@app_celery.task(name="send_forgot_password_email")
def send_forgot_password_email(user_email: str) -> dict:
    try:
        token = create_reset_token(user_email)
        frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend}/reset-password.html?token={token}"

        message = MessageSchema(
            subject="Gym System - Reset Your Password",
            recipients=[user_email],
            body=f"""
            <h2>إعادة تعيين كلمة المرور</h2>
            <p><a href="{reset_link}">اضغط هنا لتغيير كلمة المرور</a></p>
            <p>الرابط صالح لمدة محدودة.</p>
            """,
            subtype=MessageType.html,
        )
        _send_email_sync(message)
        logger.info(f"Reset email sent | {user_email}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Reset email error: {e}")
        raise
