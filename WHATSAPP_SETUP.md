# CampAlly — WhatsApp AI Agent Setup

Talk to the smart-parking + safety system over WhatsApp. Claude (Opus 4.8)
reads live parking occupancy and files emergency / lost & found reports.

```
WhatsApp ─▶ Twilio Sandbox ─▶ ngrok ─▶ Django /whatsapp/webhook/ ─▶ Claude agent ─▶ your DB
```

## What the agent can do
- **"Where can I park?"** → lists Redemption City car parks with live free spots
- **Shares 📍 location** → routes to the *nearest* open car park + Google Maps link
- **"There's a medical emergency at Car Park C"** → files an emergency (shows on the dashboard)
- **"I lost a black bag near the arena"** → files a lost & found report

## 1. Install dependencies
```bash
pip install -r requirements.txt        # adds anthropic + twilio
```
> ⚠️ The committed `venv/` was built on a Linux machine and won't run on this Mac
> (its `python3` points at a broken `/usr/bin/python3`). Create a fresh env:
> `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

## 2. Add your Anthropic API key
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```
(Get one at https://console.anthropic.com — a demo costs pennies.)

## 3. Seed the real Redemption Camp car parks
```bash
python manage.py migrate
python manage.py seed_redemption_parking      # add --reset to wipe old zones first
```
Creates Car Park A/B/C, D, F, V, New Arena Parking and Odofin with real GPS coords.

## 4. Run the server + expose it
```bash
python manage.py runserver            # terminal 1
ngrok http 8000                       # terminal 2  → copy the https URL
```
(Install ngrok from https://ngrok.com if needed.)

## 5. Point Twilio's WhatsApp Sandbox at the webhook
1. Twilio Console → **Messaging → Try it out → Send a WhatsApp message**.
2. Join the sandbox: send the `join <code>` message from your phone to the
   sandbox number.
3. In **Sandbox settings**, set **"When a message comes in"** to:
   ```
   https://<your-ngrok-subdomain>.ngrok-free.app/whatsapp/webhook/
   ```
   Method: **HTTP POST**. Save.

## 6. Text it 🎉
From your phone (joined to the sandbox), try:
- `Where can I park?`
- Share your **Location** (📎 → Location)
- `Someone fainted near Car Park V`
- `I found a child's shoe at the arena`

## Notes
- Conversation memory is in-process (per phone number) — fine for the demo.
- Webhook is `@csrf_exempt`; for production, verify Twilio's `X-Twilio-Signature`.
- Want faster/cheaper replies? Change `MODEL` in `App/whatsapp_agent.py` to
  `claude-sonnet-4-6` or `claude-haiku-4-5`.
