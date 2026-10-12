#!/usr/bin/env bash
# =====================================================================
#  Batman VPN Panel - نصب‌کننده‌ی تک‌فایلی (Ubuntu / Debian)
#  استفاده:   bash batman-install.sh
#  گزینه‌ها:  --fresh      پاک کردن همه‌ی داده‌ها و ساخت از صفر
#             --uninstall  حذف پنل (داده‌ها می‌مانند)
#             --purge      همراه با --uninstall: حذف داده‌ها و گواهی‌ها
#  متغیرهای اختیاری:  PANEL_PORT=3000 VPN_PORT=1194 VPN_PROTO=udp|tcp
#                     ADMIN_USER=admin ADMIN_PASS=... SERVER_HOST=IP_یا_دامنه
#                     LICENSE_SERVER_URL=http://IP:3200   (آدرس پنل مدیریت لایسنس)
# =====================================================================
set -u -o pipefail

APP_DIR=/opt/batman-vpn
DATA_DIR=/var/lib/batman-vpn
OVPN_DIR=/etc/openvpn/server
PANEL_PORT="${PANEL_PORT:-}"
VPN_PORT="${VPN_PORT:-1194}"
VPN_PROTO="${VPN_PROTO:-udp}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-}"
LICENSE_SERVER_URL="${LICENSE_SERVER_URL:-}"
SERVER_HOST="${SERVER_HOST:-}"
LOG=/var/log/batman-install.log
TS=$(date +%Y%m%d-%H%M%S)
FRESH=0; UNINSTALL=0; PURGE=0

if [ -z "$PANEL_PORT" ]; then   # نصب مجدد: پورت قبلی حفظ می‌شود
  PANEL_PORT=3000
  if [ -f "$APP_DIR/panel.env" ]; then
    P=$(sed -n 's/^PORT=//p' "$APP_DIR/panel.env" | head -1)
    [[ "$P" =~ ^[0-9]+$ ]] && PANEL_PORT=$P
  fi
fi

for a in "$@"; do
  case "$a" in
    --fresh) FRESH=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --purge) PURGE=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "گزینه‌ی ناشناخته: $a"; exit 1 ;;
  esac
done

if [ -t 1 ]; then B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'; else B=; G=; Y=; R=; N=; fi
step() { echo; echo "${B}▶ $*${N}"; }
ok()   { echo "  ${G}✓${N} $*"; }
warn() { echo "  ${Y}!${N} $*"; }
die()  { echo; echo "${R}✗ خطا: $*${N}"; echo "  جزئیات کامل: $LOG"; exit 1; }

[ "$(id -u)" -eq 0 ] || { echo "این اسکریپت باید با root اجرا شود:  sudo bash $0"; exit 1; }
mkdir -p "$(dirname "$LOG")"; : >> "$LOG"
exec > >(tee -a "$LOG") 2>&1
echo "=== شروع نصب: $(date) ==="

retry() { # retry N cmd...
  local n=$1; shift; local i=1
  while true; do
    "$@" && return 0
    [ "$i" -ge "$n" ] && return 1
    warn "تلاش $i ناموفق بود؛ ۵ ثانیه بعد دوباره..."; sleep 5; i=$((i+1))
  done
}

# ---------------------------------------------------------------- حذف
do_uninstall() {
  step "حذف پنل"
  systemctl disable --now batman-panel openvpn-server@server batman-nat 2>/dev/null
  rm -f /etc/systemd/system/batman-panel.service /etc/systemd/system/batman-nat.service
  rm -rf /etc/systemd/system/openvpn-server@server.service.d
  rm -f /usr/local/sbin/batman-nat /usr/local/bin/batman-panel /etc/sysctl.d/99-batman-vpn.conf
  /usr/local/sbin/batman-nat down 2>/dev/null
  systemctl daemon-reload
  rm -rf "$APP_DIR"
  if [ "$PURGE" -eq 1 ]; then
    rm -rf "$DATA_DIR"
    rm -rf "$OVPN_DIR/ca.crt" "$OVPN_DIR/server.crt" "$OVPN_DIR/server.key" "$OVPN_DIR/tls-crypt.key" "$OVPN_DIR/crl.pem" "$OVPN_DIR/ccd" "$OVPN_DIR/server.conf"
    ok "پنل و همه‌ی داده‌ها و گواهی‌ها حذف شد"
  else
    ok "پنل حذف شد. داده‌ها و گواهی‌ها در $DATA_DIR باقی ماند (برای حذف کامل: --uninstall --purge)"
  fi
  exit 0
}
[ "$UNINSTALL" -eq 1 ] && do_uninstall

