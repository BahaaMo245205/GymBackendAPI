from fastapi import FastAPI
from contextlib import asynccontextmanager
from App.Database.db import create_db_and_table

@asynccontextmanager
async def lifespan (app:FastAPI):
    await create_db_and_table()
    yield
    

app = FastAPI(version="0.0.1", description="API System Gym", title="API System Gym",lifespan=lifespan)

from App.routes.classes import classes_router

app.include_router(classes_router.classes_router)

from App.routes.users import user_router

app.include_router(user_router.router_user)

from App.routes.admin import admin

app.include_router(admin.router_admin)

from App.routes.auth import auth

app.include_router(auth.auth_router)
