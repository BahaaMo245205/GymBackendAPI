from .limiter import custom_rate_limit_handler, limiter
from fastapi.middleware.cors import CORSMiddleware
from App.Database.db import create_db_and_table
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from App.redis_client import redis_client
from fastapi import FastAPI
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - (%(levelname)s)-> %(message)s",
    filemode="a",
    filename="app.log",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client

    logger.info("Starting up and connecting to services...")

    await create_db_and_table()

    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis! 🟢")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")

    logger.info("Running app smoothly...")

    yield

    logger.info("Shutting down and cleaning up...")

    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed. 🔴")

    logger.info("App shutdown complete.")


tags_metadata = [
    {
        "name": "Auth",
        "description": "تسجيل الدخول، التسجيل، والتحقق من الهوية باستخدام JWT.",
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
        "description": "عرض الباقات، الاشتراك، وإدارة اشتراكات المستخدم.",
    },
    {
        "name": "Classes",
        "description": "عرض الكلاسات، الإنضمام، وإدارة الحصص الرياضية.",
    },
]
app = FastAPI(
    title="سيستم إدارة الجيم الاحترافي 🏋️‍♂️ REST API",
    description="""
الـ Backend الرئيسي لإدارة الصالات الرياضية، الاشتراكات، الكلاسات، والمستخدمين.

### الميزات:
- حماية المسارات بـ JWT + Bearer Auth
- إدارة الاشتراكات والكلاسات
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

BASE_DIR = Path(__file__).resolve().parent
static_profiles = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(static_profiles)), name="static")


from App.routes.classes import classes_router

app.include_router(classes_router.classes_router)

from App.routes.users import user_router

app.include_router(user_router.router_user)

from App.routes.admin import admin

app.include_router(admin.router_admin)

from App.routes.auth import auth

app.include_router(auth.auth_router)

from App.routes.membership import route

app.include_router(route.router_membership)

from App.routes.payment import router

app.include_router(router.router_payment)


