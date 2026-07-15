from fastapi import APIRouter

router_admin = APIRouter(prefix="/v1/api/admin", tags=["Admins"])


@router_admin.post("/Membership_Management")
async def MembershipManagement(): ...


@router_admin.post("/Role")
async def Role(): ...

@router_admin.get("/Reports")
async def Reports():
    """This rourts for extracting reports """

@router_admin.post("/users/{user_id}/status")
async def user(user_id:int): ...

@router_admin.post("/classes")
async def classes(): ...


