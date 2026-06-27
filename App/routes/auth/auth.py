from fastapi import APIRouter

auth_router = APIRouter(prefix="/v1/api/auth",tags=["Auth"])

@auth_router.post("/login")
def login(): pass

@auth_router.post("/register")
def register(): pass

@auth_router.post("/forgot-password")
def forgot_password(): pass

@auth_router.post("/reset-password")
def reset_password(): pass

@auth_router.post("/google/callback")
def google_callback(): pass