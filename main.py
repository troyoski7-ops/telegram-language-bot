import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Fetch token safely from Render Environment Variables
TOKEN = os.getenv("BOT_TOKEN")

# Default target language
DEFAULT_TARGET = "ml"  # Malayalam ('en' for English, 'de' for German, etc.)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send instructions on bot start."""
    help_text = (
        "🌐 **Universal Translator Bot**\n\n"
        "Send me text in **any language**, and I will translate it!\n\n"
        "• Current target: **Malayalam**\n"
        "• Change target language anytime by typing:\n"
        "`/set en` (for English)\n"
        "`/set ml` (for Malayalam)\n"
        "`/set de` (for German)\n"
        "`/set hi` (for Hindi)"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change target language dynamically."""
    if context.args:
        lang_code = context.args[0].lower()
        context.user_data["target_lang"] = lang_code
        await update.message.reply_text(f"✅ Target language set to: `{lang_code}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Please specify a language code. Example: `/set en`", parse_mode="Markdown")

async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate incoming user messages."""
    user_text = update.message.text
    if not user_text:
        return

    target_lang = context.user_data.get("target_lang", DEFAULT_TARGET)

    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(user_text)
        await update.message.reply_text(translated)
    except Exception as e:
        logging.error(f"Error during translation: {e}")
        await update.message.reply_text("❌ Translation failed. Please check the language code or try again.")

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is missing on Render!")

    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set", set_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
