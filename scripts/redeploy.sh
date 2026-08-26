#!/usr/bin/env bash
# Redeploy telegram bot avoiding docker-compose 1.29 "ContainerConfig" recreate bug.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

BUILD="${1:-build}"

echo ">>> Stop and remove old telegram bot containers"
docker-compose stop telegram-bot 2>/dev/null || true
docker-compose rm -f -v telegram-bot 2>/dev/null || true

docker ps -a --format '{{.Names}}' | grep -E 'swingfox_telegram_bot|telegram-bot' | while read -r name; do
  docker rm -f "$name" 2>/dev/null || true
done

echo ">>> Start telegram bot"
if [ "$BUILD" = "build" ]; then
  docker-compose up -d --build --force-recreate --no-deps telegram-bot
else
  docker-compose up -d --force-recreate --no-deps telegram-bot
fi

docker-compose ps
docker-compose logs --tail 30 telegram-bot
