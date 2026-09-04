# نظام إدارة الجيم 🏋️‍♂️

Backend (FastAPI) + Frontend (HTML/JS) لإدارة المستخدمين، الاشتراكات، الكلاسات، المدفوعات (Stripe)، والإشعارات عبر البريد.

---

## المميزات

- تسجيل ودخول (JWT + Refresh Token) + Google OAuth
- ملف شخصي (تحديث بيانات، صورة، تغيير كلمة المرور)
- باقات اشتراك + كلاسات مع حجز ودفع
- Stripe Checkout + Webhook
- لوحة أدمن (تقارير، مستخدمين، باقات، كلاسات)
- نسيت كلمة المرور (Celery + إيميل)
- مهام مجدولة (APScheduler)
- Redis للكاش وطوابير Celery
- Docker Compose + GitHub Actions CI

---

## هيكل المشروع

```text
System Gym/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── GymBackendAPI/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   ├── pytest.ini
│   └── App/
│       ├── app.py
│       ├── alert.py              # مهام APScheduler
│       ├── redis.py
│       ├── static/profiles/
│       ├── core/security.py
│       ├── Database/db.py
│       ├── Tasks/task.py         # Celery
│       ├── Test/                 # pytest
│       └── routes/
│           ├── auth/
│           ├── users/
│           ├── admin/
│           ├── membership/
│           ├── classes/
│           └── payment/
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
    ├── reset-password.html
    ├── email-exists.html
    └── account-disabled.html
```
---

## المتطلبات

- Python 3.12+
- MySQL 8
- Redis
- Docker (اختياري)
- حساب Stripe (Test Mode للتطوير)
- SMTP لإرسال الإيميل
---
## التثبيت المحلي

Bash

```
cd GymBackendAPI
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### ملف .env

env

```
DATABASE_URL=mysql+aiomysql://user:password@127.0.0.1:3306/systemgym
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_BACKEND_URL=redis://localhost:6379/0

SECRET_KEY=change-me-to-a-long-random-string
ALGORITHM=HS256

FRONTEND_URL=http://localhost:3000

STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=
MAIL_SERVER=
MAIL_PORT=587
```

### قاعدة البيانات



```Bash
# تأكد MySQL شغال وأنشئ قاعدة systemgym
alembic upgrade head
```

### تشغيل الـ API



```Bash
uvicorn App.app:app --reload --host 0.0.0.0 --port 8000
```

### Celery (ترمينال ثاني)



```Bash
celery -A App.Tasks.task.app_celery worker --loglevel=info --pool=solo
```

### Stripe Webhook محلي



```Bash
stripe listen --forward-to localhost:8000/v1/api/payments/webhook
```

انسخ whsec_... إلى .env.

### الفرونت

افتح ملفات Frontend/ عبر Live Server أو Nginx على منفذ 3000، وعدّل:



```JavaScript
const BACKEND_URL = "http://localhost:8000";
```

---

## Docker



```Bash
# تأكد وجود Dockerfile في الباك والفرونت
# وفي docker-compose.yml: build: . و build: ./Frontend

# أنشئ .env ثم:
docker compose up -d --build
docker compose exec api alembic upgrade head
```

|الخدمة|الرابط|
|---|---|
|API Docs|[http://localhost:8000/docs](http://localhost:8000/docs)|
|Frontend|[http://localhost:3000](http://localhost:3000/)|
|Redis|localhost:6379|

**مهم داخل Docker:**

- REDIS_HOST=redis
- DATABASE_URL host = mysql أو host.docker.internal (لو MySQL على الجهاز)

---

## أهم مسارات الـ API

|Method|Path|الوصف|
|---|---|---|
|POST|/v1/api/auth/register|تسجيل|
|POST|/v1/api/auth/login|دخول|
|GET|/v1/api/auth/check|التحقق من التوكن|
|POST|/v1/api/auth/forgot-password|نسيت كلمة المرور|
|GET|/v1/api/user/me|الملف الشخصي|
|PUT|/v1/api/user/me/update|تحديث البيانات|
|POST|/v1/api/user/upload-profile-image|رفع صورة|
|GET|/v1/api/user/is-active|حالة الحساب|
|GET|/v1/api/classes|الكلاسات|
|GET|/v1/api/membership/all|الباقات|
|POST|/v1/api/payments/create-checkout-session|بدء الدفع|
|POST|/v1/api/payments/webhook|Stripe Webhook|
|GET|/v1/api/admin/Reports|تقارير الأدمن|

---

## الأدوار

|Role|الصلاحيات|
|---|---|
|User|اشتراك، حجز، بروفايل|
|Trainer|حسب المسارات المخصصة|
|Admin|إدارة كاملة + تقارير|

---

## الاختبارات



```Bash
cd GymBackendAPI
export PYTHONPATH=.
# أو في PowerShell: $env:PYTHONPATH = "."

pytest App/Test -v
```

تأكد من وجود conftest.py و MySQL/Redis في CI.

---

## المكتبات الأساسية

|المكتبة|الاستخدام|
|---|---|
|FastAPI / Uvicorn|الـ API|
|SQLAlchemy + aiomysql|قاعدة البيانات|
|Alembic|Migrations|
|Redis + Celery|كاش + إيميل خلفي|
|python-jose|JWT|
|Stripe|الدفع|
|SlowAPI|Rate limiting|
|APScheduler|مهام مجدولة|
|fastapi-mail|الإيميل|

---

## النشر على سيرفر

1. VPS + Docker + Nginx + Certbot
2. Domain: api.domain.com و app.domain.com
3. .env إنتاجي قوي
4. FRONTEND_URL و BACKEND_URL بـ HTTPS
5. Stripe Webhook من Dashboard (Live)
6. Celery worker شغّال

راجع قسم Docker و Nginx في التوثيق الداخلي للمشروع.

---

## استكشاف أخطاء شائعة

|المشكلة|الحل|
|---|---|
|Redis connection refused داخل Docker|REDIS_HOST=redis|
|MySQL Access denied في CI|نفس الباسورد في service و DATABASE_URL|
|pull access denied for gymapi|أضف build: . في compose|
|Port 6379 allocated|خدمة Redis مكررة|
|No module named App|شغّل من جذر المشروع + pythonpath = .|
|جدول users مش موجود|alembic upgrade head من أول revision|
|dialects:driver|اضبط DATABASE_URL في alembic/env.py|

---

## الترخيص

Apache 2.0 (أو حسب إعداد مشروعك).

---

## الدعم

- Docs: http://localhost:8000/docs
- Issues على مستودع GitHub

text

````
---

حط الملف في:

```text
GymBackendAPI/README.md
````