import os
import io
import logging
import asyncio
from aiohttp import web
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)
from deep_translator import GoogleTranslator, MyMemoryTranslator

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

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
    keyboard.append([InlineKeyboardButton("⭐️ Buy VIP Access (Telegram Stars)", callback_data="buy_stars_btn")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "target_lang" not in context.user_data:
        context.user_data["target_lang"] = "ml"

    current_code = context.user_data["target_lang"]
    current_name = LANGUAGES.get(current_code, "🇮🇳 Malayalam")

    welcome_text = (
        "🌐 **Universal Language Translator & Voice Bot**\n\n"
        f"🎯 **Active Target Language:** {current_name}\n\n"
        "👇 **Tap a language below to change translation output:**\n"
        "⭐️ Type `/buy` to support with Telegram Stars!"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_language_keyboard(), parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Status: **RUNNING (ON)**\nTranslation and Voice engine ready.", parse_mode="Markdown")

async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang_code = query.data.replace("setlang_", "")
    context.user_data["target_lang"] = lang_code
    lang_name = LANGUAGES.get(lang_code, lang_code)

    await query.edit_message_text(
        f"✅ **Language set to:** {lang_name}\n\n"
        "💬 Send text in **any language**—I will translate and send voice audio!",
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )

def safe_translate(text: str, target: str) -> str:
    """Translates text with fallback engines to prevent Error 500."""
    try:
        res = GoogleTranslator(source="auto", target=target).translate(text)
        if res and "Error 500" not in res:
            return res
    except Exception:
        pass

    try:
        # Fallback to MyMemory if Google encounters rate-limits
        res = MyMemoryTranslator(source="auto", target=target).translate(text)
        if res:
            return res
    except Exception as e:
        logging.error(f"MyMemory fallback error: {e}")
    
    return ""

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return

    target = context.user_data.get("target_lang", "ml")
    target_name = LANGUAGES.get(target, target)

    translated = safe_translate(user_text, target)

    if not translated:
        await update.message.reply_text("⚠️ Translation server was busy. Please send the message again.")
        return

    # Send translated text
    await update.message.reply_text(f"🔤 **[{target_name}]**\n\n{translated}", parse_mode="Markdown")

    # Generate and send audio pronunciation
    try:
        # Standardize language code for gTTS
        tts_lang = "zh-CN" if target == "zh-CN" else target.split("-")[0]
        fp = io.BytesIO()
        tts = gTTS(text=translated, lang=tts_lang)
        tts.write_to_fp(fp)
        fp.seek(0)
        await update.message.reply_voice(voice=fp)
    except Exception as tts_err:
        logging.warning(f"Voice generation skipped for {target}: {tts_err}")

async def send_stars_invoice(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    prices = [LabeledPrice("VIP Access", 25)]
    await context.bot.send_invoice(
        chat_id=chat_id,
        title="⭐️ VIP Translator Access",
        description="Support the bot and get lifetime VIP translation access!",
        payload="vip_stars_payment",
        currency="XTR",
        prices=prices,
        provider_token=""
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(context, update.effective_chat.id)

async def stars_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_stars_invoice(context, query.message.chat_id)

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True) if query.invoice_payload == "vip_stars_payment" else await query.answer(ok=False, error_message="Error")

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 **Payment Received!** VIP access active. ⭐️", parse_mode="Markdown")

async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Please send text messages for translation.")

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

    await start_web_server()

    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("status", status))
    bot_app.add_handler(CommandHandler("buy", buy_command))
    bot_app.add_handler(CallbackQueryHandler(stars_button_click, pattern="^buy_stars_btn$"))
    bot_app.add_handler(CallbackQueryHandler(language_selected, pattern="^setlang_"))
    bot_app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    bot_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))
    bot_app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_non_text))

    async with bot_app:
        await bot_app.start()
        await bot_app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
