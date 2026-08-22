import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from App.Database.db import create_db_and_table
from App.redis import redis_client

from .alerts import (
    clear_redis_cache_job,
    expire_subscriptions_job,
    reminder_before_subscription_ends,
)
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
scheduler = AsyncIOScheduler()


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
    try:

        scheduler.start()
        logger.info("Scheduler started")
        scheduler.add_job(expire_subscriptions_job, "interval", hours=24)
        scheduler.add_job(
            reminder_before_subscription_ends, "interval", hours=24, minutes=30
        )
        scheduler.add_job(clear_redis_cache_job, "interval", hours=24)
        logger.info("Jobs added to scheduler")
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")

    yield

    logger.info("Shutting down...")
    scheduler.shutdown()
    logger.info("Scheduler shutdown")

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
from App.routes.admin import router as admin
from App.routes.auth import router as auth
from App.routes.classes import router as classes_router
from App.routes.membership import router as membership_router
from App.routes.payment import router
from App.routes.users import router as user_router

app.include_router(auth.auth_router)
app.include_router(user_router.router_user)
app.include_router(admin.router_admin)
app.include_router(membership_router.router_membership)
app.include_router(classes_router.classes_router)
app.include_router(router.router_payment)
