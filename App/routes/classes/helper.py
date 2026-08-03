from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Depends, status
from fastapi.requests import Request
from dotenv import load_dotenv
from typing import Annotated
from ...app import logger
from jose import jwt
import hashlib
import os

security_scheme = HTTPBearer()

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def retrieve_client_ip(request: Request) -> str:

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        x_real_ip.split(",")[0].strip()

    return request.client.host


def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> str:
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
        logger.error("هناك مشكله في JWT Token : {}".format(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"التوكن غير صالح أو انتهت صلاحيته.",
        )
