import os
import json
import tempfile
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from gtts import gTTS
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    "AQ.Ab8RN6IERW99GmIEEcXjveKYRX-NA35ij2dlkTaB6s35Q9_DOA"
)
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "8979035511:AAHGkERqUcEQunaF3eTwkOMLNjr1x33rAzs"
)

# Global bot state (ON by default)
BOT_ACTIVE = True

# --- RENDER KEEP-ALIVE SERVER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# --- COMMAND HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_ACTIVE
    BOT_ACTIVE = True
    welcome_text = (
        "🟢 *Bot is now ON & ACTIVE!*\n\n"
        "Send any Russian, German, or English text and I will translate it to Malayalam and English with audio pronunciation.\n\n"
        "• `/stop` — Turn bot OFF\n"
        "• `/start` — Turn bot ON\n"
        "• `/status` — Check status"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_ACTIVE
    BOT_ACTIVE = False
    stop_text = (
        "🔴 *Bot is now OFF (PAUSED)*\n\n"
        "I will ignore messages until you send `/start`."
    )
    await update.message.reply_text(stop_text, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_ACTIVE:
        msg = "🟢 Status: *RUNNING (ON)*\nReady to translate."
    else:
        msg = "🔴 Status: *STOPPED (OFF)*\nSend `/start` to activate."
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- MESSAGE HANDLER ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_ACTIVE
    if not BOT_ACTIVE:
        return

    user_text = update.message.text
    if not user_text:
        return

    await update.message.chat.send_action("typing")

    prompt = (
        f"The user says: '{user_text}'.\n"
        "1. Identify the language.\n"
        "2. Translate it accurately to Malayalam and English.\n"
        "3. Provide a brief helpful explanation or reply in the target language."
    )

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if "candidates" in data and data["candidates"]:
            reply_text = data["candidates"][0]["content"]["parts"][0]["text"]
            await update.message.reply_text(reply_text)
        elif "error" in data:
            await update.message.reply_text(f"API Error: {data['error'].get('message', 'Unknown error')}")
        else:
            await update.message.reply_text("Could not generate a response.")

        # Audio Pronunciation
        try:
            tts = gTTS(text=user_text, lang='ru')
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tts.save(f.name)
                audio_path = f.name
            
            with open(audio_path, 'rb') as voice_file:
                await update.message.reply_voice(voice_file)
            os.remove(audio_path)
        except Exception:
            pass

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# --- AUTO REGISTER COMMAND MENU ---
async def post_init(application):
    commands = [
        BotCommand("start", "Turn bot ON and start translating"),
        BotCommand("stop", "Turn bot OFF (pause translations)"),
        BotCommand("status", "Check ON/OFF status"),
    ]
    await application.bot.set_my_commands(commands)

def main():
    threading.Thread(target=run_server, daemon=True).start()
    
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Bot is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
