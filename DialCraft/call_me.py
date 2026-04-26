"""
DialCraft — Call yourself to test the voice agent.

Usage:
    1. Start the server:   python main.py
    2. Start ngrok:        ngrok http 8000
    3. Run this script:    python call_me.py

The script will:
    - Auto-detect your ngrok URL
    - Configure Twilio to connect to your local server
    - Place a call to your phone
"""
import os
import requests
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# ── Twilio Credentials ────────────────────────────────────────────────
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_phone = os.getenv("TWILIO_PHONE_NUMBER")
to_phone = os.getenv("DESTINATION_PHONE_NUMBER")


def get_ngrok_url():
    """Try to auto-detect the ngrok public URL."""
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
        tunnels = resp.json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https":
                return t["public_url"]
        if tunnels:
            return tunnels[0]["public_url"]
    except Exception:
        pass
    return None


# ── Auto-detect ngrok or fall back to env var ──────────────────────────
ngrok_url = get_ngrok_url()
if ngrok_url:
    print(f"🔗 Detected ngrok URL: {ngrok_url}")
else:
    ngrok_url = os.getenv("NGROK_URL", "")
    if not ngrok_url:
        print("❌ Could not detect ngrok. Make sure ngrok is running (ngrok http 8000)")
        print("   Or set NGROK_URL in your .env file.")
        exit(1)
    print(f"🔗 Using NGROK_URL from .env: {ngrok_url}")

# ── Build inline TwiML ────────────────────────────────────────────────
# This tells Twilio to connect the call audio to our WebSocket server
host = ngrok_url.replace("https://", "").replace("http://", "")
twiml_url = f"{ngrok_url}/twiml"

# ── Make the call ─────────────────────────────────────────────────────
client = Client(account_sid, auth_token)
call = client.calls.create(
    url=twiml_url,
    to=to_phone,
    from_=from_phone,
    method="POST",
)

print(f"📞 Dialing {to_phone}...")
print(f"   Call SID: {call.sid}")
print(f"   TwiML endpoint: {twiml_url}")
print(f"   WebSocket: wss://{host}/media-stream")