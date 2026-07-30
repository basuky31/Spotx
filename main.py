import os
import asyncio
from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

async def get_spotify_cookies(email: str, password: str) -> str:
    """Steuert den Browser, loggt sich ein und liest die Cookies aus."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login-Seite aufrufen
            await page.goto("https://accounts.spotify.com/de/login")
            
            # Zugangsdaten eingeben
            await page.fill("input#login-username", email)
            await page.fill("input#login-password", password)
            await page.click("button#login-button")

            # Warten, bis der Login abgeschlossen ist (Weiterleitung auf Übersicht)
            await page.wait_for_url("https://account.spotify.com/*", timeout=15000)

            # Cookies abgreifen
            cookies = await context.cookies()
            sp_dc = next((c['value'] for c in cookies if c['name'] == 'sp_dc'), None)
            sp_key = next((c['value'] for c in cookies if c['name'] == 'sp_key'), None)

            await browser.close()

            if sp_dc:
                res = f"🔑 **Deine Spotify Cookies:**\n\n`sp_dc`:\n`{sp_dc}`\n"
                if sp_key:
                    res += f"\n`sp_key`:\n`{sp_key}`"
                return res
            else:
                return "❌ Login fehlgeschlagen oder Cookie nicht gefunden (Falsche Daten oder Captcha-Sperre)."

        except Exception as e:
            await browser.close()
            return f"❌ Fehler beim Einloggen: {str(e)}"

# Handler für eingehende Nachrichten (Format: email:passwort)
async def handle_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if ":" not in text:
        await update.message.reply_text("Sende mir deine Daten im Format:\n`E-Mail:Passwort`", parse_mode="Markdown")
        return

    email, password = text.split(":", 1)
    await update.message.reply_text("⏳ Logge bei Spotify ein, bitte einen Moment Geduld...")

    result = await get_spotify_cookies(email.strip(), password.strip())
    await update.message.reply_text(result, parse_mode="Markdown")
