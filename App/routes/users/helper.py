from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Depends, status
from fastapi.requests import Request
from dotenv import load_dotenv
from typing import Annotated
from jose import jwt
import hashlib
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security_scheme = HTTPBearer()
load_dotenv()


def generate_password_hash(password: Annotated[str, None]) -> str:
    """Create password hash"""
    if not password:
        raise HTTPException(501, "Error hash password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hash_password


def validate_password(hashedPassword: str, password: str) -> bool:
    if not hashedPassword and not password:
        raise HTTPException(501, "Error Chick password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hashedPassword == hash_password:
        return True

    return False


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
