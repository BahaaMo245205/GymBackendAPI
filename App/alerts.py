import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from App.Database.db import Subscriptions, Users, async_session_maker
from App.redis import redis_client
from App.Tasks.task import sent_email

logger = logging.getLogger(__name__)

EMAIL_EXPIRED = """
<h1>Gym System</h1>
<p>انتهى اشتراكك. رقم الاشتراك: {}</p>
"""

EMAIL_REMINDER = """
<h1>Gym System</h1>
<p>تذكير: اشتراكك هينتهي خلال أيام. رقم الاشتراك: {}</p>
"""


async def _get_session() -> AsyncSession:
    """جلسة يدوية — مش Depends"""
    return async_session_maker()


async def expire_subscriptions_job():
    logger.info("Job: expire subscriptions")
    session = async_session_maker()
    try:
        result = await session.execute(
            select(Subscriptions).where(
                Subscriptions.status == "active",
                Subscriptions.EndDate < datetime.now(),
            )
        )
        subscriptions = result.scalars().all()

        for sub in subscriptions:
            sub.status = "expired"

            user_result = await session.execute(
                select(Users).where(Users.UserID == sub.UserID)
            )
            user = user_result.scalar_one_or_none()
            if user and user.email:
                sent_email.delay(
                    user.email,
                    EMAIL_EXPIRED.format(sub.SubscriptionsID),
                    "Subscription Expired",
                )

        await session.commit()
        logger.info(f"Expired {len(subscriptions)} subscriptions")
    except Exception as e:
        await session.rollback()
        logger.error(f"expire_subscriptions_job failed: {e}")
    finally:
        await session.close()


async def reminder_before_subscription_ends():
    logger.info("Job: reminder before subscription ends")
    session = async_session_maker()
    try:
        now = datetime.now()
        result = await session.execute(
            select(Subscriptions).where(
                Subscriptions.status == "active",
                Subscriptions.EndDate > now,
                Subscriptions.EndDate <= now + timedelta(days=7),
            )
        )
        subscriptions = result.scalars().all()

        for sub in subscriptions:
            user_result = await session.execute(
                select(Users).where(Users.UserID == sub.UserID)
            )
            user = user_result.scalar_one_or_none()
            if user and user.email:
                sent_email.delay(
                    user.email,
                    EMAIL_REMINDER.format(sub.SubscriptionsID),
                    "Subscription Reminder",
                )

        logger.info(f"Reminders sent: {len(subscriptions)}")
    except Exception as e:
        logger.error(f"reminder job failed: {e}")
    finally:
        await session.close()


async def clear_redis_cache_job():
    logger.info("Job: clear redis cache")
    try:
        await redis_client.delete("all_classes")
        await redis_client.delete("all_trainers")
        await redis_client.delete("all_memberships")
        await redis_client.delete("all_system_users")
        logger.info("Redis cache cleared")
    except Exception as e:
        logger.error(f"clear_redis_cache_job failed: {e}")
