from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Depends, status
from ..auth.helper import get_current_user
from fastapi.requests import Request
from dotenv import load_dotenv
from jose import jwt
import os

load_dotenv()


security_scheme = HTTPBearer()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            str(os.getenv("SECRET_KEY")),
            algorithms=[str(os.getenv("ALGORITHM"))],
        )
        data_user: dict = payload.get("sub")

        if not data_user or not data_user.get("Email"):
            raise HTTPException(status_code=401, detail="بيانات التوكن ناقصة")

        if data_user.get("ip-address") != retrieve_client_ip(request):
            raise HTTPException(status_code=401, detail="محاولة اختراق: الـ IP متغير!")

        return data_user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="انتهت صلاحية التوكن.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="التوكن غير صالح.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ غير متوقع: {e}")


def retrieve_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()

    return request.client.host if request.client else "unknown"


def ensure_admin_role(current_user: dict = Depends(get_current_user)) -> str:
    user_role = current_user.get("user-role")

    if user_role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="عفواً.. هذا المسار مخصص للأدمن فقط!",
        )

    return user_role


def ensure_trainer_role(current_user: dict = Depends(get_current_user)) -> str:
    user_role = current_user.get("user-role")

    if user_role != "Trainer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="عفواً.. هذا المسار مخصص للمدربين فقط!",
        )

    return user_role
