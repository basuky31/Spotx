import os
import asyncio
import requests
from flask import Flask, request, redirect
from telegram import Update, Bot

app = Flask(__name__)

# Umweltvariablen aus Render auslesen
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
RENDER_URL = os.environ.get("RENDER_URL")  # z.B. https://spotx-cqms.onrender.com
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

REDIRECT_URI = f"{RENDER_URL}/callback" if RENDER_URL else "http://localhost:10000/callback"

# Telegram Bot instanziieren
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

# Helper-Funktion zum asynchronen Senden von Nachrichten
def send_telegram_message(chat_id, text, parse_mode="Markdown"):
    if not bot:
        return
    asyncio.run(bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode))

# ----------------- FLASK & WEBHOOK ROUTEN -----------------

@app.route("/")
def index():
    return "Spotx Bot Server läuft einwandfrei!"

# Webhook-Empfänger für Telegram-Nachrichten
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    if not TELEGRAM_TOKEN or not bot:
        return "Token fehlt", 500
        
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        
        if update and update.message and update.message.text:
            text = update.message.text.strip()
            chat_id = update.message.chat.id
            
            if text.startswith("/start") or text.startswith("/login"):
                login_link = f"{RENDER_URL}/login?user_id={chat_id}"
                msg = (
                    f"Hallo! Klicke auf den folgenden Link, um dich sicher bei Spotify einzuloggen:\n\n"
                    f"🔗 [Hier bei Spotify einloggen]({login_link})"
                )
                send_telegram_message(chat_id, msg)
    except Exception as e:
        print(f"Fehler im Webhook: {e}")
            
    return "OK", 200

# Spotify Login Route
@app.route("/login")
def login():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Fehler: Keine Telegram User-ID übergeben.", 400

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
        return "Login abgebrochen oder fehlerhaft.", 400

    # Token-Austausch bei Spotify
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
            "✅ **Erfolgreich bei Spotify eingeloggt!**\n\n"
            f"🔑 **Access Token:**\n`{access_token}`\n\n"
            f"🔄 **Refresh Token:**\n`{refresh_token}`"
        )
        send_telegram_message(int(user_id), msg)
        return "<h1>Login erfolgreich! Du kannst diesen Tab jetzt schließen und zu Telegram zurückkehren.</h1>"
    else:
        error_msg = data.get('error_description', 'Unbekannter Fehler')
        return f"Fehler beim Abrufen der Tokens: {error_msg}", 400

# ----------------- SERVER START & WEBHOOK REGISTRIERUNG -----------------

if __name__ == "__main__":
    # Webhook automatisch bei Telegram registrieren
    if RENDER_URL and TELEGRAM_TOKEN and bot:
        webhook_url = f"{RENDER_URL}/{TELEGRAM_TOKEN}"
        try:
            asyncio.run(bot.set_webhook(url=webhook_url))
            print(f"Webhook erfolgreich gesetzt auf: {webhook_url}")
        except Exception as e:
            print(f"Fehler beim Setzen des Webhooks: {e}")

    # Webserver starten
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
