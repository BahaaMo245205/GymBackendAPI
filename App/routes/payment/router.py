import os
from datetime import datetime, timedelta

import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...app import logger
from ...Database.db import (Booking, Classes, Memberships, Payments,
                            Subscriptions, get_async_session)
from ...redis import redis_client
from ..users.helper import get_current_user

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")

router_payment = APIRouter(prefix="/v1/api/payments", tags=["Payments"])


@router_payment.post("/create-checkout-session")
async def create_checkout_session(
    pay_type: str,  # "membership" | "class"
    item_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    user_id = current_user.get("ID") or current_user.get("UserID")
    if not user_id:
        logger.warning("المستخدم غير معروف")
        raise HTTPException(status_code=401, detail="المستخدم غير معروف")

    if pay_type not in ("membership", "class"):
        logger.warning("pay_type غير صالح: %s", pay_type)
        raise HTTPException(status_code=400, detail="pay_type غير صالح")

    duration_days = None
    name = ""
    description = ""
    price = 0

    if pay_type == "membership":
        await redis_client.delete(f"user:subscriptions:{user_id}")

        result = await session.execute(
            select(Memberships).where(Memberships.MembershipsID == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            logger.warning("الباقة غير موجودة | id=%s", item_id)
            raise HTTPException(status_code=404, detail="الباقة غير موجودة")

        active = await session.execute(
            select(Subscriptions).where(
                Subscriptions.UserID == user_id,
                Subscriptions.EndDate > datetime.now(),
                Subscriptions.status == "active",
            )
        )
        if active.scalars().first():
            logger.warning("اشتراك ساري موجود | user=%s", user_id)
            raise HTTPException(status_code=400, detail="لديك اشتراك ساري بالفعل")

        name = f"اشتراك {item.duration_months} شهور"
        description = item.description or "باقة جيم"
        price = int(item.Price)
        duration_days = int(item.duration_months) * 30

    else: 
        await redis_client.delete(f"user:bookings:{user_id}")
        result = await session.execute(
            select(Classes).where(Classes.ClassesID == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            logger.warning("الكلاس غير موجود | id=%s", item_id)
            raise HTTPException(status_code=404, detail="الكلاس غير موجود")

        existing = await session.execute(
            select(Booking).where(
                Booking.UserID == user_id,
                Booking.ClassID == item_id,
                Booking.Is_active == True,  
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="لديك حجز نشط على هذا الكلاس بالفعل",
            )

        name = item.ClassName
        description = f"{item.TypeClass} | {item.Start_time} - {item.End_time}"
        price = int(item.Price)

    amount = price * 100
    frontend = os.getenv("FRONTEND_URL", "http://localhost:5500/Frontend")

    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "egp",
                        "product_data": {"name": name, "description": description},
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{frontend}/payment-success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend}/{'memberships' if pay_type == 'membership' else 'classes'}.html",
            client_reference_id=str(user_id),
            metadata={
                "type": pay_type,
                "user_id": str(user_id),
                "item_id": str(item_id),
            },
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail=str(e.user_message or e))

    try:
        if pay_type == "membership":
            await redis_client.delete(f"user:subscriptions:{user_id}")

            sub = Subscriptions(
                userid=user_id,
                membershipsid=item_id,
                startdate=datetime.now(),
                enddate=datetime.now() + timedelta(days=duration_days),
                status="pending",
            )
            session.add(sub)
            await session.flush()



        else:
            await redis_client.delete(f"user:bookings:{user_id}")
            booking = Booking(
                userid=user_id,
                classid=item_id,
                is_active=False,
                date=datetime.now(),
            )
            session.add(booking)
            await session.flush()

        logger.info(
            f"Checkout created | type={pay_type} | user={user_id} | item={item_id} | "
            f"stripe={checkout.id}"
        )
        await session.commit()

    except Exception as e:
        await session.rollback()
        logger.error(f"DB error after checkout create: {e}")
        raise HTTPException(status_code=500, detail="فشل حفظ الطلب")

    logger.info(
        f"Checkout created | type={pay_type} | user={user_id} | item={item_id} | "
        f"stripe={checkout.id}"
    )

    return {
        "status": "success",
        "checkout_url": checkout.url,
        "session_id": checkout.id,
    }


@router_payment.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    payload = await request.body()
    logger.info(f"Webhook payload: {payload}")
    sig = request.headers.get("stripe-signature")
    logger.info(f"Webhook signature: {sig}")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        logger.info(f"Webhook event: {event}")
    except Exception as e:
        logger.error(f"Webhook signature error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":

        checkout = event["data"]["object"]
        logger.info(f"Webhook | checkout={checkout}")

        raw_meta = getattr(checkout, "metadata", None)
        if raw_meta is None and isinstance(checkout, dict):
            raw_meta = checkout.get("metadata")

        if raw_meta is None:
            meta = {}
        elif isinstance(raw_meta, dict):
            meta = raw_meta
        elif hasattr(raw_meta, "to_dict"):
            meta = raw_meta.to_dict()
        else:
            meta = {}
            try:
                for key in raw_meta.keys():
                    meta[key] = raw_meta[key]
            except Exception as e:
                logger.error(f"metadata parse error: {e}")
                meta = {}

        payment_status = getattr(checkout, "payment_status", None)
        if payment_status is None and isinstance(checkout, dict):
            payment_status = checkout.get("payment_status")
            logger.info(f"Webhook | payment_status={payment_status}")

        checkout_id = getattr(checkout, "id", None)
        if checkout_id is None and isinstance(checkout, dict):
            checkout_id = checkout.get("id")
            logger.info(f"Webhook | checkout_id={checkout_id}")

        logger.info(f"Webhook | id={checkout_id} | paid={payment_status} | meta={meta}")

        if payment_status and payment_status != "paid":
            return JSONResponse({"status": "ignored_not_paid"})

        pay_type = meta.get("type")
        user_id = meta.get("user_id")
        item_id = meta.get("item_id")

        if not pay_type or not user_id or not item_id:
            logger.error(f"missing metadata | meta={meta}")
            return JSONResponse({"status": "missing_metadata"})

        try:
            if pay_type == "membership":
                await redis_client.delete(f"user:subscriptions:{user_id}")
                result = await db.execute(
                    select(Subscriptions).where(
                        Subscriptions.UserID == user_id,
                        Subscriptions.membershipsID == item_id,
                        Subscriptions.status == "pending",
                    )
                )
                get_price = select(Memberships).where(
                    Memberships.MembershipsID == item_id
                )
                price = await db.execute(get_price)
                price = price.scalar_one_or_none()
                sub = result.scalars().first()
                if sub:
                    sub.status = "active"
                    payment = Payments(
                            date=datetime.now(),
                            price=price.Price,
                            typepay="Card",
                            subscription_id=sub.SubscriptionsID,
                    )
                    db.add(payment)
                    await db.commit()
                    logger.info(f"Membership activated | user={user_id}")
                else:
                    logger.warning("Pending subscription not found")

            elif pay_type == "class":
                await redis_client.delete(f"user:bookings:{user_id}")
                result = await db.execute(
                    select(Booking).where(
                        Booking.UserID == user_id,
                        Booking.ClassID == item_id,
                        Booking.Is_active == False,
                    )
                )
                booking = result.scalars().first()
                if booking:
                    booking.Is_active = True
                    await db.commit()
                    logger.info(f"Class booking activated | user={user_id}")
                else:
                    logger.warning("Pending booking not found")

            try:
                await redis_client.delete(f"user:subscriptions:{user_id}")
                await redis_client.delete(f"user:bookings:{user_id}")
            except Exception:
                pass

        except Exception as e:
            await db.rollback()
            logger.error(f"Webhook DB error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({"status": "ok"})


@router_payment.get("/session/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        s = stripe.checkout.Session.retrieve(session_id)

        raw_meta = getattr(s, "metadata", None)
        if raw_meta is None:
            meta = {}
        elif isinstance(raw_meta, dict):
            meta = raw_meta
        elif hasattr(raw_meta, "to_dict"):
            meta = raw_meta.to_dict()
        else:
            meta = {}
            try:
                for key in raw_meta.keys():
                    meta[str(key)] = raw_meta[key]
            except Exception:
                meta = {}

        return {
            "status": "success",
            "payment_status": s.payment_status,
            "type": meta.get("type"),
            "item_id": meta.get("item_id"),
        }
    except Exception as e:
        logger.error(f"Stripe session status error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
