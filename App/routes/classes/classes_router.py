from fastapi import APIRouter

classes_router = APIRouter(prefix="/v1/api/classes",tags=["Classes"])

@classes_router.get("/")
def get_classes(): pass

@classes_router.post("/{class_id}/book")
def book_class(class_id: int): pass

@classes_router.delete("/{class_id}/cancel")
def cancel_class(class_id: int): pass