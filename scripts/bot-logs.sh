#!/usr/bin/env bash
# Collect bot crash diagnostics on the server (run as root).
set -euo pipefail

CONTAINER="${BOT_CONTAINER_NAME:-swingfox_telegram_bot}"

echo "============================================"
echo "  SwingFox Telegram bot diagnostics"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Container '$CONTAINER' not found."
  echo "Running containers:"
  docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep -i telegram || true
  exit 1
fi

echo ""
echo "=== Container state ==="
docker inspect "$CONTAINER" --format \
  'Status={{.State.Status}} ExitCode={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}} Error={{.State.Error}}
Started={{.State.StartedAt}} Finished={{.State.FinishedAt}} RestartCount={{.RestartCount}}'

echo ""
echo "=== docker logs (last 300 lines) ==="
echo "(If you only see «Attaching to», you ran «docker-compose up» without -d."
echo " Use: docker logs $CONTAINER --tail 300)"
docker logs "$CONTAINER" --tail 300 2>&1 || true

echo ""
echo "=== Persistent file log (/app/data/bot.log) ==="
if docker exec "$CONTAINER" test -f /app/data/bot.log 2>/dev/null; then
  docker exec "$CONTAINER" tail -n 300 /app/data/bot.log 2>&1 || true
else
  echo "(no bot.log yet — deploy build with persistent logging)"
fi

echo ""
echo "=== Host OOM hints (last 20) ==="
if command -v dmesg >/dev/null 2>&1; then
  dmesg -T 2>/dev/null | grep -iE 'oom|killed process' | tail -n 20 || echo "(no OOM lines or dmesg restricted)"
else
  echo "(dmesg not available)"
fi
