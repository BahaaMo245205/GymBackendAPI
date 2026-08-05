from fastapi import APIRouter, Depends, HTTPException, Request
from ...Database.db import get_async_session,Memberships
from sqlalchemy.ext.asyncio import AsyncSession
from ..users.helper import get_current_user
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from dotenv import load_dotenv
from ...app import logger
import stripe
import os

load_dotenv()


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
router_payment = APIRouter(prefix="/v1/api/payments", tags=["Payments"])


@router_payment.post("/create-checkout-session")
async def create_checkout_session(
    membership_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Memberships).where(Memberships.MembershipsID == membership_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="الباقة غير موجودة")

    user_id = current_user.get("ID")
    price_egp = int(membership.Price)  
    amount_piasters = price_egp * 100  
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "egp", 
                        "product_data": {
                            "name": f"اشتراك {membership.duration_months} شهور",
                            "description": membership.description or "باقة جيم",
                        },
                        "unit_amount": amount_piasters,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{os.getenv('FRONTEND_URL')}/payment-success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/memberships.html",
            metadata={
                "user_id": user_id,
                "membership_id": membership_id,
            },
        )
        logger.info(f"Checkout session created: {checkout_session.id}")
        return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))