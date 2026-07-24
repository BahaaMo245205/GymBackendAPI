from fastapi import FastAPI
from contextlib import asynccontextmanager
from App.Database.db import create_db_and_table
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_table()
    yield


tags_metadata = [
    {
        "name": "Auth",
        "description": "عمليات تسجيل الدخول والتحقق من الهوية وتوليد الـ JWT Tokens لحماية النظام.",
    },
    {
        "name": "Admins",
        "description": "صلاحيات الإدارة العليا (RBAC) للتحكم في الكباتن، الموظفين، والتقارير المالية للنظام.",
    },
]

app = FastAPI(
    title="سيستم إدارة الجيم الاحترافي 🏋️‍♂️ REST API",
    description="""
هذا الـ API هو المحرك الخلفي الرئيسي لإدارة الصالات الرياضية، الاشتراكات، وحضور الكابتن واللاعبين بصلاحيات أمنية متكاملة.

## الميزات الحالية:
* **حماية مشددة:** تأمين كامل للمسارات باستخدام OAuth2 و JWT Tokens لمنع التلاعب بالاشتراكات.
* **إدارة ذكية لقواعد البيانات:** معمارية بيانات مرنة للتحكم في الكباتن، اللاعبين، وتتبع باقات الاشتراك الحالية.
* **أداء عالي وسريع:** معالجة البيانات بكفاءة عالية تدعم التوسع الفوري للأنظمة.
""",
    summary="الباك-إند الرئيسي لنظام إدارة الجيم والاشتراكات المتكامل",
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

from App.routes.classes import classes_router

app.include_router(classes_router.classes_router)

from App.routes.users import user_router

app.include_router(user_router.router_user)

from App.routes.admin import admin

app.include_router(admin.router_admin)

from App.routes.auth import auth

app.include_router(auth.auth_router)
