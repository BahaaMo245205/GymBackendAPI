from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    membership_id: str
    amount: float
    membership_name: str
    user_id: str