# ---------------------------------------------------------------- بررسی‌ها
step "بررسی سیستم"
command -v apt-get >/dev/null || die "این نصب‌کننده فقط روی Ubuntu/Debian کار می‌کند"
case "$VPN_PROTO" in udp|tcp) ;; *) die "VPN_PROTO باید udp یا tcp باشد" ;; esac
[[ "$VPN_PORT" =~ ^[0-9]+$ ]] && [ "$VPN_PORT" -ge 1 ] && [ "$VPN_PORT" -le 65535 ] || die "VPN_PORT نامعتبر است"
[[ "$PANEL_PORT" =~ ^[0-9]+$ ]] && [ "$PANEL_PORT" -ge 1 ] && [ "$PANEL_PORT" -le 65535 ] || die "PANEL_PORT نامعتبر است"
[ "$PANEL_PORT" = "$VPN_PORT" ] && [ "$VPN_PROTO" = tcp ] && die "پورت پنل و پورت OpenVPN-TCP نباید یکی باشد"
[ -c /dev/net/tun ] || warn "دستگاه /dev/net/tun پیدا نشد؛ اگر سرور OpenVZ/LXC است، باید TUN را از پنل هاستینگ فعال کنید"
ok "سیستم: $(. /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-unknown}")"

# ---------------------------------------------------------------- پاکسازی نسخه‌ی قبلی
step "پاکسازی نسخه‌ی قدیمی پنل"
if command -v pm2 >/dev/null 2>&1; then
  pm2 delete batman-vpn >/dev/null 2>&1 && ok "پروسه‌ی قدیمی pm2 حذف شد"
  pm2 save --force >/dev/null 2>&1
fi
if [ -f /etc/systemd/system/openvpn@server.service ]; then
  systemctl disable --now openvpn@server >/dev/null 2>&1
  rm -f /etc/systemd/system/openvpn@server.service
  ok "یونیت قدیمی openvpn@server حذف شد"
fi
if [ -f "$APP_DIR/app.js" ] && [ ! -f "$APP_DIR/server.js" ]; then
  tar czf "/root/batman-old-backup-$TS.tar.gz" -C / --exclude='opt/batman-vpn/node_modules' opt/batman-vpn 2>/dev/null
  rm -rf "$APP_DIR"
  ok "پنل قدیمی حذف شد (پشتیبان: /root/batman-old-backup-$TS.tar.gz)"
fi
if systemctl list-unit-files 2>/dev/null | grep -q '^mongod.service'; then
  if systemctl is-active --quiet mongod; then
    systemctl disable --now mongod >/dev/null 2>&1
    ok "MongoDB خاموش و غیرفعال شد (دیگر لازم نیست و رم آزاد می‌شود؛ حذف نشد)"
  fi
fi
if [ -f "$OVPN_DIR/server.conf" ] && ! grep -q 'فایل خودکار پنل' "$OVPN_DIR/server.conf"; then
  mv "$OVPN_DIR/server.conf" "$OVPN_DIR/server.conf.bak-$TS"
  ok "server.conf قبلی به server.conf.bak-$TS منتقل شد"
fi
if [ "$FRESH" -eq 1 ]; then
  systemctl stop batman-panel openvpn-server@server >/dev/null 2>&1
  rm -rf "$DATA_DIR"
  rm -rf "$OVPN_DIR/ca.crt" "$OVPN_DIR/server.crt" "$OVPN_DIR/server.key" "$OVPN_DIR/tls-crypt.key" "$OVPN_DIR/crl.pem" "$OVPN_DIR/ccd"
  ok "حالت --fresh: داده‌ها و گواهی‌های قبلی پاک شد"
fi
systemctl stop batman-panel >/dev/null 2>&1
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${PANEL_PORT}\$"; then
  die "پورت $PANEL_PORT توسط برنامه‌ی دیگری اشغال است. با PANEL_PORT=3100 bash $0 پورت دیگری بدهید"
fi
ok "آماده"

