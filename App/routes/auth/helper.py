from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from jose import jwt, JWTError
from dotenv import load_dotenv
from typing import Annotated,Union
import hashlib
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


def generate_password_hash(password: Annotated[str, None]) -> str:
    """Create password hash"""
    if not password:
        raise HTTPException(501, "Error hash password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hash_password


def validate_password(
    hashedPassword:str, password:str
) -> bool:
    if not hashedPassword and not password:
        raise HTTPException(501, "Error Chick password")

    hash_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hashedPassword == hash_password:
        return True

    return False


def create_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {"exp": expire, "sub": email, "action": "reset_password"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_reset_token(token) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        if payload.get("action") != "reset_password":
            return None
        return payload.get("sub")
    except JWTError:
        return None
