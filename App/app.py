from fastapi.middleware.cors import CORSMiddleware
from App.Database.db import create_db_and_table
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_table()
    yield


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

BASE_DIR = Path(__file__).resolve().parent
static_profiles = BASE_DIR  / "static"

app.mount("/static", StaticFiles(directory=str(static_profiles)), name="static")


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s",filemode='a',filename='app.log')
logger = logging.getLogger(__name__)

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
