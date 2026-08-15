# نظام إدارة الجيم 🏋️‍♂️

Backend (FastAPI) + Frontend (HTML/JS) لإدارة المستخدمين، الاشتراكات، الكلاسات، المدفوعات (Stripe)، والإشعارات عبر البريد الإلكتروني.

---

## نظرة عامة

المشروع يوفّر:

- تسجيل ودخول (JWT + Refresh Token)
- ملف شخصي (تحديث بيانات، صورة، تغيير كلمة المرور)
- باقات اشتراك + كلاسات مع حجز
- دفع عبر Stripe Checkout + Webhook
- لوحة أدمن (تقارير، مستخدمين، باقات، كلاسات)
- نسيت كلمة المرور (إيميل عبر Celery)
- مهام مجدولة (APScheduler): انتهاء الاشتراكات، تذكير، تنظيف كاش
- Redis للكاش والطوابير
- Docker Compose للتشغيل الموحّد

---

## هيكل المشروع

```text
System Gym/
├── docker-compose.yml
├── .env
├── README.md
│
├── GymBackendAPI/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .dockerignore
│   └── App/
│       ├── app.py                 # نقطة تشغيل FastAPI + lifespan
│       ├── alert.py               # مهام APScheduler
│       ├── limiter.py             # SlowAPI rate limit
│       ├── redis.py               # عميل Redis
│       ├── static/profiles/       # صور المستخدمين
│       ├── core/
│       │   └── security.py        # get_current_user / ensure_admin_role
│       ├── Database/
│       │   └── db.py              # Engine, Models, Sessions
│       ├── Tasks/
│       │   └── task.py            # Celery tasks (إيميل)
│       └── routes/
│           ├── auth/              # تسجيل، دخول، forgot/reset
│           ├── users/             # بروفايل، حجوزات، اشتراكات المستخدم
│           ├── admin/             # لوحة الأدمن
│           ├── membership/        # الباقات
│           ├── classes/           # الكلاسات
│           └── payment/           # Stripe checkout + webhook
│
└── Frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── login.html
    ├── regester.html
    ├── index.html
    ├── memberships.html
    ├── classes.html
    ├── profile.html
    ├── admin.html
    ├── payment-success.html
    ├── forget-password.html
    └── reset-password.html
```

## المكتبات وأهميتها للمشروع

|المكتبة|الفائدة في المشروع|
|---|---|
|**fastapi**|إطار الـ API الرئيسي (مسارات، Docs، Depends)|
|**uvicorn**|تشغيل خادم ASGI للتطوير/الإنتاج|
|**gunicorn**|تشغيل متعدد العمليات في الإنتاج (اختياري مع uvicorn workers)|
|**SQLAlchemy**|ORM وقاعدة البيانات (Users, Subscriptions, Classes...)|
|**aiomysql / pymysql**|اتصال MySQL غير متزامن / متزامن|
|**alembic**|ترحيل مخطط قاعدة البيانات (migrations)|
|**pydantic / email-validator**|التحقق من المدخلات (Login, Register, Schemas)|
|**python-jose**|إنشاء والتحقق من JWT (access / refresh / reset)|
|**passlib / bcrypt**|تشفير كلمات المرور (أو hashing حسب التنفيذ)|
|**python-multipart**|رفع الملفات (صورة البروفايل)|
|**python-dotenv**|قراءة متغيرات .env|
|**redis**|كاش القوائم + broker/backend لـ Celery|
|**celery**|طابور خلفية: إرسال إيميل الترحيب وإعادة كلمة المرور|
|**fastapi-mail**|إرسال رسائل HTML عبر SMTP|
|**httpx**|طلبات HTTP (مثل OAuth / خدمات خارجية)|
|**stripe**|إنشاء Checkout Session + استقبال Webhook|
|**slowapi**|تحديد معدل الطلبات (مثل login / forgot-password)|
|**pillow**|معالجة وتصغير صورة البروفايل قبل الحفظ|
|**apscheduler**|مهام مجدولة: انتهاء اشتراك، تذكير، مسح كاش|
|**sentry-sdk**|مراقبة الأخطاء في الإنتاج (اختياري)|
|**imagekitio**|رفع/تحسين صور سحابيًا (إن وُجد في المشروع)|

---

## المتطلبات
- Python 3.12+
- Docker Desktop (Windows + WSL2 مُفضّل)
- MySQL 8
- Redis
- حساب Stripe (Test Mode)
- SMTP (مثل TurboSMTP / Gmail App Password) لإرسال الإيميل
---
## متغيرات البيئة (.env)

```env
# Database
MYSQL_ROOT_PASSWORD=rootpass
MYSQL_DATABASE=systemgym
MYSQL_USER=gym
MYSQL_PASSWORD=gym123
DATABASE_URL=mysql+aiomysql://gym:gym123@mysql:3306/systemgym

# Redis / Celery
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_BACKEND_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=change-me-long-random
ALGORITHM=HS256

# Frontend URLs
FRONTEND_URL=http://localhost:3000

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Mail (fastapi-mail)
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_FROM=...
MAIL_SERVER=...
MAIL_PORT=587

# Optional
SENTRY_DSN=
ENV=development
```

