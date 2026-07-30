import os
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

# Umweltvariablen aus Render
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
RENDER_URL = os.environ.get("RENDER_URL")  # https://spotx1.onrender.com
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

REDIRECT_URI = f"{RENDER_URL}/callback" if RENDER_URL else "http://localhost:10000/callback"

def send_telegram_msg(chat_id, text):
    if not TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Fehler beim Senden: {e}")

# ----------------- ROUTEN -----------------

@app.route("/")
def index():
    return "Spotx Bot Server läuft!"

# Empfänger für Telegram Webhook
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    
    if "message" in data and "text" in data["message"]:
        text = data["message"]["text"].strip()
        chat_id = data["message"]["chat"]["id"]
        
        if text.startswith("/start") or text.startswith("/login"):
            login_link = f"{RENDER_URL}/login?user_id={chat_id}"
            msg = (
                f"Hallo! Klicke auf den folgenden Link, um dich bei Spotify anzumelden:\n\n"
                f"🔗 [Bei Spotify einloggen]({login_link})"
            )
            send_telegram_msg(chat_id, msg)
            
    return "OK", 200

# Spotify Login Route
@app.route("/login")
def login():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Fehler: Keine User-ID übergeben.", 400

    scope = "user-read-private user-read-email"
    auth_url = (
        f"https://accounts.spotify.com/authorize?"
        f"response_type=code&client_id={SPOTIFY_CLIENT_ID}"
        f"&scope={scope}&redirect_uri={REDIRECT_URI}&state={user_id}"
    )
    return redirect(auth_url)

# Spotify Callback Route
@app.route("/callback")
def callback():
    code = request.args.get("code")
    user_id = request.args.get("state")

    if not code or not user_id:
        return "Login fehlgeschlagen.", 400

    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }

    res = requests.post(token_url, data=payload)
    data = res.json()

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if access_token:
        msg = (
            "✅ **Erfolgreich eingeloggt!**\n\n"
            f"🔑 **Access Token:**\n`{access_token}`\n\n"
            f"🔄 **Refresh Token:**\n`{refresh_token}`"
        )
        send_telegram_msg(int(user_id), msg)
        return "<h1>Login erfolgreich! Du kannst das Fenster jetzt schließen.</h1>"
    else:
        return f"Fehler: {data.get('error_description', 'Unbekannter Fehler')}", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
