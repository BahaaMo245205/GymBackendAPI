from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.requests import Request
from dotenv import load_dotenv
from jose import jwt, JWTError
from typing import Annotated
import hashlib
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security_scheme = HTTPBearer()


def retrieve_client_ip(request: Request) -> str:

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        x_real_ip.split(",")[0].strip()

    return request.client.host


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            key=str(SECRET_KEY),
            algorithms=[str(ALGORITHM)],
        )

        user_id = payload.get("ID")
        user_email = payload.get("Email")
        user_name = payload.get("UserName")
        ipaddress = payload.get("ip-address")
        user_role = payload.get("Role")

        if user_email is None or ipaddress != retrieve_client_ip(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="توكن غير صالح: البيانات ناقصة أو عنوان الـ IP غير مطبق.",
            )

        return {
            "ID": user_id,
            "Email": user_email,
            "UserName": user_name,
            "Role": user_role,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="التوكن غير صالح أو انتهت صلاحيته.",
        )


def get_current_user_id(get_current_user: dict = Depends(get_current_user)) -> str:
    if not get_current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return get_current_user.get("ID")
