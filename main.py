import os
import json
import tempfile
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from gtts import gTTS
from telegram import Update
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
    "AQ.Ab8RN6KFTZJe90GANt5eRpki_j0j_MeizdW-FwknVz37gBIizQ"
)
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "8979035511:AAFKhUJy2mVg52MDcYMshefeNml_EJd6DUQ"
)

# Simple web server to keep Render service alive
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# --- BOT HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🚀 *Language Bot Ready!*\n\n"
        "Send me any text in Russian, German, or English and I will translate, explain, and provide pronunciation audio!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        # Direct REST API call bypassing SDK auth restrictions
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
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

        # Generate audio pronunciation
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

def main():
    threading.Thread(target=run_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Bot is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