# ---------------------------------------------------------------- بسته‌ها
step "نصب بسته‌های لازم (۱ تا ۳ دقیقه)"
export DEBIAN_FRONTEND=noninteractive
retry 3 apt-get update -y -o DPkg::Lock::Timeout=180 >/dev/null 2>&1 || warn "apt update کامل نشد؛ ادامه می‌دهیم"
retry 3 apt-get install -y -o DPkg::Lock::Timeout=180 openvpn easy-rsa curl ca-certificates openssl iptables >/dev/null 2>&1 \
  || die "نصب openvpn/easy-rsa ناموفق بود (اینترنت یا مخزن apt را بررسی کنید)"
ok "OpenVPN $(openvpn --version 2>/dev/null | head -1 | awk '{print $2}') و easy-rsa نصب شد"
[ -x /usr/share/easy-rsa/easyrsa ] || die "فایل /usr/share/easy-rsa/easyrsa پیدا نشد"

node_major() { node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0; }
if [ "$(node_major)" -lt 18 ]; then
  warn "Node.js نصب نیست یا قدیمی است؛ نصب Node 20..."
  retry 3 bash -c 'curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null 2>&1' || die "دانلود مخزن NodeSource ناموفق بود"
  retry 3 apt-get install -y -o DPkg::Lock::Timeout=180 nodejs >/dev/null 2>&1 || die "نصب Node.js ناموفق بود"
fi
[ "$(node_major)" -ge 18 ] || die "نسخه‌ی Node.js باید ۱۸ یا بالاتر باشد"
NODE_BIN=$(command -v node)
ok "Node.js $(node -v)"

# ---------------------------------------------------------------- فایل‌های برنامه
step "نصب فایل‌های پنل"
[ -f "$0" ] || die "این اسکریپت باید به‌صورت فایل اجرا شود (bash batman-install.sh)، نه از pipe"
TMP=$(mktemp -d)
LINE=$(awk '/^__PAYLOAD_BELOW__$/ {print NR+1; exit}' "$0")
[ -n "$LINE" ] || die "بسته‌ی داخلی اسکریپت پیدا نشد؛ فایل را کامل و بدون تغییر آپلود کنید"
tail -n +"$LINE" "$0" | base64 -d 2>/dev/null | tar xz -C "$TMP" 2>/dev/null || die "باز کردن بسته‌ی داخلی ناموفق بود (فایل هنگام آپلود خراب شده؟)"
[ -f "$TMP/server.js" ] || die "بسته‌ی داخلی ناقص است"
mkdir -p "$APP_DIR"
rm -rf "$APP_DIR/lib" "$APP_DIR/public" "$APP_DIR/server.js" "$APP_DIR/cli.js"
cp -r "$TMP"/. "$APP_DIR"/
rm -rf "$TMP"
{
  echo "PORT=$PANEL_PORT"
  echo "HOST=0.0.0.0"
  if [ -n "$LICENSE_SERVER_URL" ]; then
    echo "LICENSE_SERVER_URL=$LICENSE_SERVER_URL"
  fi
} > "$APP_DIR/panel.env"
chmod 700 "$APP_DIR"
ok "پنل در $APP_DIR نصب شد"

# ---------------------------------------------------------------- آی‌پی عمومی
detect_ip() {
  local ip=""
  for u in https://api.ipify.org https://ifconfig.me https://icanhazip.com; do
    ip=$(curl -4 -fsS --max-time 6 "$u" 2>/dev/null | tr -d '[:space:]')
    [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] && { echo "$ip"; return; }
  done
  ip=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)
  [ -z "$ip" ] && ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  echo "$ip"
}

# ---------------------------------------------------------------- راه‌اندازی اولیه (PKI، ادمین، server.conf)
step "ساخت گواهی‌ها و تنظیم سرور OpenVPN"
export DATA_DIR OVPN_DIR EASYRSA_BIN=/usr/share/easy-rsa/easyrsa
INIT_ARGS=()
if [ ! -f "$DATA_DIR/db.json" ] || [ -n "${SERVER_HOST:-}" ]; then
  [ -z "$SERVER_HOST" ] && SERVER_HOST=$(detect_ip)
  [ -n "$SERVER_HOST" ] || die "آی‌پی سرور تشخیص داده نشد؛ با SERVER_HOST=آی‌پی اجرا کنید"
  INIT_ARGS+=(--host "$SERVER_HOST")
