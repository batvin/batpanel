# BAT-PANEL — Batman VPN Control Panel

پنل مدیریتی BAT-PANEL با رابط فارسی راست‌چین، داشبورد Glassmorphism، تولید کانفیگ پروتکل‌ها و API مرکزی.

> **وضعیت نسخه 2.1:** داشبورد شیشه‌ای با موشن قوی، ساخت واقعی کانفیگ VLESS / VMess / Trojan / WireGuard / قالب OpenVPN، کنترل خودکار حجم و انقضا، و API گزارش ترافیک Agent پیاده‌سازی شده‌اند. اجرای کامل Agent روی نود (اعمال کانفیگ روی سرویس‌های در حال اجرا) هنوز در حال توسعه است.

## نصب BAT-PANEL V2

سیستم‌عامل هدف: Ubuntu 22.04 یا 24.04، معماری amd64، دسترسی root و اینترنت.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install-v2.sh)
```

نصب‌کننده در نصب تازه این موارد را می‌پرسد:
- نام کاربری مدیر (۳ تا ۶۴ کاراکتر)
- رمز عبور مدیر (حداقل ۱۴ کاراکتر؛ حروف انگلیسی، عدد و علائم مجاز)
- پورت پنل (۱۰۲۴ تا ۶۵۵۳۵)

پس از نصب:
- آدرس محلی: `http://127.0.0.1:PORT` (با تونل SSH یا reverse proxy امن)
- مستندات API: `http://SERVER-IP:PORT/api/docs`
- اطلاعات ورود: `/root/batman-v2-credentials.txt` (دسترسی محدود root)
- دستور مدیریت ترمینال: `bat-panel`
- پشتیبانی: [@shocavpnadmin](https://t.me/shocavpnadmin)

پنل فقط روی `127.0.0.1` در دسترس است. برای دسترسی از کامپیوتر خود از تونل SSH استفاده کنید:

```bash
ssh -L 8000:127.0.0.1:8000 root@SERVER_IP
```

سپس `http://127.0.0.1:8000` را باز کنید.

## منوی مدیریتی

با root اجرا کنید:

```bash
bat-panel
```

امکانات: وضعیت، restart، stop، start، logs، backup، update از GitHub، تغییر پورت و تغییر مشخصات مدیر.

## قابلیت‌های جدید 2.1

- UI شیشه‌ای (Glassmorphism) با انیمیشن‌های قوی
- تولید لینک و کانفیگ VLESS / VMess / Trojan
- تولید فایل WireGuard و قالب OpenVPN
- قطع خودکار کاربر منقضی یا تمام‌حجم
- دکمه مشاهده و کپی کانفیگ در پنل
- API گزارش ترافیک برای Agent آینده

## معماری و پوشه‌ها

- `install-v2.sh`: نصب و به‌روزرسانی V2
- `v2/backend`: API و تولید کانفیگ
- `v2/web`: داشبورد وب فارسی
- `v2/scripts/bat-panel`: منوی مدیریتی ترمینال
- `v2/docker-compose.yml`: استقرار Docker
- `v2/DEPLOYMENT.md`: راهنمای استقرار

## امنیت

- رمز عبور قوی انتخاب کنید.
- پورت پنل را فقط برای IPهای مورد اعتماد باز کنید.
- برای استفاده عمومی HTTPS را فعال کنید.
- فایل `.env` و اطلاعات ورود را محرمانه نگه دارید.

## Releases

- [نسخه‌های منتشرشده](https://github.com/batvin/batpanel/releases)
- نسخه قدیمی V1 با تگ `v1.0.0` در Releases حفظ شده است.

---
**BAT-PANEL** · پشتیبانی تلگرام: [@shocavpnadmin](https://t.me/shocavpnadmin)
