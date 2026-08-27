#!/usr/bin/env bash
# Writes .env for telegram bot from CI/CD exported variables.
set -euo pipefail

TARGET_DIR="${1:-.}"
ENV_FILE="$TARGET_DIR/.env"

mkdir -p "$TARGET_DIR"

cat > "$ENV_FILE" <<EOF
TELEGRAM_SECRET=${TELEGRAM_SECRET:-}
TELEGRAM_BOT_SHARED_SECRET=${TELEGRAM_BOT_SHARED_SECRET:-}
TELEGRAM_PROXY=${TELEGRAM_PROXY:-}
TELEGRAM_API_BASE_URL=${TELEGRAM_API_BASE_URL:-https://api.telegram.org}
SWINGFOX_API_URL=${SWINGFOX_API_URL:-https://127.0.0.1:3001/api}
SWINGFOX_UPLOADS_URL=${SWINGFOX_UPLOADS_URL:-https://swingfox.ru/uploads}
PUBLIC_WEB_URL=${PUBLIC_WEB_URL:-https://swingfox.ru}
EOF

chmod 600 "$ENV_FILE"
echo "Wrote $ENV_FILE"
