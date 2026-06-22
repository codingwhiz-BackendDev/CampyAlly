#!/bin/bash
# ── CampAlly Django startup script ──────────────────────────────────────────
# Usage: ./start.sh [port]
# Loads .env then starts the Django dev server.

set -e

PORT="${1:-8000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load .env if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
  echo "✓ Loaded .env"
fi

echo "✓ ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:12}..."
echo ""
echo "Starting Django on port $PORT..."
echo "Webhook URL (local): http://127.0.0.1:$PORT/whatsapp/webhook/"
echo ""

exec "$SCRIPT_DIR/venv_new/bin/python" "$SCRIPT_DIR/manage.py" runserver "$PORT"
