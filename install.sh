#!/usr/bin/env bash
# Batman VPN Panel - one-command bootstrap installer
# Usage: curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install.sh | bash
set -Eeuo pipefail

REPO_RAW="${BATMAN_RAW_BASE:-https://raw.githubusercontent.com/batvin/batpanel/main}"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if [[ "$(id -u)" -ne 0 ]]; then
  echo "خطا: نصب‌کننده باید با دسترسی root اجرا شود."
  echo "ابتدا اجرا کنید: sudo -i"
  exit 1
fi

command -v curl >/dev/null 2>&1 || {
  echo "خطا: curl نصب نیست. ابتدا اجرا کنید: apt-get update && apt-get install -y curl"
  exit 1
}

echo "در حال دریافت نصب‌کننده Batman VPN Panel..."
if ! curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
  "$REPO_RAW/batman-install.sh" -o "$TMP_DIR/batman-install.sh"; then
  echo "خطا: دریافت فایل نصب ناموفق بود. اتصال اینترنت و دسترسی به GitHub را بررسی کنید."
  exit 1
fi

if [[ ! -s "$TMP_DIR/batman-install.sh" ]] || ! grep -q '^__PAYLOAD_BELOW__$' "$TMP_DIR/batman-install.sh"; then
  echo "خطا: فایل نصب ناقص یا نامعتبر دریافت شد."
  exit 1
fi

chmod 700 "$TMP_DIR/batman-install.sh"
echo "فایل دریافت شد؛ اجرای نصب..."
bash "$TMP_DIR/batman-install.sh" "$@"
