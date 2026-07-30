import os
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

# Environment Variables von Render
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
RENDER_URL = os.environ.get("RENDER_URL", "https://spotx1.onrender.com")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Exakte HTTPS Callback-URL
REDIRECT_URI = "https://spotx1.onrender.com/callback"

def send_telegram_msg(chat_id, text):
    if not TELEGRAM_TOKEN:
        print("[FEHLER] Kein TELEGRAM_TOKEN hinterlegt!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"[TELEGRAM RESPONSE] Status: {r.status_code} | Body: {r.text}")
    except Exception as e:
        print(f"[FEHLER] Ausführen von send_telegram_msg fehlgeschlagen: {e}")

@app.route("/")
def index():
    return "Spotx Bot Server läuft!", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True, silent=True)
        print(f"[EMPFANGEN] Data: {data}")
        
        if data and "message" in data and "text" in data["message"]:
            text = data["message"]["text"].strip()
            chat_id = data["message"]["chat"]["id"]

            if text.startswith("/start") or text.startswith("/login"):
                # Direktlink zu Spotify ohne Umweg über /login
                scope = "user-read-private user-read-email"
                auth_url = (
                    f"https://accounts.spotify.com/authorize?"
                    f"response_type=code&client_id={SPOTIFY_CLIENT_ID}"
                    f"&scope={scope}&redirect_uri={REDIRECT_URI}&state={chat_id}"
                )
                
                msg = (
                    "Hallo!\n\n"
                    f'Klicke auf den Link, um dich bei Spotify anzumelden:\n'
                    f'<a href="{auth_url}">👉 Hier bei Spotify einloggen</a>'
                )
                send_telegram_msg(chat_id, msg)
            else:
                msg = f"Empfangen: <code>{text}</code>"
                send_telegram_msg(chat_id, msg)

    except Exception as e:
        print(f"[FEHLER Webhook] {e}")

    return "OK", 200

@app.route("/callback")
def callback():
    code = request.args.get("code")
    user_id = request.args.get("state")

    if not code or not user_id:
        return "Login fehlgeschlagen: Fehlender Code oder State.", 400

    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }

    try:
        res = requests.post(token_url, data=payload, timeout=10)
        data = res.json()
        print(f"[SPOTIFY CALLBACK DATA] {data}")

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if access_token:
            msg = (
                "✅ <b>Erfolgreich bei Spotify eingeloggt!</b>\n\n"
                f"🔑 <b>Access Token:</b>\n<code>{access_token}</code>\n\n"
                f"🔄 <b>Refresh Token:</b>\n<code>{refresh_token}</code>"
            )
            send_telegram_msg(int(user_id), msg)
            return "<h1>Login erfolgreich! Du kannst dieses Fenster schliessen und zu Telegram zurueckkehren.</h1>"
        else:
            err_msg = data.get("error_description", "Unbekannter Fehler")
            return f"<h1>Fehler von Spotify: {err_msg}</h1>", 400
            
    except Exception as e:
        print(f"[FEHLER Callback] {e}")
        return f"<h1>Interner Fehler: {e}</h1>", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
