import logging
import os
import re

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt,JWTError

logger = logging.getLogger(__name__)
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ADMINID = os.getenv("ADMINID")

security_scheme = HTTPBearer()
HttpSecurity = Depends(security_scheme)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = HttpSecurity,
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
            logger.warning("توكن غير صالح: البيانات ناقصة أو عنوان الـ IP غير مطبق.")
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
    except JWTError as jwterorr:
        logging.warning("Error JWT : {}".format(jwterorr))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error JWT: {}".format(jwterorr)
        )
    except Exception as e:
        logger.error(f"{e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="التوكن غير صالح أو انتهت صلاحيته.",
        )


def retrieve_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()

    return request.client.host if request.client else "unknown"


CurrentUser = Depends(get_current_user)


def ensure_admin_role(current_user: dict = CurrentUser) -> str:
    user_role = current_user.get("Role")
    user_id = current_user.get("ID")

    if user_role != "Admin" and user_id != ADMINID:
        logger.error(f"هذا المسار مخصص للأدمن فقط! {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="عفواً.. هذا المسار مخصص للأدمن فقط!",
        )

    return


def is_password_strong(password: str) -> bool:
    if len(password) < 8:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    return re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
