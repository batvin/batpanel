# استقرار آزمایشی Batman VPN Panel V2

## محدوده این نسخه

این بسته یک **Control Plane MVP** است: ورود مدیر، داشبورد آماری API، ثبت سرور، heartbeat عامل، ثبت کاربران، فهرست کاربران و ثبت تعلیق در دیتابیس. این عملیات هنوز به OpenVPN/Xray/WireGuard اعمال نمی‌شوند. API عمداً این محدودیت را در پاسخ‌ها اعلام می‌کند.

این نسخه را جایگزین V1 نکنید و روی سرور عملیاتی VPN بدون VM آزمایشی اجرا نکنید.

## پیش‌نیاز

- Ubuntu 22.04 یا 24.04 (هدف آزمایش، نه ادعای تأیید نهایی)
- Docker Engine و Docker Compose plugin
- حداقل 1 GB RAM برای تست سبک
- دسترسی root برای اجرای Docker Compose
- پورت 8000 فقط روی loopback؛ فایل Compose آن را به 127.0.0.1 متصل می‌کند

## نصب

از ریشه clone مخزن:

```bash
sudo bash v2/install.sh
```

در اولین اجرا نام کاربری و رمز مدیر پرسیده می‌شود. رمز حداقل 14 نویسه باشد. کلید JWT به‌صورت تصادفی ساخته و فایل `.env` با مجوز 600 ذخیره می‌شود.

## بررسی

```bash
docker compose -f v2/docker-compose.yml --env-file v2/.env -p batman-v2 ps
curl -fsS http://127.0.0.1:8000/api/health
```

برای مشاهده مستندات API از طریق تونل SSH یا همان ماشین:
`http://127.0.0.1:8000/api/docs`

## پشتیبان‌گیری

```bash
docker compose -f v2/docker-compose.yml --env-file v2/.env -p batman-v2 stop
docker run --rm -v batman-v2_batman_v2_data:/data -v "$PWD":/backup alpine tar czf /backup/batman-v2-data-backup.tgz -C /data .
docker compose -f v2/docker-compose.yml --env-file v2/.env -p batman-v2 start
```

نام volume در نصب‌کننده فعلی `batman-v2_batman_v2_data` است. قبل از backup آن را با `docker volume ls` بررسی کنید.

## توقف

```bash
docker compose -f v2/docker-compose.yml --env-file v2/.env -p batman-v2 down
```

برای حفظ دیتابیس، از `down -v` استفاده نکنید.

## هنوز تکمیل نشده

- Agent اجرایی و احراز هویت امن دوطرفه
- اعمال provisioning واقعی در OpenVPN، Xray و WireGuard
- تمدید/تعلیق واقعی روی پروتکل‌ها و آمار مصرف واقعی
- TLS/reverse proxy عمومی، rate limiting و RBAC چندنقشی
- migration از V1 و تست‌های integration روی VMهای مجزا

تا تکمیل موارد بالا این نسخه برای فروش/مدیریت سرویس واقعی production-ready نیست.
