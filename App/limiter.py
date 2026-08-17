from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379/0",
    default_limits=["100/minute"],
)


async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "detail": "انت بعت طلبات كتير أوي. استنى شوية وجرب تاني.",
        },
    )
