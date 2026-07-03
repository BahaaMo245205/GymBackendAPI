from App.routes.auth.models import ForgotPasswordSchema,LoginSchema,RegisterSchema,ResetPasswordSchema,RegisterSchemaOut
from App.routes.auth.helper import genrate_password_hash,chick_password
from App.Database.db import get_async_session ,Users
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, Union


auth_router = APIRouter(prefix="/v1/api/auth", tags=["Auth"])


@auth_router.post("/login")
async def login():
    pass


@auth_router.post("/register", status_code=201)
async def register(register: RegisterSchema,session:AsyncSession=Depends(get_async_session)) :
    """Create User"""
    
    try :
        query = select(Users).where(Users.email == register.email)
        existing_user = await session.execute(query)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="🚨 هذا البريد الإلكتروني مسجل بالفعل!"
            )
        
        username = register.username
        email = register.email
        password = register.password
        confirm_password = register.confirm_password

        if not username and not email and not password and not confirm_password:
            raise HTTPException(status_code=401, detail="Please input all data !")


        
        add_user = Users(
            username,
            email,
            genrate_password_hash(password)
        )
        session.add(add_user)
        await session.commit()
        session.refresh(add_user)
        
        return {"status": "success", "message": "تم تسجيل الحساب بنجاح يا برنس!"}
        
    except Exception as e :
        raise HTTPException(status_code=500,detail=f"Error : {e}")
    

    

# @auth_router.post("/forgot-password")
# def forgot_password():
#     pass


# @auth_router.post("/reset-password")
# def reset_password():
#     pass


# @auth_router.post("/google/callback")
# def google_callback():
#     pass
