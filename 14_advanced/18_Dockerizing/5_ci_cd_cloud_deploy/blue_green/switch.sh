#!/usr/bin/env sh
# Usage: ./switch.sh green   |   ./switch.sh blue
set -e
cd "$(dirname "$0")"
COLOR="$1"
[ "$COLOR" = "blue" ] || [ "$COLOR" = "green" ] || { echo "usage: $0 blue|green"; exit 1; }
# 1. Never switch to a version that is not ready.
docker compose exec -T "$COLOR" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready', timeout=2)" \
  || { echo "$COLOR is not ready - staying where we are"; exit 1; }
# 2. Point the upstream at the new colour and reload nginx (graceful).
printf 'upstream live { server %s:8000; }' "$COLOR" > active.conf
docker compose exec -T proxy nginx -s reload
echo "Live traffic -> $COLOR"
