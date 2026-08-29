import os
import io
import logging
import asyncio
import urllib.parse
import requests
from aiohttp import web
from gtts import gTTS
from deep_translator import GoogleTranslator, MyMemoryTranslator

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8979035511:AAFKhUJy2mVg52MDcYMshefeNml_EJd6DUQ")

# All Languages (Extended with Tajik & Hebrew/Israel)
LANGUAGES = {
    "en": "🇬🇧 English",
    "ml": "🇮🇳 Malayalam",
    "ta": "🇮🇳 Tamil",
    "te": "🇮🇳 Telugu",
    "kn": "🇮🇳 Kannada",
    "bn": "🇮🇳 Bengali",
    "hi": "🇮🇳 Hindi",
    "ur": "🇵🇰 Urdu",
    "he": "🇮🇱 Hebrew (Israel)",
    "tg": "🇹🇯 Tajik (Tajikistan)",
    "my": "🇲🇲 Burmese",
    "vi": "🇻🇳 Vietnamese",
    "es": "🇲🇽 Spanish (Mexican)",
    "de": "🇩🇪 German",
    "ru": "🇷🇺 Russian",
    "fr": "🇫🇷 French",
    "it": "🇮🇹 Italian",
    "pt": "🇧🇷 Portuguese",
    "no": "🇳🇴 Norwegian",
    "sv": "🇸🇪 Swedish",
    "pl": "🇵🇱 Polish",
    "ar": "🇪🇬 Arabic",
    "fa": "🇮🇷 Persian",
    "tr": "🇹🇷 Turkish",
    "zh-CN": "🇨🇳 Chinese",
    "ja": "🇯🇵 Japanese",
    "ko": "🇰🇷 Korean",
    "id": "🇮🇩 Indonesian",
    "uk": "🇺🇦 Ukrainian",
    "uz": "🇺🇿 Uzbek",
    "kk": "🇰🇿 Kazakh",
    "az": "🇦🇿 Azerbaijani",
}

# gTTS Supported Language Codes
TTS_MAP = {
    "en": "en",
    "ml": "ml",
    "ta": "ta",
    "te": "te",
    "kn": "kn",
    "bn": "bn",
    "hi": "hi",
    "ur": "ur",
    "he": "iw",  # Hebrew gTTS code
    "my": "my",
    "vi": "vi",
    "es": "es",
    "de": "de",
    "ru": "ru",
    "fr": "fr",
    "it": "it",
    "pt": "pt",
    "no": "no",
    "sv": "sv",
    "pl": "pl",
    "ar": "ar",
    "tr": "tr",
    "zh-CN": "zh-CN",
    "ja": "ja",
    "ko": "ko",
    "id": "id",
    "uk": "uk",
}

def init_user_data(context: ContextTypes.DEFAULT_TYPE):
    if "native_lang" not in context.user_data:
        context.user_data["native_lang"] = "ml"
    if "target_lang" not in context.user_data:
        context.user_data["target_lang"] = "de"
    if "mode" not in context.user_data:
        context.user_data["mode"] = "Translation"
    if "voice_enabled" not in context.user_data:
        context.user_data["voice_enabled"] = True

def get_settings_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    native_code = context.user_data.get("native_lang", "ml")
    target_code = context.user_data.get("target_lang", "de")
    mode = context.user_data.get("mode", "Translation")
    voice = "ON 🔊" if context.user_data.get("voice_enabled", True) else "OFF 🔇"

    return (
        "⚙️ **Bot Settings**\n\n"
        f"🌐 **My Language:** {LANGUAGES.get(native_code, 'Malayalam')}\n"
        f"📚 **Target Language:** {LANGUAGES.get(target_code, 'German')}\n"
        f"🔄 **Mode:** {mode} Mode\n"
        f"🔊 **Voice Audio:** {voice}\n\n"
        "👇 *Tap a button below to customize:*"
    )

def get_settings_keyboard(context: ContextTypes.DEFAULT_TYPE):
    voice_status = "🔊 Voice: ON" if context.user_data.get("voice_enabled", True) else "🔇 Voice: OFF"
    current_mode = context.user_data.get("mode", "Translation")
    mode_switch = "🔄 Switch to Learning Mode" if current_mode == "Translation" else "🔄 Switch to Translation Mode"

    keyboard = [
        [InlineKeyboardButton("🌐 Change My Language", callback_data="page_native_lang")],
        [InlineKeyboardButton("📚 Change Target Language", callback_data="page_target_lang")],
        [InlineKeyboardButton(mode_switch, callback_data="toggle_mode")],
        [InlineKeyboardButton(voice_status, callback_data="toggle_voice")],
        [InlineKeyboardButton("⭐️ Buy VIP Access (Telegram Stars)", callback_data="buy_stars_btn")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_picker_keyboard(action_type: str):
    keyboard = []
    items = list(LANGUAGES.items())
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"{action_type}_{items[i][0]}")]
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(items[i + 1][1], callback_data=f"{action_type}_{items[i + 1][0]}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")])
    return InlineKeyboardMarkup(keyboard)

