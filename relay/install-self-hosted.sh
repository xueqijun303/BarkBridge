#!/usr/bin/env bash
set -euo pipefail

PORT="${BARKBRIDGE_RELAY_PORT:-8787}"
SECRET="${BARKBRIDGE_RELAY_SECRET:-}"
APP_DIR="/opt/barkbridge-relay"
ENV_FILE="/etc/barkbridge-relay.env"
SERVICE_FILE="/etc/systemd/system/barkbridge-relay.service"

if [[ -z "$SECRET" ]]; then
  echo "BARKBRIDGE_RELAY_SECRET is required" >&2
  echo "Example: sudo BARKBRIDGE_RELAY_SECRET='your-secret' bash relay/install-self-hosted.sh" >&2
  exit 1
fi

if ss -ltn "( sport = :$PORT )" | grep -q ":$PORT"; then
  echo "Port $PORT is already in use. Choose another port with BARKBRIDGE_RELAY_PORT=8788." >&2
  exit 1
fi

id -u barkbridge >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin barkbridge
mkdir -p "$APP_DIR"
install -m 0755 relay/self-hosted-relay.py "$APP_DIR/self-hosted-relay.py"
install -m 0644 relay/barkbridge-relay.service "$SERVICE_FILE"

cat > "$ENV_FILE" <<EOF
BARKBRIDGE_RELAY_PORT=$PORT
BARKBRIDGE_RELAY_DB=$APP_DIR/relay.sqlite3
BARKBRIDGE_RELAY_SECRET=$SECRET
EOF
chmod 0600 "$ENV_FILE"
chown -R barkbridge:barkbridge "$APP_DIR"

systemctl daemon-reload
systemctl enable --now barkbridge-relay.service
systemctl --no-pager status barkbridge-relay.service

echo
echo "BarkBridge relay is installed:"
echo "  http://$(hostname -I | awk '{print $1}'):$PORT/"
