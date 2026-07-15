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


async def create_reset_token(gmail: str | dict) -> str:
    """This functions for forgetting passwords"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"exp": expire, "sub": gmail, "action": "reset_password"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def verify_reset_token(token) -> str | None:
    """This functions for check JWT token & resetting passwords"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        if payload.get("action") != "reset_password":
            return None
        return payload.get("sub")
    except JWTError:
        return None


async def create_access_token(data: dict) -> str | None:
    """This function is for creating access token users"""

    if not data:
        return None

    access_payload = data.copy()
    access_payload.update({"exp": datetime.utcnow() + timedelta(minutes=15)})
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    refresh_payload = data.copy()
    refresh_payload.update({"exp": datetime.utcnow() + timedelta(days=7)})
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    return access_token ,refresh_token


async def retrieve_client_ip(request: Request) -> str:

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
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            str(os.getenv("SECRET_KEY")),
            algorithms=[str(os.getenv("ALGORITHM"))],
        )
        user_email: str = payload.get("sub")
        ipaddress: str = payload.get("ip-address")
        if user_email is None or ipaddress != retrieve_client_ip(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="توكن غير صالح: البيانات ناقصة.",
            )

        return user_email

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
