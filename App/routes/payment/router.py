from fastapi import APIRouter, Depends, HTTPException, status
from App.routes.users.helper import get_current_user
from .models import PaymentRequest
from dotenv import load_dotenv
import stripe
import os

router_payment = APIRouter(prefix="/v1/api/payment", tags=["Payment"])

load_dotenv()
SECRET_KEY = os.getenv("API_SECRETE_STRIPE")
stripe.api_key = SECRET_KEY

@router_payment.post("/create-checkout-session")
async def create_checkout_session(
    data: PaymentRequest, user_id: str = Depends(get_current_user)
):
    try:
        # إنشاء رابط دفع تجريبي
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "egp",
                        "product_data": {
                            "name": data.membership_name,
                        },
                        "unit_amount": int(data.amount * 100),  # السعر بالقرش
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url="http://127.0.0.1:5500/success.html?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://127.0.0.1:5500/cancel.html",
        )
        return {"checkout_url": checkout_session.url}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