fi
if [ ! -f "$DATA_DIR/db.json" ]; then
  INIT_ARGS+=(--port "$VPN_PORT" --proto "$VPN_PROTO" --admin-user "$ADMIN_USER")
  [ -n "$ADMIN_PASS" ] && INIT_ARGS+=(--admin-pass "$ADMIN_PASS")
fi
INIT_OUT=$("$NODE_BIN" "$APP_DIR/cli.js" init "${INIT_ARGS[@]}" 2>&1) || { echo "$INIT_OUT"; die "راه‌اندازی اولیه ناموفق بود"; }
echo "$INIT_OUT" | grep -q INIT_OK || { echo "$INIT_OUT"; die "راه‌اندازی اولیه کامل نشد"; }
NEW_USER=$(echo "$INIT_OUT" | sed -n 's/^ADMIN_USER=//p')
NEW_PASS=$(echo "$INIT_OUT" | sed -n 's/^ADMIN_PASS=//p')
# مقدارهای واقعی ذخیره‌شده (برای نمایش در خلاصه)
read -r REAL_PORT REAL_PROTO REAL_HOST < <("$NODE_BIN" -e '
const s=JSON.parse(require("fs").readFileSync(process.env.DATA_DIR+"/db.json","utf8")).settings;
console.log(s.port, s.proto, s.serverHost)')
VPN_PORT=$REAL_PORT; VPN_PROTO=$REAL_PROTO; SERVER_HOST=$REAL_HOST
ok "گواهی‌ها آماده است (EC prime256v1، بدون نیاز به DH)"

# ---------------------------------------------------------------- شبکه
step "تنظیم شبکه (فوروارد و NAT)"
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-batman-vpn.conf
sysctl -p /etc/sysctl.d/99-batman-vpn.conf >/dev/null 2>&1 || sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1
cat > /usr/local/sbin/batman-nat <<'EOF'
#!/bin/sh
SUBNET=10.8.0.0/24
case "$1" in
  up)
    iptables -t nat -C POSTROUTING -s $SUBNET ! -d $SUBNET -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -s $SUBNET ! -d $SUBNET -j MASQUERADE
    iptables -C FORWARD -s $SUBNET -j ACCEPT 2>/dev/null || iptables -I FORWARD 1 -s $SUBNET -j ACCEPT
    iptables -C FORWARD -d $SUBNET -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || iptables -I FORWARD 1 -d $SUBNET -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
    ;;
  down)
    iptables -t nat -D POSTROUTING -s $SUBNET ! -d $SUBNET -j MASQUERADE 2>/dev/null
    iptables -D FORWARD -s $SUBNET -j ACCEPT 2>/dev/null
    iptables -D FORWARD -d $SUBNET -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null
    ;;
esac
exit 0
EOF
chmod 755 /usr/local/sbin/batman-nat
cat > /etc/systemd/system/batman-nat.service <<'EOF'
[Unit]
Description=Batman VPN NAT rules
After=network-online.target ufw.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/batman-nat up
ExecStop=/usr/local/sbin/batman-nat down

[Install]
WantedBy=multi-user.target
EOF
ok "NAT برای شبکه‌ی 10.8.0.0/24 تنظیم شد"

# ---------------------------------------------------------------- فایروال
step "فایروال"
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  SSHP=$(ss -tnlp 2>/dev/null | awk '/sshd/ {n=split($4,a,":"); print a[n]}' | sort -u | head -1)
  [ -z "$SSHP" ] && SSHP=22
  ufw allow "$SSHP"/tcp >/dev/null 2>&1
  ufw allow "$PANEL_PORT"/tcp >/dev/null 2>&1
  ufw allow "$VPN_PORT/$VPN_PROTO" >/dev/null 2>&1
  ok "ufw: پورت‌های $SSHP/tcp و $PANEL_PORT/tcp و $VPN_PORT/$VPN_PROTO باز شد"
else
  ok "ufw فعال نیست؛ تغییری لازم نبود"
fi

