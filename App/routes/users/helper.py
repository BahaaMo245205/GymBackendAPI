from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Depends, status
from fastapi.requests import Request
from dotenv import load_dotenv
from typing import Annotated
from jose import jwt
import hashlib
import os

security_scheme = HTTPBearer()

load_dotenv()


async def generate_password_hash(password: Annotated[str, None]) -> str:
    """Create password hash"""
    if not password:
        raise HTTPException(501, "Error hash password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hash_password


async def validate_password(hashedPassword: str, password: str) -> bool:
    if not hashedPassword and not password:
        raise HTTPException(501, "Error Chick password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hashedPassword == hash_password:
        return True

    return False


async def retrieve_client_ip(request: Request) -> str:

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
            str(os.getenv("SECRET_KEY")),
            algorithms=[str(os.getenv("ALGORITHM"))],
        )
        user_id: str = payload.get("sub").get("id")
        ipaddress: str = payload.get("sub").get("ip-address")
        if user_id is None or ipaddress != retrieve_client_ip(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="توكن غير صالح: البيانات ناقصة.",
            )

        return user_id

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error : {e}")

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="انتهت صلاحية التوكن، سجل دخول تاني يا بطل.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="التوكن ده مضروب وغير صالح! 🚨",
        )
