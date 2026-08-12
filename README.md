# نظام إدارة الجيم 🏋️‍♂️

Backend + Frontend لإدارة الاشتراكات، الكلاسات، المستخدمين، والمدفوعات عبر Stripe.

---

## المميزات

- تسجيل / دخول (JWT + Refresh Token)
- ملف شخصي + رفع صورة
- باقات اشتراك + كلاسات
- دفع Stripe (عضوية / كلاس)
- لوحة أدمن (تقارير، مستخدمين، إدارة باقات وكلاسات)
- Redis للكاش وتجديد الجلسات
- Docker Compose (API + Frontend + Redis + MySQL اختياري)

---

## هيكل المشروع

```text
System Gym/
├── docker-compose.yml
├── .env
├── GymBackendAPI/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── App/
│       ├── app.py
│       ├── Database/
│       ├── routes/
│       │   ├── auth/
│       │   ├── users/
│       │   ├── admin/
│       │   ├── membership/
│       │   ├── classes/
│       │   └── payment/
│       └── ...
