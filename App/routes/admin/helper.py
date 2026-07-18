from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Depends, status
from ..auth.helper import get_current_user
from fastapi.requests import Request
from dotenv import load_dotenv
from jose import jwt
import os

load_dotenv()


security_scheme = HTTPBearer()


def retrieve_client_ip(request: Request) -> str:

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        x_real_ip.split(",")[0].strip()

    return request.client.host


def get_current_user_role(
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
        current_user_role: str = payload.get("sub").get("role-user")
        ipaddress: str = payload.get("sub").get("ip-address")
        if current_user_role is None or ipaddress != retrieve_client_ip(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="توكن غير صالح: البيانات ناقصة.",
            )

        return current_user_role

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
