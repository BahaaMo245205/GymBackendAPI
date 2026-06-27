from fastapi import FastAPI

app = FastAPI(version="0.0.1", description="API System Gym", title="API System Gym")

from App.routes.classes import classes_router

app.include_router(classes_router.classes_router)

from App.routes.users import user_router

app.include_router(user_router.router_user)

from App.routes.admin import admin

app.include_router(admin.router_admin)

from App.routes.auth import auth

app.include_router(auth.auth_router)
