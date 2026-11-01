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

## نصب و به‌روزرسانی خودکار

روی Ubuntu 22.04/24.04 با معماری amd64 و دسترسی root:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install-v2.sh)
```

نصب‌کننده در صورت نیاز Docker و Compose را نصب می‌کند، سورس V2 را از شاخه main می‌گیرد، دیتابیس V2 موجود را قبل از ارتقا پشتیبان می‌گیرد و پس از اجرا health check می‌زند. در نصب تازه، نصب‌کننده نام کاربری، رمز عبور و پورت را از شما می‌پرسد. رمز باید حداقل ۱۴ کاراکتر باشد و اطلاعات ورود در `/root/batman-v2-credentials.txt` با مجوز 600 ذخیره می‌شود. در به‌روزرسانی، فایل `.env` و دیتابیس قبلی حفظ می‌شوند.

این اسکریپت V1 یا سرویس‌های VPN را متوقف/حذف نمی‌کند و به پورت 3000 دست نمی‌زند. V2 داشبورد فارسی BAT-PANEL را روی پورت انتخابی شما و از طریق `http://SERVER-IP:PORT` ارائه می‌کند. دسترسی این پورت را در فایروال فقط برای IPهای مورد اعتماد باز کنید و برای استفاده عمومی، HTTPS را با reverse proxy تنظیم کنید. این داشبورد امکانات پیاده‌سازی‌شده API را مدیریت می‌کند، اما ساخت کانفیگ واقعی VPN و مهاجرت کاربران V1 هنوز پیاده‌سازی نشده است.

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
