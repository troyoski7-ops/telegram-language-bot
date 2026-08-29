import os
import logging
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Fetch token safely from Render Environment Variables
TOKEN = os.getenv("BOT_TOKEN")

# All 20 Countries and Languages
LANGUAGES = {
    "ml": "🇮🇳 Malayalam",
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "ru": "🇷🇺 Russian",
    "de": "🇩🇪 German",
    "fr": "🇫🇷 French",
    "es": "🇪🇸 Spanish",
    "ar": "🇪🇬 Arabic",
    "fa": "🇮🇷 Persian",
    "tr": "🇹🇷 Turkish",
    "it": "🇮🇹 Italian",
    "pt": "🇧🇷 Portuguese",
    "zh-CN": "🇨🇳 Mandarin Chinese",
    "ja": "🇯🇵 Japanese",
    "ko": "🇰🇷 Korean",
    "id": "🇮🇩 Indonesian",
    "uk": "🇺🇦 Ukrainian",
    "uz": "🇺🇿 Uzbek",
    "kk": "🇰🇿 Kazakh",
    "az": "🇦🇿 Azerbaijani",
    "ur": "🇵🇰 Urdu",
}

def get_language_keyboard():
    keyboard = []
    items = list(LANGUAGES.items())
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"setlang_{items[i][0]}")]
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(items[i + 1][1], callback_data=f"setlang_{items[i + 1][0]}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "target_lang" not in context.user_data:
        context.user_data["target_lang"] = "ml"

    current_code = context.user_data["target_lang"]
    current_name = LANGUAGES.get(current_code, "🇮🇳 Malayalam")

    welcome_text = (
        "🌐 **Universal Language Translator**\n\n"
        f"🎯 **Active Target Language:** {current_name}\n\n"
        "👇 **Tap a language below to set your translation output:**"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )

async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang_code = query.data.replace("setlang_", "")
    context.user_data["target_lang"] = lang_code
    lang_name = LANGUAGES.get(lang_code, lang_code)

    await query.edit_message_text(
        f"✅ **Translation language set to:** {lang_name}\n\n"
        "💬 Now send any word or sentence in **any language** to translate it!",
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return

    target = context.user_data.get("target_lang", "ml")

    try:
        translated = GoogleTranslator(source="auto", target=target).translate(user_text)
        target_name = LANGUAGES.get(target, target)
        response = f"🔤 **[{target_name}]**\n\n{translated}"
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Translation error: {e}")
        await update.message.reply_text("❌ Translation failed. Please try again.")

async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    # Starts port binding for Render health check
    await start_web_server()

    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(language_selected, pattern="^setlang_"))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

    async with bot_app:
        await bot_app.start()
        await bot_app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