# ---------------------------------------------------------------- سرویس‌ها
step "راه‌اندازی سرویس‌ها"
mkdir -p /etc/systemd/system/openvpn-server@server.service.d
cat > /etc/systemd/system/openvpn-server@server.service.d/batman.conf <<'EOF'
[Service]
RuntimeDirectory=openvpn-server
RuntimeDirectoryMode=0755
RuntimeDirectoryPreserve=yes
Restart=always
EOF
cat > /etc/systemd/system/batman-panel.service <<EOF
[Unit]
Description=Batman VPN Panel
After=network-online.target openvpn-server@server.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
Environment=NODE_ENV=production
Environment=DATA_DIR=$DATA_DIR
Environment=OVPN_DIR=$OVPN_DIR
EnvironmentFile=-$APP_DIR/panel.env
ExecStart=$NODE_BIN $APP_DIR/server.js
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
cat > /usr/local/bin/batman-panel <<EOF
#!/bin/sh
export DATA_DIR=$DATA_DIR OVPN_DIR=$OVPN_DIR
case "\$1" in
  status)  systemctl status batman-panel openvpn-server@server --no-pager ;;
  logs)    journalctl -u batman-panel -u openvpn-server@server -n 80 -f ;;
  restart) systemctl restart openvpn-server@server batman-panel && echo "ری‌استارت شد" ;;
  reset-admin) $NODE_BIN $APP_DIR/cli.js reset-admin "\${2:-}" ;;
  *) echo "استفاده: batman-panel {status|logs|restart|reset-admin [رمز-جدید]}" ;;
esac
EOF
chmod 755 /usr/local/bin/batman-panel
systemctl daemon-reload
systemctl enable batman-nat openvpn-server@server batman-panel >/dev/null 2>&1
systemctl restart batman-nat
systemctl restart openvpn-server@server
systemctl restart batman-panel
ok "سرویس‌ها فعال و روی بوت خودکار شدند"

# ---------------------------------------------------------------- بررسی نهایی
step "بررسی نهایی"
PANEL_UP=0; VPN_UP=0
for i in $(seq 1 30); do
  curl -fsS -m 2 "http://127.0.0.1:$PANEL_PORT/api/brand" >/dev/null 2>&1 && { PANEL_UP=1; break; }
  sleep 1
done
for i in $(seq 1 15); do
  systemctl is-active --quiet openvpn-server@server && { VPN_UP=1; break; }
  sleep 1
done
[ "$PANEL_UP" -eq 1 ] && ok "پنل پاسخ می‌دهد" || { warn "پنل پاسخ نداد:"; journalctl -u batman-panel -n 15 --no-pager 2>/dev/null; }
if [ "$VPN_UP" -eq 1 ]; then ok "OpenVPN فعال است"; else warn "OpenVPN بالا نیامد:"; journalctl -u openvpn-server@server -n 20 --no-pager 2>/dev/null; fi

CRED=/root/batman-credentials.txt
if [ -n "$NEW_PASS" ] || [ ! -f "$CRED" ]; then
  {
    echo "آدرس پنل:    http://$SERVER_HOST:$PANEL_PORT"
    [ -n "$NEW_PASS" ] && { echo "نام کاربری:  $NEW_USER"; echo "رمز عبور:    $NEW_PASS"; }
    echo "OpenVPN:     $SERVER_HOST  $VPN_PORT/$VPN_PROTO"
  } > "$CRED"
  chmod 600 "$CRED"
fi

echo
echo "${B}════════════════════════════════════════════════════${N}"
echo "${B}  نصب تمام شد${N}"
echo "${B}════════════════════════════════════════════════════${N}"
echo "  آدرس پنل:   ${G}http://$SERVER_HOST:$PANEL_PORT${N}"
if [ -n "$NEW_PASS" ]; then
  echo "  نام کاربری: ${G}$NEW_USER${N}"
  echo "  رمز عبور:   ${G}$NEW_PASS${N}   (در $CRED هم ذخیره شد)"
else
  echo "  ورود: همان نام کاربری و رمز قبلی (برای ریست: batman-panel reset-admin)"
fi
echo "  OpenVPN:    $SERVER_HOST  پورت $VPN_PORT/$VPN_PROTO"
echo
echo "  دستورهای مفید:  batman-panel status | logs | restart | reset-admin"
echo "  اگر از فایروال ابری (مثل Hetzner Firewall) استفاده می‌کنید، پورت‌های"
echo "  $PANEL_PORT/tcp و $VPN_PORT/$VPN_PROTO را آنجا هم باز کنید."
echo
[ "$PANEL_UP" -eq 1 ] && [ "$VPN_UP" -eq 1 ] || exit 2
exit 0
__PAYLOAD_BELOW__
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
