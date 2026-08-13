import json

from fastapi import APIRouter, Depends, Path
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...app import logger, redis_client
from ...Database.db import Classes, Memberships, Subscriptions
from ...Database.db import Users as Us
from ...Database.db import get_async_session
from .helper import *
from .models import (
    ClassCreateSchema,
    ClassUpdateSchema,
    MembershipDetails,
    RoleUpdateSchema,
    UserStatusUpdate,
)

router_admin = APIRouter(prefix="/v1/api/admin", tags=["Admins"])


@router_admin.get("/users", status_code=status.HTTP_200_OK)
async def get_all_users(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    chick_role: str = Depends(ensure_admin_role),
):
    admin_id = current_user.get("ID") or current_user.get("UserID")
    cache_key = "all_system_users"

    try:
        cached_users = await redis_client.get(cache_key)
        if cached_users:
            logger.info(f"Admin {admin_id} fetched users list from Redis ⚡")
            users_data = json.loads(cached_users)
            return {
                "status": "success",
                "count": len(users_data),
                "users": users_data,
            }
    except Exception as e:
        logger.error(f"Redis get error: {e}")

    try:
        query = select(Us)
        result = await session.execute(query)
        users = result.scalars().all()

        users_list = []
        for user in users:
            users_list.append(
                {
                    "UserID": user.UserID,
                    "UserName": user.UserName,
                    "Email": getattr(user, "Email", None)
                    or getattr(user, "email", None),
                    "Role": user.Role,
                    "profile_image": getattr(user, "profile_image", None),
                    "is_active": getattr(user, "is_active", True),
                }
            )

        try:
            await redis_client.set(cache_key, json.dumps(users_list), ex=300)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

        logger.info(
            f"Admin {admin_id} fetched users list from DB | count={len(users_list)}"
        )

        return {
            "status": "success",
            "count": len(users_list),
            "users": users_list,
        }

    except Exception as e:
        logger.error(f"Failed to fetch users | admin={admin_id} | error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب المستخدمين: {str(e)}",
        )


@router_admin.post("/memberships", status_code=status.HTTP_201_CREATED)
async def membership_management(
    membership_details: MembershipDetails,
    session: AsyncSession = Depends(get_async_session),
):

    add_membership = Memberships(
        price=membership_details.Price,
        duration_months=membership_details.duration_months,
        walk_machine=membership_details.walk_machine,
        deduct=membership_details.deduct,
        description=membership_details.description,
        is_active=True,
    )

    try:
        session.add(add_membership)
        await session.commit()
        await session.refresh(add_membership)

        logger.info("تم إضافة الباقة بنجاح")
        await redis_client.delete("all_memberships")
        return {
            "status": "success",
            "message": "تم إضافة الباقة بنجاح",
            "data": add_membership,
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"حدث خطأ أثناء إضافة الباقة: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حفظ الباقة في قاعدة البيانات",
        )


@router_admin.put("/memberships/{membership_id}", status_code=status.HTTP_200_OK)
async def update_membership(
    membership_id: str = Path(..., title="ID الخاص بالباقة"),
    update_data: MembershipDetails = None,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Memberships).where(Memberships.MembershipsID == membership_id)
    result = await session.execute(query)
    db_membership = result.scalar_one_or_none()

    if not db_membership:
        logger.error("الباقة دي مش موجودة!")
        raise HTTPException(status_code=404, detail="الباقة دي مش موجودة!")

    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_membership, key, value)

    try:
        await session.commit()
        await session.refresh(db_membership)
        await redis_client.delete("all_memberships")
        logger.info("تم تحديث الباقة بنجاح")

        return {
            "status": "success",
            "message": "تم تحديث الباقة بنجاح",
            "data": db_membership,
        }
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تحديث الباقة: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="مشكلة في تحديث البيانات")


