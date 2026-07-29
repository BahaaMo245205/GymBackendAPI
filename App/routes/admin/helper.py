from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Depends, status
from ..auth.helper import get_current_user
from fastapi.requests import Request
from dotenv import load_dotenv
from jose import jwt
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ADMINID = os.getenv("ADMINID")

security_scheme = HTTPBearer()

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
            "Role": user_role
        }

    except Exception as e:
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


def ensure_admin_role(current_user: dict = Depends(get_current_user)) -> str:
    user_role = current_user.get("Role")
    user_id = current_user.get("ID")

    if user_role != "Admin" and user_id != ADMINID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="عفواً.. هذا المسار مخصص للأدمن فقط!",
        )

    return True


# def ensure_trainer_role(current_user: dict = Depends(get_current_user)) -> str:
#     user_role = current_user.get("Role")

#     if user_role != "Trainer":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="عفواً.. هذا المسار مخصص للمدربين فقط!",
#         )

#     return user_role