def robust_translate(text: str, target: str, source: str = "auto") -> str:
    # 1. Direct Google API
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source}&tl={target}&dt=t&q={urllib.parse.quote(text)}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0]:
                return "".join([part[0] for part in data[0] if part[0]]).strip()
    except Exception as e:
        logging.warning(f"Direct Google API error: {e}")

    # 2. deep-translator GoogleTranslator fallback
    try:
        res = GoogleTranslator(source="auto", target=target).translate(text)
        if res and "Error 500" not in res and "<html>" not in res.lower():
            return res.strip()
    except Exception as e:
        logging.warning(f"GoogleTranslator fallback error: {e}")

    # 3. MyMemory fallback
    try:
        src = source if source != "auto" else "en"
        res = MyMemoryTranslator(source=src, target=target).translate(text)
        if res and "MYMEMORY WARNING" not in res:
            return res.strip()
    except Exception as e:
        logging.warning(f"MyMemory fallback error: {e}")

    return text

# Telegram Stars Payment Handlers
async def send_stars_invoice(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    prices = [LabeledPrice("⭐️ VIP Lifetime Access", 25)]
    await context.bot.send_invoice(
        chat_id=chat_id,
        title="⭐️ VIP Lifetime Membership",
        description="Unlock priority fast translation & lifetime VIP access!",
        payload="vip_stars_payment",
        currency="XTR",
        prices=prices,
        provider_token=""
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(context, update.effective_chat.id)

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload == "vip_stars_payment":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Payment validation failed.")

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 **Thank you!** Your VIP Access is now active. ⭐️", parse_mode="Markdown")

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_user_data(context)
    welcome = (
        "👋 **Welcome to TranslateMate!**\n\n"
        "💬 Send any word or sentence to translate instantly.\n"
        "⚙️ Use `/settings` to change target language or toggle voice audio.\n"
        "⭐️ Use `/buy` to support with Telegram Stars!"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")
    await update.message.reply_text(
        get_settings_text(context),
        reply_markup=get_settings_keyboard(context),
        parse_mode="Markdown"
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_user_data(context)
    await update.message.reply_text(
        get_settings_text(context),
        reply_markup=get_settings_keyboard(context),
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_user_data(context)
    target = context.user_data["target_lang"]
    mode = context.user_data["mode"]
    voice = "ON" if context.user_data["voice_enabled"] else "OFF"
    await update.message.reply_text(
        f"🟢 **Status: RUNNING (ON)**\n\n"
        f"📚 Target: {LANGUAGES.get(target, target)}\n"
        f"🔄 Mode: {mode}\n"
        f"🔊 Voice: {voice}",
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    init_user_data(context)
    data = query.data

    if data == "buy_stars_btn":
        await send_stars_invoice(context, query.message.chat_id)
    elif data == "back_to_settings":
        await query.edit_message_text(
            get_settings_text(context),
            reply_markup=get_settings_keyboard(context),
            parse_mode="Markdown"
        )
    elif data == "page_native_lang":
        await query.edit_message_text(
            "🌐 **Choose Your Native Language:**",
            reply_markup=get_language_picker_keyboard("setnative"),
            parse_mode="Markdown"
        )
    elif data == "page_target_lang":
        await query.edit_message_text(
            "📚 **Choose Your Target Language:**",
            reply_markup=get_language_picker_keyboard("settarget"),
            parse_mode="Markdown"
        )
    elif data.startswith("setnative_"):
        context.user_data["native_lang"] = data.replace("setnative_", "")
        await query.edit_message_text(
            get_settings_text(context),
            reply_markup=get_settings_keyboard(context),
            parse_mode="Markdown"
        )
    elif data.startswith("settarget_"):
        context.user_data["target_lang"] = data.replace("settarget_", "")
        await query.edit_message_text(
            get_settings_text(context),
            reply_markup=get_settings_keyboard(context),
            parse_mode="Markdown"
        )
    elif data == "toggle_mode":
        current = context.user_data.get("mode", "Translation")
        context.user_data["mode"] = "Learning" if current == "Translation" else "Translation"
        await query.edit_message_text(
            get_settings_text(context),
            reply_markup=get_settings_keyboard(context),
            parse_mode="Markdown"
        )
    elif data == "toggle_voice":
        context.user_data["voice_enabled"] = not context.user_data.get("voice_enabled", True)
        await query.edit_message_text(
            get_settings_text(context),
            reply_markup=get_settings_keyboard(context),
            parse_mode="Markdown"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    init_user_data(context)
    user_text = update.message.text
    native_lang = context.user_data["native_lang"]
    target_lang = context.user_data["target_lang"]
    mode = context.user_data["mode"]
    voice_enabled = context.user_data["voice_enabled"]

    target_name = LANGUAGES.get(target_lang, "German")

    await update.message.chat.send_action("typing")

    translated = robust_translate(user_text, target=target_lang, source=native_lang)

    if mode == "Learning":
        reply_body = f"🔤 **[{target_name}]**\n\n{translated}\n\n💡 *Learning Tip:* Listen to pronunciation & practice aloud!"
    else:
        reply_body = f"🔤 **[{target_name}]**\n\n{translated}"

    await update.message.reply_text(reply_body, parse_mode="Markdown")

    # Generate Voice Audio (Hebrew supported via 'iw', safe fallback for others)
    if voice_enabled and target_lang in TTS_MAP and "Error" not in translated:
        try:
            await update.message.chat.send_action("record_voice")
            fp = io.BytesIO()
            fp.name = "audio.mp3"
            tts = gTTS(text=translated, lang=TTS_MAP[target_lang])
            tts.write_to_fp(fp)
            fp.seek(0)
            await update.message.reply_voice(voice=fp)
        except Exception as e:
            logging.warning(f"Voice generation skipped: {e}")

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
    await start_web_server()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("buy", buy_command))

    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("🟢 Bot is running!")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