@router_admin.delete("/memberships/{membership_id}", status_code=status.HTTP_200_OK)
async def delete_membership(
    membership_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(ensure_admin_role),
):
    query = select(Memberships).where(Memberships.MembershipsID == membership_id)
    result = await session.execute(query)
    db_membership = result.scalar_one_or_none()

    if not db_membership:
        logger.warning(f"Delete membership failed | id={membership_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الباقة دي مش موجودة، اتأكد من الـ ID",
        )

    subs_count_result = await session.execute(
        select(func.count(Subscriptions.SubscriptionsID)).where(
            Subscriptions.membershipsID == membership_id
        )
    )
    subs_count = subs_count_result.scalar() or 0

    if subs_count > 0:
        logger.warning(
            f"Delete membership blocked | id={membership_id} | linked_subscriptions={subs_count}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"لا يمكن حذف الباقة لأنها مرتبطة بـ {subs_count} اشتراك. أوقف الباقة بدل الحذف.",
        )

    try:
        await session.delete(db_membership)
        await session.commit()

        await redis_client.delete("all_memberships")

        logger.info(f"Membership deleted successfully | id={membership_id}")
        return {
            "status": "success",
            "message": "تم حذف الباقة نهائياً من السيستم",
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"Delete membership error | id={membership_id} | error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء محاولة الحذف",
        )


@router_admin.patch("/ChangeRole/{UserID}", status_code=status.HTTP_200_OK)
async def change_user_role(
    UserID: str,
    role_data: RoleUpdateSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    check_role: dict = Depends(ensure_admin_role),
):
    admin_id = current_user.get("ID") or current_user.get("UserID")

    if admin_id == UserID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="لا يمكنك تغيير صلاحيتك بنفسك.",
        )

    allowed_roles = {"User", "Trainer", "Admin"}
    if role_data.new_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"الصلاحية غير صالحة. المسموح: {', '.join(allowed_roles)}",
        )

    query = select(Us).where(Us.UserID == UserID)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم المراد تعديل صلاحيته غير موجود في النظام",
        )

    old_role = db_user.Role
    db_user.Role = role_data.new_role

    try:
        await session.commit()
        await session.refresh(db_user)

        logger.info(
            f"Admin {admin_id} changed role of user {UserID} from {old_role} to {db_user.Role}"
        )
        await redis_client.delete("all_system_users")
        await redis_client.delete("all_trainers")
        return {
            "status": "success",
            "message": f"تم بنجاح تغيير صلاحية المستخدم إلى: {db_user.Role}",
            "user_id": db_user.UserID,
            "old_role": old_role,
            "updated_role": db_user.Role,
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"حدث خطأ أثناء تحديث الصلاحية: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تحديث الصلاحية في قاعدة البيانات: {str(e)}",
        )


@router_admin.post("/Role", status_code=status.HTTP_200_OK)
async def get_admin_role_info(
    current_user: dict = Depends(ensure_admin_role),
):
    """
    التحقق من أن المستخدم الحالي أدمن وإرجاع بياناته الأساسية.
    """
    user_id = current_user.get("ID") or current_user.get("UserID")
    role = current_user.get("user-role") or current_user.get("Role") or "Admin"
    email = current_user.get("Email")

    logger.info(
        f"Admin role check success | user_id={user_id} | role={role} | email={email}"
    )

    return {
        "status": "success",
        "message": "تم التحقق من الصلاحية بنجاح",
        "assigned_role": role,
        "user_id": user_id,
        "email": email,
    }


