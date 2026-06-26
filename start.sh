#!/bin/bash
# ── CampAlly full startup: Django + ngrok + auto-update Twilio webhook ───────

PORT="${1:-8000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Load .env ────────────────────────────────────────────────────────────────
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
  echo "✓ Loaded .env"
fi

# ── Kill any existing processes ───────────────────────────────────────────────
pkill -f "manage.py runserver" 2>/dev/null
pkill -f ngrok 2>/dev/null
sleep 1

# ── Start Django ─────────────────────────────────────────────────────────────
echo "▶ Starting Django on port $PORT..."
source "$SCRIPT_DIR/venv_new/bin/activate"
python "$SCRIPT_DIR/manage.py" runserver "$PORT" > /tmp/django.log 2>&1 &
DJANGO_PID=$!
echo "  Django PID: $DJANGO_PID"

# ── Start ngrok ───────────────────────────────────────────────────────────────
echo "▶ Starting ngrok..."
ngrok http $PORT --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

# ── Wait for ngrok to get a URL ───────────────────────────────────────────────
echo "  Waiting for ngrok tunnel..."
NGROK_URL=""
for i in $(seq 1 15); do
  sleep 1
  NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('tunnels',[]); print(t[0]['public_url'] if t else '')" 2>/dev/null)
  [ -n "$NGROK_URL" ] && break
done

if [ -z "$NGROK_URL" ]; then
  echo "❌ ngrok failed to start. Check /tmp/ngrok.log"
  exit 1
fi

WEBHOOK_URL="$NGROK_URL/whatsapp/webhook/"
echo ""
echo "✅ Django:  http://localhost:$PORT"
echo "✅ ngrok:   $NGROK_URL"
echo "✅ Webhook: $WEBHOOK_URL"

# ── Auto-update Twilio sandbox webhook ───────────────────────────────────────
if [ -n "$TWILIO_ACCOUNT_SID" ] && [ -n "$TWILIO_AUTH_TOKEN" ]; then
  echo ""
  echo "▶ Updating Twilio sandbox webhook..."
  RESPONSE=$(curl -s -X POST \
    "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/IncomingPhoneNumbers.json" \
    -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" 2>/dev/null)

  # Update sandbox config
  SANDBOX_RESPONSE=$(curl -s -X POST \
    "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/SandboxParticipants.json" \
    -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
    -d "SmsSandboxUrl=$WEBHOOK_URL" 2>/dev/null)

  echo "  Twilio updated → $WEBHOOK_URL"
else
  echo ""
  echo "⚠️  Twilio credentials not set — update webhook manually:"
  echo "   $WEBHOOK_URL"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  CampAlly is live. Press Ctrl+C to stop."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Keep alive — show live logs ───────────────────────────────────────────────
tail -f /tmp/django.log
