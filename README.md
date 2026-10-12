README آماده است. این کار را بکن:

### در GitHub
1. برو به: https://github.com/batvin/batpanel  
2. فایل **README.md** را باز کن → آیکون مداد (Edit)  
3. همه محتوا را پاک کن و متن زیر را جایگزین کن  
4. **Commit changes** بزن  

---

متن کامل README:

```markdown
# Batpanel — Batman VPN Panel

پنل مدیریت **OpenVPN** با سیستم لایسنس وابسته به IP، ربات تلگرام و مدیریت ورکر.

[![Release](https://img.shields.io/github/v/release/batvin/batpanel?style=for-the-badge)](https://github.com/batvin/batpanel/releases/latest)
[![License](https://img.shields.io/badge/License-Commercial-blue?style=for-the-badge)](https://t.me/shocavpnadmin)

---

## خرید لایسنس

برای تهیه لایسنس و پشتیبانی با تلگرام زیر در ارتباط باشید:

<p align="center">
  <a href="https://t.me/shocavpnadmin">
    <img src="https://img.shields.io/badge/Telegram-خرید_لایسنس_و_پشتیبانی-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram">
  </a>
</p>

**آیدی پشتیبانی:** [@shocavpnadmin](https://t.me/shocavpnadmin)

---

## نصب سریع

```bash
curl -fsSL -o batman-install.sh https://github.com/batvin/batpanel/releases/latest/download/batman-install.sh
sed -i 's/\r$//' batman-install.sh
bash batman-install.sh
```

بعد از نصب، آدرس پنل، نام کاربری و رمز عبور نمایش داده می‌شود.  
وارد پنل شوید و **کلید لایسنس** را در بخش لایسنس فعال کنید.

> ⚠️ بدون لایسنس معتبر، پنل قفل است و فقط بخش فعال‌سازی لایسنس در دسترس است.

---

## امکانات پنل

| بخش | توضیح |
|---|---|
| **داشبورد** | آمار کاربران، مصرف، وضعیت سرور و نمودار ساعتی |
| **کاربران** | ساخت / ویرایش / حذف کاربر، محدودیت حجم و زمان، دانلود کانفیگ `.ovpn` |
| **آنلاین‌ها** | لیست اتصالات زنده با سرعت آپلود/دانلود و امکان قطع اتصال |
| **ورکرها** | ساخت نماینده با سقف تعداد کاربر و پنل جدا |
| **ربات تلگرام** | ارسال خودکار مشخصات و فایل کانفیگ به کاربر بعد از `/start` |
| **تنظیمات** | آدرس سرور، پورت/پروتکل OpenVPN، DNS، لوگو و عنوان برند |
| **لایسنس** | فعال‌سازی کلید — وابسته به IP سرور |

### قابلیت‌های کاربردی
- محدودیت **حجم** و **مدت اعتبار** برای هر کاربر
- شروع اعتبار از **اولین اتصال** (اختیاری)
- ریست ترافیک و قطع اجباری کاربر
- پشتیبانی **UDP / TCP** و تغییر پورت از داخل پنل
- تم روشن / تاریک
- نصب یک‌فایلی روی Ubuntu / Debian

---

## گزینه‌های نصب

```bash
# پورت دلخواه برای پنل
PANEL_PORT=3100 bash batman-install.sh

# OpenVPN روی TCP 443
VPN_PORT=443 VPN_PROTO=tcp bash batman-install.sh

# نصب از صفر (پاک کردن داده قبلی)
bash batman-install.sh --fresh

# حذف پنل
bash batman-install.sh --uninstall
bash batman-install.sh --uninstall --purge   # حذف کامل داده‌ها
```

---

## دستورات بعد از نصب

```bash
batman-panel status          # وضعیت سرویس‌ها
batman-panel logs            # لاگ زنده
batman-panel restart         # ری‌استارت
batman-panel reset-admin     # ریست رمز مدیر
```

---

## نیازمندی‌ها

- سیستم‌عامل: **Ubuntu 20.04 / 22.04** یا Debian مشابه
- دسترسی **root**
- باز بودن پورت پنل (پیش‌فرض `3000/tcp`) و پورت OpenVPN (پیش‌فرض `1194/udp`)
- در صورت فایروال ابری (Hetzner و …) همان پورت‌ها را آنجا هم باز کنید

---

## سیستم لایسنس

- هر لایسنس فقط روی **یک IP** کار می‌کند
- کلید با امضای رمزنگاری‌شده صادر می‌شود
- در صورت غیرفعال‌سازی از سمت مدیریت، دسترسی پنل ظرف چند ثانیه قطع می‌شود

برای خرید یا تمدید لایسنس:

**[تلگرام پشتیبانی — @shocavpnadmin](https://t.me/shocavpnadmin)**

---

## پشتیبانی

سوال، مشکل نصب یا خرید لایسنس:

👉 **https://t.me/shocavpnadmin**
```

---

دکمه آبی **Telegram — خرید لایسنس و پشتیبانی** در بالای README نمایش داده می‌شود و با کلیک مستقیم به `https://t.me/shocavpnadmin` می‌رود.