> داخل Docker: REDIS_HOST=redis و DATABASE_URL host = mysql تشغيل محلي للـ API: localhost لـ Redis/MySQL

---

## التشغيل بـ Docker

### docker-compose.yml (ملخص)



``` YAML
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    ports:
      - "3307:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    networks: [gym-net]

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks: [gym-net]

  api:
    build: ./GymBackendAPI
    ports:
      - "8000:8000"
    env_file: [.env]
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_HOST: redis
      REDIS_PORT: "6379"
    depends_on: [mysql, redis]
    networks: [gym-net]

  frontend:
    build: ./Frontend
    ports:
      - "3000:80"
    depends_on: [api]
    networks: [gym-net]

volumes:
  mysql_data:

networks:
  gym-net:
```

### أوامر

Bash

```
docker compose up -d --build
docker compose ps
docker compose logs -f api
docker compose down
```

### الروابط

|الخدمة|الرابط|
|---|---|
|الواجهة|[http://localhost:3000](http://localhost:3000)|
|API Docs|[http://localhost:8000/docs](http://localhost:8000/docs)|
|Redis|localhost:6379|
|MySQL من الجهاز|localhost:3307|

---

## التشغيل المحلي (بدون Docker للـ API)



```Bash
cd GymBackendAPI
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt

# عدّل .env: REDIS_HOST=localhost و DATABASE_URL على localhost
uvicorn App.app:app --reload --host 0.0.0.0 --port 8000
```

### Celery (ترمينال ثانٍ)



```Bash
celery -A App.Tasks.task.app_celery worker --loglevel=info --pool=solo
```

### Stripe Webhook محلي



```Bash
stripe listen --forward-to localhost:8000/v1/api/payments/webhook
```

---

## أهم المسارات (API)

|Method|Path|الوصف|
|---|---|---|
|POST|/v1/api/auth/register|تسجيل|
|POST|/v1/api/auth/login|دخول|
|GET|/v1/api/auth/check|التحقق من التوكن|
|POST|/v1/api/auth/forgot-password|نسيت كلمة المرور|
|POST|/v1/api/auth/reset-password|تعيين كلمة مرور جديدة|
|GET|/v1/api/user/me|الملف الشخصي|
|PUT|/v1/api/user/me/update|تحديث البيانات|
|POST|/v1/api/user/upload-profile-image|رفع صورة|
|GET|/v1/api/user/me/bookings|حجوزات الكلاسات|
|GET|/v1/api/user/me/subscriptions|اشتراكات المستخدم|
|GET|/v1/api/classes|عرض الكلاسات|
|GET|/v1/api/membership/...|عرض الباقات|
|POST|/v1/api/payments/create-checkout-session|بدء الدفع|
|POST|/v1/api/payments/webhook|تأكيد الدفع من Stripe|
|GET|/v1/api/admin/Reports|تقارير الأدمن|

---

## تدفقات مهمة

### الدفع (Stripe)

text

```
المستخدم → create-checkout-session
  → سجل pending في DB
  → Stripe Checkout
  → Webhook (paid) → active
  → payment-success.html
```

### نسيت كلمة المرور

text

```
forgot-password → Celery task → إيميل برابط token
  → reset-password.html → باسورد جديد
```

### المهام المجدولة (APScheduler)

|Job|الوظيفة|
|---|---|
|expire_subscriptions_job|تحويل الاشتراكات المنتهية إلى expired|
|reminder_before_subscription_ends|تذكير قبل الانتهاء|
|clear_redis_cache_job|مسح مفاتيح الكاش العامة|

---

## الأدوار

|Role|الصلاحيات|
|---|---|
|User|اشتراك، حجز كلاس، بروفايل|
|Trainer|حسب المسارات المخصصة|
|Admin|إدارة كاملة + تقارير|

---

## قواعد Docker المهمة

|من|إلى|Host|
|---|---|---|
|API container|MySQL|mysql|
|API container|Redis|redis|
|API container|MySQL على ويندوز|host.docker.internal|
|المتصفح|API|localhost:8000|
|المتصفح|Frontend|localhost:3000|

text

```
لا تستخدم MYSQL_USER=root
لا تترك DATABASE_PORT فاضي (يسبب :None)
REDIS_HOST داخل الحاوية = redis وليس localhost
```

---

## استكشاف أخطاء شائعة

|المشكلة|الحل|
|---|---|
|Circular import|get_current_user في App/core/security.py فقط|
|Redis connection refused|REDIS_HOST=redis + rebuild|
|Celery لا يرسل إيميل|worker شغال + Redis|
|Stripe pending لا يتحول active|stripe listen + webhook secret|
|رفع صورة فشل|وجود مجلد App/static/profiles|
|Port 3306 مشغول|انشر MySQL على 3307:3306|


## التطوير المستقبلي (مقترحات)

- اختبارات pytest للـ API
- CI/CD
- HTTPS + domain حقيقي
- Sentry في الإنتاج
- تحسين لوحة الأدمن والتقارير