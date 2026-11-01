# Batman VPN Panel

پنل مدیریت کاربران **OpenVPN** با نصب خودکار روی سرورهای Ubuntu و Debian.

> **نکته مهم:** نصب‌کننده تنظیمات شبکه و سرویس OpenVPN را تغییر می‌دهد. برای نصب اول، یک سرور تازه و اختصاصی پیشنهاد می‌شود. روی سروری که OpenVPN یا سرویس VPN دیگری دارد، بدون بررسی قبلی نصب نکنید.

## نصب سریع (فقط یک دستور)

با SSH وارد سرور شوید و دستور زیر را با دسترسی `root` اجرا کنید:

```bash
curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install.sh | bash
```

این دستور فایل نصب اصلی را خودکار دریافت و اجرا می‌کند؛ نیازی به ساخت فایل یا کپی چندمرحله‌ای نیست.

اگر با کاربر عادی وارد شده‌اید، ابتدا به root بروید:

```bash
sudo -i
```

سپس دستور نصب سریع را اجرا کنید.

## پیش‌نیازها

- Ubuntu 20.04 / 22.04 یا Debian سازگار با `apt`
- معماری 64-bit و دسترسی اینترنت از سرور
- دسترسی root یا sudo
- فعال بودن قابلیت TUN در VPS
- سرور ترجیحاً تازه و بدون نصب قبلی OpenVPN
- امکان باز کردن پورت‌های موردنیاز در فایروال سیستم و فایروال ارائه‌دهنده VPS

## پورت‌های پیش‌فرض

| سرویس | پورت پیش‌فرض | پروتکل |
|---|---:|---|
| پنل وب | 3000 | TCP |
| OpenVPN | 1194 | UDP |

اگر UFW از قبل فعال باشد، نصب‌کننده تلاش می‌کند پورت‌های پنل، VPN و SSH فعلی را مجاز کند. در فایروال ابری ارائه‌دهنده VPS نیز باید پورت‌های لازم را باز کنید.

## پس از نصب

در پایان نصب، آدرس پنل و اطلاعات ورود نمایش داده می‌شود و اطلاعات ورود در فایل زیر با دسترسی محدود ذخیره می‌شود:

```text
/root/batman-credentials.txt
```

آدرس پنل به این شکل است:

```text
http://SERVER_IP:3000
```

پس از ورود، برای باز شدن امکانات پنل، کلید لایسنس معتبر را در قسمت لایسنس فعال کنید. بدون لایسنس معتبر، پنل در حالت محدود باقی می‌ماند.

## تنظیمات نصب

برای تغییر پورت پنل، همان نصب سریع را با متغیر محیطی اجرا کنید:

```bash
curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install.sh | PANEL_PORT=3100 bash
```

برای استفاده از OpenVPN روی TCP پورت 443:

```bash
curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install.sh | VPN_PORT=443 VPN_PROTO=tcp bash
```

برای تعیین IP یا دامنه سرور:

```bash
curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install.sh | SERVER_HOST=vpn.example.com bash
```

## مدیریت پنل

```bash
batman-panel status       # وضعیت پنل و OpenVPN
batman-panel logs         # مشاهده زنده لاگ‌ها
batman-panel restart      # راه‌اندازی مجدد سرویس‌ها
batman-panel reset-admin  # بازنشانی رمز مدیر
```

## حذف پنل

برای اجرای دستورات حذف، ابتدا فایل نصب اصلی را دریافت کنید:

```bash
curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/batman-install.sh -o batman-install.sh
```

حذف برنامه با نگه‌داشتن داده‌ها و گواهی‌ها:

```bash
bash batman-install.sh --uninstall
```

حذف کامل پنل، داده‌ها و گواهی‌های مرتبط:

```bash
bash batman-install.sh --uninstall --purge
```

**هشدار:** گزینه `--purge` داده‌های پنل و گواهی‌های OpenVPN را حذف می‌کند. قبل از اجرا از اطلاعات موردنیاز نسخه پشتیبان بگیرید.

## امکانات

- داشبورد آمار کاربران، مصرف و وضعیت سرور
- ساخت، ویرایش و حذف کاربران
- محدودیت حجم و مدت اعتبار
- شروع اعتبار از اولین اتصال (در صورت فعال‌سازی)
- مشاهده اتصال‌های آنلاین و قطع اتصال
- ساخت ورکر با محدودیت تعداد کاربر
- ربات تلگرام برای ارسال اطلاعات و فایل کانفیگ
- پشتیبانی از OpenVPN روی UDP و TCP
- تم روشن و تاریک
- مدیریت لایسنس وابسته به IP سرور

## عیب‌یابی

مشاهده وضعیت سرویس‌ها:

```bash
batman-panel status
systemctl status batman-panel openvpn-server@server --no-pager
```

مشاهده لاگ نصب:

```bash
tail -n 100 /var/log/batman-install.log
```

مشاهده لاگ پنل:

```bash
journalctl -u batman-panel -n 100 --no-pager
```

اگر پنل باز نمی‌شود، ابتدا وضعیت سرویس را بررسی کنید و سپس باز بودن TCP پورت پنل را در فایروال سیستم و پنل VPS بررسی کنید.

## پشتیبانی

برای پشتیبانی، پرسش درباره نصب یا تهیه لایسنس:

**[تلگرام پشتیبانی — @shocavpnadmin](https://t.me/shocavpnadmin)**
