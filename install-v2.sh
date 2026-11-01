#!/usr/bin/env bash
set -Eeuo pipefail

REPO="batvin/batpanel"
BRANCH="main"
INSTALL_DIR="/opt/batman-v2"
BACKUP_ROOT="/var/backups/batman-v2"
PROJECT="batman-v2"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

LOCK_FILE="/var/lock/batman-v2-installer.lock"
TMP_DIR="$(mktemp -d)"
PREVIOUS_DIR=""
NEW_INSTALL=0

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

log() { printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

if [[ "$EUID" -ne 0 ]]; then
  die "Run as root: sudo bash install-v2.sh"
fi
exec 9>"$LOCK_FILE"
flock -n 9 || die "Another Batman V2 installation/update is running."

. /etc/os-release
[[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "22.04" || "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "24.04" ]] || die "Supported operating systems: Ubuntu 22.04 and 24.04."
[[ "$(dpkg --print-architecture)" == "amd64" ]] || die "This installer currently supports amd64 only."

export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  log "Installing Docker Engine and Compose plugin from Ubuntu packages..."
  apt-get update
  apt-get install -y docker.io docker-compose-v2 curl ca-certificates openssl
fi
systemctl enable --now docker
docker info >/dev/null 2>&1 || die "Docker daemon is not responding."

command -v curl >/dev/null 2>&1 || apt-get install -y curl
command -v openssl >/dev/null 2>&1 || apt-get install -y openssl

mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"

if [[ -d "$INSTALL_DIR" ]]; then
  PREVIOUS_DIR="$TMP_DIR/previous-source"
  cp -a "$INSTALL_DIR" "$PREVIOUS_DIR"
  if [[ -f "$INSTALL_DIR/$ENV_FILE" ]]; then
    cp -a "$INSTALL_DIR/$ENV_FILE" "$TMP_DIR/existing.env"
  fi
else
  NEW_INSTALL=1
fi

log "Downloading Batman V2 from GitHub ($BRANCH)..."
ARCHIVE="$TMP_DIR/source.tar.gz"
curl --fail --location --retry 3 --connect-timeout 15 \
  "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" -o "$ARCHIVE"
mkdir -p "$TMP_DIR/source"
tar -xzf "$ARCHIVE" --strip-components=1 -C "$TMP_DIR/source"
[[ -f "$TMP_DIR/source/v2/docker-compose.yml" && -f "$TMP_DIR/source/v2/backend/Dockerfile" ]] || die "Downloaded repository does not contain the expected V2 files."

if [[ "$NEW_INSTALL" -eq 0 ]]; then
  if [[ -f "$INSTALL_DIR/v2/$ENV_FILE" ]]; then
    cp -a "$INSTALL_DIR/v2/$ENV_FILE" "$TMP_DIR/existing.env"
  fi
fi

mkdir -p "$INSTALL_DIR"
cp -a "$TMP_DIR/source/v2/." "$INSTALL_DIR/"
if [[ -f "$TMP_DIR/existing.env" ]]; then
  cp -a "$TMP_DIR/existing.env" "$INSTALL_DIR/$ENV_FILE"
fi

if [[ ! -f "$INSTALL_DIR/$ENV_FILE" ]]; then
  log "Creating the first administrator account..."
  read -r -p "نام کاربری مدیر [admin]: " ADMIN_USERNAME
  ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
  [[ "$ADMIN_USERNAME" =~ ^[a-zA-Z0-9_.-]{3,64}$ ]] || die "نام کاربری باید 3 تا 64 کاراکتر انگلیسی باشد."
  while true; do
    read -r -s -p "رمز عبور مدیر (حداقل 14 کاراکتر): " ADMIN_PASSWORD; echo
    [[ ${#ADMIN_PASSWORD} -ge 14 && "$ADMIN_PASSWORD" =~ ^[a-zA-Z0-9!@#%_^+=.,:/?-]+$ ]] && break
    echo "رمز عبور کوتاه است."
  done
  read -r -p "پورت پنل [8000]: " PANEL_PORT
  PANEL_PORT="${PANEL_PORT:-8000}"
  [[ "$PANEL_PORT" =~ ^[0-9]+$ ]] && ((PANEL_PORT>=1024 && PANEL_PORT<=65535)) || die "پورت باید بین 1024 و 65535 باشد."
  if ss -lnt | awk '{print $4}' | grep -Eq "[:.]$PANEL_PORT$"; then die "این پورت از قبل در حال استفاده است."; fi
  JWT_SECRET="$(openssl rand -hex 48)"
  umask 077
  cat > "$INSTALL_DIR/$ENV_FILE" <<EOF
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
JWT_SECRET=$JWT_SECRET
TOKEN_TTL_HOURS=8
DATABASE_URL=sqlite:////data/batman-v2.db
PANEL_PORT=$PANEL_PORT
EOF
  chmod 600 "$INSTALL_DIR/$ENV_FILE"
  cat > /root/batman-v2-credentials.txt <<EOF
BAT-PANEL V2
Username: $ADMIN_USERNAME
Password: $ADMIN_PASSWORD
Panel: http://SERVER-IP:$PANEL_PORT
API: http://SERVER-IP:$PANEL_PORT/api
API docs: http://SERVER-IP:$PANEL_PORT/api/docs
EOF
  chmod 600 /root/batman-v2-credentials.txt
else
  chmod 600 "$INSTALL_DIR/$ENV_FILE"
  if ! grep -q '^PANEL_PORT=' "$INSTALL_DIR/$ENV_FILE"; then
    echo "PANEL_PORT=8000" >> "$INSTALL_DIR/$ENV_FILE"
  fi
  if [[ ! -f /root/batman-v2-credentials.txt ]]; then
    EXISTING_USERNAME="$(sed -n 's/^ADMIN_USERNAME=//p' "$INSTALL_DIR/$ENV_FILE" | head -n1)"
    EXISTING_PASSWORD="$(sed -n 's/^ADMIN_PASSWORD=//p' "$INSTALL_DIR/$ENV_FILE" | head -n1)"
    if [[ -n "$EXISTING_USERNAME" && -n "$EXISTING_PASSWORD" ]]; then
      : # Credentials file is regenerated below from the preserved environment.
    fi
  fi
fi

PANEL_PORT="$(sed -n 's/^PANEL_PORT=//p' "$INSTALL_DIR/$ENV_FILE" | tail -n1)"
PANEL_PORT="${PANEL_PORT:-8000}"
ADMIN_USERNAME="$(sed -n 's/^ADMIN_USERNAME=//p' "$INSTALL_DIR/$ENV_FILE" | head -n1)"
ADMIN_PASSWORD="$(sed -n 's/^ADMIN_PASSWORD=//p' "$INSTALL_DIR/$ENV_FILE" | head -n1)"
cat > /root/batman-v2-credentials.txt <<EOF
BAT-PANEL V2
Username: $ADMIN_USERNAME
Password: $ADMIN_PASSWORD
Panel: http://SERVER-IP:$PANEL_PORT
API: http://SERVER-IP:$PANEL_PORT/api
API docs: http://SERVER-IP:$PANEL_PORT/api/docs
Support: https://t.me/shocavpnadmin
EOF
chmod 600 /root/batman-v2-credentials.txt

install -m 700 "$INSTALL_DIR/scripts/bat-panel" /usr/local/bin/bat-panel
cd "$INSTALL_DIR"
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" config --quiet

# Preserve the existing database volume before an update. Never remove it.
VOLUME="${PROJECT}_batman_v2_data"
if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  log "Backing up existing V2 database volume..."
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop api || true
  docker run --rm -v "$VOLUME:/data:ro" -v "$BACKUP_ROOT:/backup" alpine:3.20 \
    sh -c "tar czf /backup/batman-v2-data-$(date +%Y%m%d-%H%M%S).tgz -C /data ."
fi

log "Building and starting BAT-PANEL V2..."
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

log "Waiting for API health check..."
healthy=0
for _ in $(seq 1 30); do
  PANEL_PORT="$(sed -n 's/^PANEL_PORT=//p' "$INSTALL_DIR/$ENV_FILE" | tail -n1)"
  PANEL_PORT="${PANEL_PORT:-8000}"
  if curl --fail --silent --max-time 3 "http://127.0.0.1:$PANEL_PORT/api/health" > "$TMP_DIR/health.json" \
    && grep -Eq '"ok"[[:space:]]*:[[:space:]]*true' "$TMP_DIR/health.json" \
    && curl --fail --silent --max-time 3 "http://127.0.0.1:$PANEL_PORT/" > "$TMP_DIR/dashboard.html" \
    && grep -Eiq '<!doctype[[:space:]]+html|<html([[:space:]>])' "$TMP_DIR/dashboard.html" \
    && curl --fail --silent --output /dev/null --max-time 3 "http://127.0.0.1:$PANEL_PORT/assets/styles.css"; then
    healthy=1
    break
  fi
  sleep 2
done

if [[ "$healthy" -ne 1 ]]; then
  log "V2 health check failed."
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=100 || true
  if [[ -n "$PREVIOUS_DIR" && -d "$PREVIOUS_DIR" ]]; then
    log "Restoring previous V2 application files and restarting previous build..."
    rm -rf "$INSTALL_DIR"
    cp -a "$PREVIOUS_DIR" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    docker compose -p "$PROJECT" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build || true
  fi
  die "V2 did not pass its health check. Existing Batman V1 was not stopped or modified."
fi

log "Batman V2 is running."
echo
echo "========== INSTALLATION RESULT =========="
cat "$TMP_DIR/health.json"
echo
PANEL_PORT="$(sed -n 's/^PANEL_PORT=//p' "$INSTALL_DIR/$ENV_FILE" | tail -n1)"
echo "V2 Panel:     http://SERVER-IP:${PANEL_PORT:-8000}"
echo "V2 API:       http://SERVER-IP:${PANEL_PORT:-8000}/api"
echo "API docs:     http://SERVER-IP:${PANEL_PORT:-8000}/api/docs"
echo "Credentials:  /root/batman-v2-credentials.txt"
if [[ -f /root/batman-v2-credentials.txt ]]; then
  echo
  cat /root/batman-v2-credentials.txt
else
  echo "Admin credentials were preserved from the previous installation."
  echo "See $INSTALL_DIR/$ENV_FILE (root-only; do not share it)."
fi
echo
echo "Backup directory: $BACKUP_ROOT"
echo "Terminal menu: bat-panel"
echo "Support: https://t.me/shocavpnadmin"
echo "Firewall: TCP $PANEL_PORT (UFW rule added only if UFW was active). Check provider firewall too."
echo "Batman V1 was left running and unchanged."
echo "IMPORTANT: V2 now includes a working API-connected web dashboard, but live VPN provisioning and V1 user migration are not implemented."
