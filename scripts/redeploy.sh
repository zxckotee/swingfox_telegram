#!/usr/bin/env bash
# Redeploy telegram bot avoiding docker-compose 1.29 "ContainerConfig" recreate bug.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

BUILD="${1:-build}"

echo ">>> Stop and remove old telegram bot containers"
set +e
docker-compose stop telegram-bot 2>/dev/null
docker rm -f swingfox_telegram_bot 2>/dev/null

while IFS= read -r cid; do
  [ -n "$cid" ] && docker rm -f "$cid" 2>/dev/null
done < <(docker ps -aq --filter "name=swingfox_telegram" 2>/dev/null)

while IFS= read -r name; do
  [ -n "$name" ] && docker rm -f "$name" 2>/dev/null
done < <(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -E 'swingfox_telegram|telegram-bot' || true)

set -e

echo ">>> Start telegram bot"
if [ "$BUILD" = "build" ]; then
  docker-compose up -d --build --force-recreate --no-deps telegram-bot
else
  docker-compose up -d --force-recreate --no-deps telegram-bot
fi

docker-compose ps
docker-compose logs --tail 30 telegram-bot