@router_admin.get("/Reports", status_code=status.HTTP_200_OK)
async def get_system_reports(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(ensure_admin_role),
):
    try:
        logger.info(f" requested system reports")

        users_result = await session.execute(select(func.count(Us.UserID)))
        total_users = users_result.scalar() or 0

        active_subs_result = await session.execute(
            select(func.count(Subscriptions.SubscriptionsID)).where(
                Subscriptions.status == "active"
            )
        )
        active_subscriptions = active_subs_result.scalar() or 0

        classes_result = await session.execute(
            select(func.count(Classes.ClassesID)).where(Classes.Is_active == True)
        )
        total_active_classes = classes_result.scalar() or 0

        revenue_result = await session.execute(
            select(func.coalesce(func.sum(Memberships.Price), 0))
            .select_from(Subscriptions)
            .join(Memberships, Memberships.MembershipsID == Subscriptions.membershipsID)
        )
        total_revenue = revenue_result.scalar() or 0

        recent_query = (
            select(Subscriptions, Us)
            .join(Us, Us.UserID == Subscriptions.UserID)
            .order_by(desc(Subscriptions.StartDate))
            .limit(10)
        )
        recent_result = await session.execute(recent_query)
        recent_rows = recent_result.all()

        recent_subscriptions = []
        for sub, user in recent_rows:
            recent_subscriptions.append(
                {
                    "UserID": sub.UserID,
                    "username": getattr(user, "UserName", None)
                    or getattr(user, "username", None),
                    "StartDate": sub.StartDate.isoformat() if sub.StartDate else None,
                    "EndDate": sub.EndDate.isoformat() if sub.EndDate else None,
                    "status": sub.status,
                }
            )

        logger.info(
            f"Reports generated successfully  | "
            f"users={total_users} | active_subs={active_subscriptions} | "
            f"classes={total_active_classes} | revenue={int(total_revenue)}"
        )

        return {
            "status": "success",
            "message": "تم استخراج تقارير النظام بنجاح",
            "reports": {
                "total_users": total_users,
                "active_subscriptions": active_subscriptions,
                "total_active_classes": total_active_classes,
                "total_revenue": int(total_revenue),
            },
            "recent_subscriptions": recent_subscriptions,
        }

    except Exception as e:
        logger.error(f"Failed to generate reports  | error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء استخراج التقارير: {str(e)}",
        )


@router_admin.patch("/users/{user_id}/status", status_code=status.HTTP_200_OK)
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    check_role: dict = Depends(ensure_admin_role),
):
    admin_id = current_user.get("ID") or current_user.get("UserID")

    if admin_id == user_id:
        logger.warning(f"Admin {admin_id} tried to change their own status")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="لا يمكنك تغيير حالة حسابك بنفسك.",
        )

    query = select(Us).where(Us.UserID == user_id)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        logger.warning(f"Admin {admin_id} tried to update missing user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود في النظام",
        )

    db_user.is_active = not status_update.is_disabled

    try:
        await session.commit()
        await session.refresh(db_user)

        status_text = "مفعل" if db_user.is_active else "محظور"

        logger.info(
            f"Admin {admin_id} updated user {user_id} status → "
            f"is_active={db_user.is_active} ({status_text})"
        )
        await redis_client.delete("all_system_users")
        return {
            "status": "success",
            "message": f"تم تحديث حالة المستخدم بنجاح وأصبح الآن: {status_text}",
            "user_id": db_user.UserID,
            "is_active": db_user.is_active,
        }

    except Exception as e:
        await session.rollback()
        logger.error(
            f"Failed to update user status | admin={admin_id} | "
            f"user={user_id} | error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة المستخدم في قاعدة البيانات",
        )


@router_admin.post("/classes", status_code=status.HTTP_201_CREATED)
async def create_new_class(
    class_data: ClassCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(ensure_admin_role),
):
    await redis_client.delete("all_classes")
    admin_id = current_user

    trainer_query = select(Us).where(Us.UserID == class_data.Trainer_id)
    trainer_result = await session.execute(trainer_query)
    trainer = trainer_result.scalar_one_or_none()

    if not trainer:
        logger.warning(
            f"Admin {admin_id} tried to create class with invalid trainer_id={class_data.Trainer_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المدرب المحدد غير موجود",
        )

    new_class = Classes(
        classname=class_data.ClassName,
        typeclass=class_data.TypeClass,
        price=class_data.Price,
        date=class_data.Date,
        starttime=class_data.Start_time,
        endtime=class_data.End_time,
        trainerid=class_data.Trainer_id,
    )

    try:
        session.add(new_class)
        await session.commit()
        await session.refresh(new_class)

        logger.info(
            f"Admin {admin_id} created class | id={new_class.ClassesID} | "
            f"name={new_class.ClassName} | trainer={class_data.Trainer_id}"
        )

        return {
            "status": "success",
            "message": "تم إنشاء الحصة بنجاح",
            "classes_id": new_class.ClassesID,
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create class | admin={admin_id} | error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء حفظ الحصة: {str(e)}",
        )


