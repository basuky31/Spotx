import os
import asyncio
from flask import Flask, request, redirect
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests

app = Flask(__name__)

# Zugangsdaten aus den Render-Einstellungen (Environment Variables)
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
RENDER_URL = os.environ.get("RENDER_URL")  # z.B. https://spotx.onrender.com
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

REDIRECT_URI = f"{RENDER_URL}/callback" if RENDER_URL else "http://localhost:10000/callback"

# Globaler Bot-Speicher
telegram_app = None

# ----------------- WEB-SERVER (FLASK) -----------------

@app.route("/")
def index():
    return "Spotx Bot Server läuft!"

@app.route("/login")
def login():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Fehler: Keine Telegram User-ID übergeben.", 400

    # Weiterleitung zum offiziellen Spotify-Login
    scope = "user-read-private user-read-email"
    auth_url = (
        f"https://accounts.spotify.com/authorize?"
        f"response_type=code&client_id={SPOTIFY_CLIENT_ID}"
        f"&scope={scope}&redirect_uri={REDIRECT_URI}&state={user_id}"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    user_id = request.args.get("state")  # Telegram-ID wird zurückgeliefert

    if not code or not user_id:
        return "Login abgebrochen oder fehlgeschlagen.", 400

    # Tokens von Spotify anfordern
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
        # Nachricht mit den Tokens zurück an deinen Telegram-Chat senden
        msg = (
            "✅ **Erfolgreich eingeloggt!**\n\n"
            f"🔑 **Access Token:**\n`{access_token}`\n\n"
            f"🔄 **Refresh Token:**\n`{refresh_token}`"
        )
        
        if telegram_app and telegram_app.loop:
            asyncio.run_coroutine_threadsafe(
                telegram_app.bot.send_message(chat_id=int(user_id), text=msg, parse_mode="Markdown"),
                telegram_app.loop
            )

        return "<h1>Erfolgreich eingeloggt! Du kannst diesen Tab jetzt schließen und zu Telegram zurückkehren.</h1>"
    else:
        return f"Fehler beim Abrufen der Daten: {data.get('error_description', 'Unbekannter Fehler')}", 400

# ----------------- TELEGRAM BOT -----------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    login_link = f"{RENDER_URL}/login?user_id={user_id}"
    
    await update.message.reply_text(
        f"Hallo! Klicke auf den folgenden Link, um dich sicher bei Spotify anzumelden:\n\n"
        f"🔗 [Hier bei Spotify einloggen]({login_link})",
        parse_mode="Markdown"
    )

# ----------------- SERVER & BOT STARTEN -----------------

if __name__ == "__main__":
    # Telegram Bot initialisieren
    telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("login", start_command))

    # Event-Loop vorbereiten
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegram_app.loop = loop

    # Bot-Start auf dem Loop einplanen
    loop.run_until_complete(telegram_app.initialize())
    loop.run_until_complete(telegram_app.start())
    loop.run_until_complete(telegram_app.updater.start_polling())

    # Webserver auf Render-Port starten
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
