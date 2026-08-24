import hashlib
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

from dotenv import load_dotenv
from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_password_hash(password: Annotated[str, None]) -> str:
    """Create password hash"""
    if not password:
        logger.error("خطأ في كلمة المرور")
        raise HTTPException(501, "Error hash password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    # hash_password = pwd_context.hash(hash_password)
    logger.info("تم أنشاء الكلمة المرور بنجاح")
    return hash_password


def validate_password(hashedPassword: str, password: str) -> bool:
    if not hashedPassword and not password:
        logger.error("خطأ في كلمة المرور")
        raise HTTPException(501, "Error Chick password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hashedPassword == hash_password:
        return True

    # hash_password = pwd_context.hash(hash_password)
    # if pwd_context.verify(hash_password, hashedPassword):
    #     return True

    logger.error("🚨 كلمة المرور غير صحيحة!")
    return False


def create_reset_token(gmail: str | dict) -> str:
    """This functions for forgetting passwords"""
    expire = datetime.now(UTC) + timedelta(minutes=10)
    to_encode = {"exp": expire, "sub": gmail, "action": "reset_password"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_reset_token(token) -> str | None:
    """This functions for check JWT token & resetting passwords"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        if payload.get("action") != "reset_password":
            return None
        return payload.get("sub")
    except JWTError:
        logger.error("🚨 الرابط غير صالح أو انتهت صلاحيته!")
        return None


def create_access_token(data: dict) -> str | None:
    """This function is for creating access token users"""

    if not data:
        return None

    access_payload = data.copy()
    access_payload.update({"exp": datetime.now(UTC) + timedelta(minutes=15)})
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)

    refresh_payload = data.copy()
    refresh_payload.update({"exp": datetime.now(UTC) + timedelta(days=7)})
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

    return access_token, refresh_token
