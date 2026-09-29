#!/usr/bin/env bash
# Redeploy telegram bot avoiding docker-compose 1.29 "ContainerConfig" recreate bug.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

BUILD="${1:-build}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose / docker-compose not found" >&2
  exit 1
fi

compose() {
  "${COMPOSE[@]}" "$@"
}

echo ">>> Stop and remove old telegram bot containers"
set +e
compose down --remove-orphans 2>/dev/null
docker rm -f swingfox_telegram_bot 2>/dev/null

while IFS= read -r cid; do
  [ -n "$cid" ] && docker rm -f "$cid" 2>/dev/null
done < <(docker ps -aq --filter "name=swingfox_telegram" 2>/dev/null)

while IFS= read -r cid; do
  [ -n "$cid" ] && docker rm -f "$cid" 2>/dev/null
done < <(docker ps -aq --filter "label=com.docker.compose.project=swingfox_telegram" 2>/dev/null)

while IFS= read -r name; do
  [ -n "$name" ] && docker rm -f "$name" 2>/dev/null
done < <(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -E 'swingfox_telegram|telegram-bot' || true)

set -e

echo ">>> Start telegram bot (${COMPOSE[*]})"
# Не используем --force-recreate: на compose 1.29 он читает ContainerConfig у старого контейнера.
compose rm -f -s telegram-bot 2>/dev/null || true

if [ "$BUILD" = "build" ]; then
  compose build telegram-bot
fi
compose up -d --no-deps telegram-bot

compose ps
compose logs --tail 30 telegram-bot
