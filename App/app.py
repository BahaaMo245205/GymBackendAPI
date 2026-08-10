import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from App.Database.db import create_db_and_table
from App.redis_client import redis_client

from .limiter import custom_rate_limit_handler, limiter

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - (%(levelname)s)-> %(message)s",
    filename="app.log",
    filemode="a",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    await create_db_and_table()
    logger.info("Database ready")

    try:
        await redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    yield

    logger.info("Shutting down...")
    try:
        await redis_client.close()
        logger.info("Redis closed")
    except Exception as e:
        logger.error(f"Redis close error: {e}")

    logger.info("Shutdown complete")


# ---------- OpenAPI tags ----------
tags_metadata = [
    {
        "name": "Auth",
        "description": "تسجيل الدخول، التسجيل، Google OAuth، والتحقق من الهوية باستخدام JWT.",
    },
    {
        "name": "User",
        "description": "الملف الشخصي، تحديث البيانات، تغيير كلمة المرور، والحجوزات.",
    },
    {
        "name": "Admins",
        "description": "صلاحيات الإدارة: التقارير، المدربين، إدارة الاشتراكات والكلاسات.",
    },
    {
        "name": "Membership",
        "description": "عرض الباقات وإدارة اشتراكات المستخدم.",
    },
    {
        "name": "Classes",
        "description": "عرض الكلاسات وإدارة الحصص الرياضية.",
    },
    {
        "name": "Payments",
        "description": "Stripe Checkout وWebhook لتفعيل الاشتراكات وحجوزات الكلاسات.",
    },
]


# ---------- App ----------
app = FastAPI(
    title="سيستم إدارة الجيم الاحترافي 🏋️‍♂️ REST API",
    description="""
الـ Backend الرئيسي لإدارة الصالات الرياضية، الاشتراكات، الكلاسات، والمدفوعات.

### الميزات
- حماية المسارات بـ JWT + Bearer Auth
- اشتراكات وكلاسات مع Stripe
- تقارير للأدمن
- صلاحيات حسب الدور (User / Trainer / Admin)
""",
    summary="Backend لنظام إدارة الجيم والاشتراكات",
    version="1.0.0",
    terms_of_service="https://bahaadevs.com/gym-terms/",
    contact={
        "name": "الدعم الفني لنظام الجيم",
        "url": "https://bahaadevs.com/support",
        "email": "gym-support@bahaadevs.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


# ---------- Middleware ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Rate limit ----------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


# ---------- Static files ----------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------- Routers ----------
from App.routes.admin import admin
from App.routes.auth import auth
from App.routes.classes import classes_router
from App.routes.membership import route
from App.routes.payment import router
from App.routes.users import user_router

app.include_router(auth.auth_router)
app.include_router(user_router.router_user)
app.include_router(admin.router_admin)
app.include_router(route.router_membership)
app.include_router(classes_router.classes_router)
app.include_router(router.router_payment)
