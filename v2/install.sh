#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash v2/install.sh"
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine and the Compose plugin first:"
  echo "https://docs.docker.com/engine/install/ubuntu/"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is required."
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Creating a private .env file..."
  read -r -p "Admin username [admin]: " ADMIN_USERNAME
  ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
  while true; do
    read -r -s -p "Set admin password (minimum 14 characters): " ADMIN_PASSWORD
    echo
    [[ ${#ADMIN_PASSWORD} -ge 14 ]] && break
    echo "Password is too short."
  done
  JWT_SECRET="$(openssl rand -hex 48)"
  umask 077
  cat > .env <<EOF
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
JWT_SECRET=$JWT_SECRET
TOKEN_TTL_HOURS=8
DATABASE_URL=sqlite:////data/batman-v2.db
EOF
  chmod 600 .env
fi

echo "Starting Batman VPN Panel V2 control-plane MVP..."
docker compose -p batman-v2 up -d --build
echo
echo "API health:"
sleep 3
curl --fail --silent http://127.0.0.1:8000/api/health || {
  echo "Container did not become healthy. Check: docker compose logs --tail=100"
  exit 1
}
echo
echo "API is bound to localhost only: http://127.0.0.1:8000"
echo "API docs: http://127.0.0.1:8000/api/docs"
echo "This MVP does not yet provision VPN accounts or change firewall/network settings."