@router_admin.put("/classes/{class_id}", status_code=status.HTTP_200_OK)
async def update_class(
    class_id: str,
    class_data: ClassUpdateSchema,
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
):
    query = select(Classes).where(Classes.ClassesID == class_id)
    result = await session.execute(query)
    db_class = result.scalar_one_or_none()

    if not db_class:
        logger.warning(f"Update class failed | class_id={class_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الحصة دي مش موجودة في السيستم، اتأكد من الـ ID",
        )

    update_data = class_data.model_dump(exclude_unset=True)

    if not update_data:
        logger.warning(f"Update class failed | class_id={class_id} | empty payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم يتم إرسال أي بيانات للتحديث!",
        )

    for key, value in update_data.items():
        setattr(db_class, key, value)

    try:
        await session.commit()
        await session.refresh(db_class)

        logger.info(
            f"Class updated successfully | class_id={class_id} | fields={list(update_data.keys())}"
        )

        return {
            "status": "success",
            "message": "تم تحديث بيانات الحصة بنجاح",
            "data": db_class,
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"Update class error | class_id={class_id} | error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الحصة في قاعدة البيانات",
        )


@router_admin.delete("/classes/{class_id}", status_code=status.HTTP_200_OK)
async def delete_class(
    class_id: str,
    session: AsyncSession = Depends(get_async_session),
    admin_role: str = Depends(ensure_admin_role),
):
    await redis_client.delete("all_classes")
    await redis_client.delete("all_trainers")
    query = select(Classes).where(Classes.ClassesID == class_id)
    result = await session.execute(query)
    db_class = result.scalar_one_or_none()

    if not db_class:
        logger.warning(f"Delete class failed | class_id={class_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="الحصة غير موجودة بالفعل"
        )

    try:
        await session.delete(db_class)
        await session.commit()

        logger.info(f"Class deleted successfully | class_id={class_id}")

        return {"status": "success", "message": "تم حذف الحصة نهائياً من السيستم"}
    except Exception as e:
        await session.rollback()
        logger.error(f"Delete class error | class_id={class_id} | error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="تعذر حذف الحصة، قد تكون مرتبطة بحجوزات قائمة للمشتركين",
        )


@router_admin.post("/Check_Role", status_code=status.HTTP_200_OK)
async def check_role(role: str = Depends(ensure_admin_role)):
    logger.info(f"Admin role check success | role={role}")
    return {
        "status": "success",
        "message": "أهلاً بك يا أدمن، أنت تمتلك الصلاحيات الكاملة للتحكم في النظام.",
        "role": role,
    }


@router_admin.get("/GetAll/Trainers", status_code=status.HTTP_200_OK)
async def get_all_trainers(session: AsyncSession = Depends(get_async_session)):
    try:
        cash = await redis_client.get("all_trainers")
        if cash:
            logger.info("Fetched trainers list from Redis ⚡")
            return json.loads(cash)
    except Exception as e:
        logger.error(f"Redis get error: {e}")

    query = select(Us).where(Us.Role == "Trainer")
    result = await session.execute(query)
    trainers = result.scalars().all()

    logger.info(f"Fetched trainers list from DB | count={len(trainers)}")

    all_trainers = [
        {
            "UserName": t.UserName,
            "UserID": t.UserID,
        }
        for t in trainers
    ]

    try:
        await redis_client.set("all_trainers", json.dumps(all_trainers), ex=3600)
    except Exception as e:
        logger.error(f"Redis set error: {e}")

    return all_trainers
