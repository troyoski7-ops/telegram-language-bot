import os
import io
import logging
import asyncio
from aiohttp import web
from gtts import gTTS
from deep_translator import GoogleTranslator, MyMemoryTranslator

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8979035511:AAFKhUJy2mVg52MDcYMshefeNml_EJd6DUQ")

# Supported Languages
LANGUAGES = {
    "en": "🇬🇧 English",
    "ml": "🇮🇳 Malayalam",
    "hi": "🇮🇳 Hindi",
    "it": "🇮🇹 Italian",
    "de": "🇩🇪 German",
    "ru": "🇷🇺 Russian",
    "fr": "🇫🇷 French",
    "es": "🇪🇸 Spanish",
    "ar": "🇪🇬 Arabic",
    "fa": "🇮🇷 Persian",
    "tr": "🇹🇷 Turkish",
    "pt": "🇧🇷 Portuguese",
    "zh-CN": "🇨🇳 Chinese",
    "ja": "🇯🇵 Japanese",
    "ko": "🇰🇷 Korean",
    "id": "🇮🇩 Indonesian",
    "uk": "🇺🇦 Ukrainian",
    "uz": "🇺🇿 Uzbek",
    "kk": "🇰🇿 Kazakh",
    "az": "🇦🇿 Azerbaijani",
    "ur": "🇵🇰 Urdu",
}

# gTTS supported codes
TTS_MAP = {
    "en": "en", "ml": "ml", "hi": "hi", "it": "it", "de": "de",
    "ru": "ru", "fr": "fr", "es": "es", "ar": "ar", "tr": "tr",
    "pt": "pt", "zh-CN": "zh-CN", "ja": "ja", "ko": "ko",
    "id": "id", "uk": "uk", "ur": "ur",
}

def init_user_data(context: ContextTypes.DEFAULT_TYPE):
    if "native_lang" not in context.user_data:
        context.user_data["native_lang"] = "en"
    if "target_lang" not in context.user_data:
        context.user_data["target_lang"] = "it"
    if "mode" not in context.user_data:
        context.user_data["mode"] = "Translation"
    if "voice_enabled" not in context.user_data:
        context.user_data["voice_enabled"] = True

def get_settings_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    native_code = context.user_data.get("native_lang", "en")
    target_code = context.user_data.get("target_lang", "it")
    mode = context.user_data.get("mode", "Translation")
    voice = "ON 🔊" if context.user_data.get("voice_enabled", True) else "OFF 🔇"

    return (
        "⚙️ **Bot Settings**\n\n"
        f"🌐 **My Language:** {LANGUAGES.get(native_code, 'English')}\n"
        f"📚 **Target Language:** {LANGUAGES.get(target_code, 'Italian')}\n"
        f"🔄 **Mode:** {mode} Mode\n"
        f"🔊 **Voice:** {voice}\n\n"
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

def safe_translate(text: str, target: str) -> str:
    try:
        res = GoogleTranslator(source="auto", target=target).translate(text)
        if res:
            return res
    except Exception:
        pass
    try:
        res = MyMemoryTranslator(source="auto", target=target).translate(text)
        if res:
            return res
    except Exception as e:
        logging.error(f"Translation error: {e}")
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_user_data(context)
    welcome = (
        "👋 **Welcome to TranslateMate!**\n\n"
        "💬 Send me any text or voice note in any language, and I will translate it instantly!\n"
        "⚙️ Use `/settings` to change languages or voice audio options."
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

    if data == "back_to_settings":
        await query.edit_message_text(
            get_settings_text(context),
            reply_markup=get_settings_keyboard(context),
            parse_mode="Markdown"
        )
    elif data == "page_native_lang":
        await query.edit_message_text(
            "🌐 **Choose Your Native/Base Language:**",
            reply_markup=get_language_picker_keyboard("setnative"),
            parse_mode="Markdown"
        )
    elif data == "page_target_lang":
        await query.edit_message_text(
            "📚 **Choose Your Target/Learning Language:**",
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
    target_lang = context.user_data["target_lang"]
    mode = context.user_data["mode"]
    voice_enabled = context.user_data["voice_enabled"]

    target_name = LANGUAGES.get(target_lang, "Italian")

    await update.message.chat.send_action("typing")

    translated = safe_translate(user_text, target_lang)

    if mode == "Learning":
        reply_body = f"🔤 **[{target_name}]**\n\n{translated}\n\n💡 *Learning Tip:* Practice repeating the phrase out loud!"
    else:
        reply_body = f"🔤 **[{target_name}]**\n\n{translated}"

    await update.message.reply_text(reply_body, parse_mode="Markdown")

    if voice_enabled and target_lang in TTS_MAP:
        try:
            await update.message.chat.send_action("record_voice")
            fp = io.BytesIO()
            fp.name = "voice.mp3"
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
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("🟢 Bot is running!")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
