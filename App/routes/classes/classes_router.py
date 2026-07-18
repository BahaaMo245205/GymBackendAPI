from fastapi import APIRouter

classes_router = APIRouter(prefix="/v1/api/classes",tags=["Classes"])

@classes_router.get("/")
async def get_classes():
    ...

@classes_router.post("/{class_id}/book")
async def book_class(class_id: int): pass

@classes_router.delete("/{class_id}/cancel")
async def cancel_class(class_id: int): pass