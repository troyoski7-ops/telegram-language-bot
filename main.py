import os
import io
import logging
import asyncio
import urllib.parse
import datetime
import requests
from aiohttp import web
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
from deep_translator import GoogleTranslator, MyMemoryTranslator

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

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

BOT_TOKEN = os.getenv("BOT_TOKEN", "8979035511:AAFKhUJy2mVg52MDcYMshefeNml_EJd6DUQ")

# Configuration
AUTO_LIMIT_USER_THRESHOLD = 500
DAILY_FREE_LIMIT = 20
VIP_DURATION_DAYS = 30

REGISTERED_USERS = set()

# Universal Language Registry
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
    "es": "🇲🇽 Spanish",
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
    "uz": "UZ Uzbek",
    "kk": "🇰🇿 Kazakh",
    "az": "🇦🇿 Azerbaijani",
}

SR_MAP = {
    "en": "en-US", "ml": "ml-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN",
    "bn": "bn-IN", "hi": "hi-IN", "ur": "ur-PK", "he": "he-IL", "vi": "vi-VN",
    "es": "es-ES", "de": "de-DE", "ru": "ru-RU", "fr": "fr-FR", "it": "it-IT",
    "pt": "pt-PT", "no": "no-NO", "sv": "sv-SE", "pl": "pl-PL", "ar": "ar-SA",
    "fa": "fa-IR", "tr": "tr-TR", "zh-CN": "zh-CN", "ja": "ja-JP", "ko": "ko-KR",
    "id": "id-ID", "uk": "uk-UA"
}

# Supported TTS Language mapping
TTS_MAP = {
    "en": "en", "ml": "ml", "ta": "ta", "te": "te", "kn": "kn",
    "bn": "bn", "hi": "hi", "ur": "ur", "he": "iw", "my": "my",
    "vi": "vi", "es": "es", "de": "de", "ru": "ru", "fr": "fr",
    "it": "it", "pt": "pt", "no": "no", "sv": "sv", "pl": "pl",
    "ar": "ar", "tr": "tr", "zh-CN": "zh-CN", "ja": "ja", "ko": "ko",
    "id": "id", "uk": "uk", "fa": "fa"
}

def is_user_vip(context: ContextTypes.DEFAULT_TYPE) -> bool:
    expiry_str = context.user_data.get("vip_expiry")
    if not expiry_str:
        return False
    try:
        expiry_date = datetime.date.fromisoformat(expiry_str)
        return datetime.date.today() <= expiry_date
    except Exception:
        return False

def init_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    REGISTERED_USERS.add(user_id)
    today = datetime.date.today().isoformat()
    if "native_lang" not in context.user_data:
        context.user_data["native_lang"] = "ml"
    if "target_lang" not in context.user_data:
        context.user_data["target_lang"] = "de"
    if "mode" not in context.user_data:
        context.user_data["mode"] = "Translation"
    if "voice_enabled" not in context.user_data:
        context.user_data["voice_enabled"] = True
    if "usage_date" not in context.user_data or context.user_data["usage_date"] != today:
        context.user_data["usage_date"] = today
        context.user_data["daily_count"] = 0

def is_limit_active() -> bool:
    return len(REGISTERED_USERS) >= AUTO_LIMIT_USER_THRESHOLD

def get_settings_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    native_code = context.user_data.get("native_lang", "ml")
    target_code = context.user_data.get("target_lang", "de")
    mode = context.user_data.get("mode", "Translation")
    voice = "ON 🔊" if context.user_data.get("voice_enabled", True) else "OFF 🔇"
    
    vip_active = is_user_vip(context)
    used = context.user_data.get("daily_count", 0)
    
    if vip_active:
        expiry = context.user_data.get("vip_expiry", "")
        limit_text = f"⭐️ **VIP Member (1 Month Plan):** Active until `{expiry}`"
    elif not is_limit_active():
        limit_text = "🎁 **Status:** Early Access (100% Free & Unlimited)"
    else:
        limit_text = f"📊 **Status:** {used}/{DAILY_FREE_LIMIT} Free Translations Used Today"

    return (
        "⚙️ **Bot Settings**\n\n"
        f"🌐 **My Language (Voice/Input):** {LANGUAGES.get(native_code, 'Malayalam')}\n"
        f"📚 **Target Language (Output):** {LANGUAGES.get(target_code, 'German')}\n"
        f"🔄 **Mode:** {mode} Mode\n"
        f"🔊 **Voice Audio:** {voice}\n"
        f"{limit_text}\n\n"
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
    
    if not is_user_vip(context):
        keyboard.append([InlineKeyboardButton("⭐️ Get 1 Month VIP (25 Stars)", callback_data="buy_stars_btn")])
        
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

# ==================== ROBUST MULTI-ENGINE TRANSLATOR ====================

def query_google_dict_api(text: str, target: str, source: str = "auto") -> str:
    url = "https://clients5.google.com/translate_a/t"
    params = {
        "client": "dict-chrome-ex",
        "sl": source,
        "tl": target,
        "q": text,
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            res = r.json()
            if isinstance(res, list) and len(res) > 0:
                if isinstance(res[0], list):
                    return "".join([x for x in res[0] if isinstance(x, str)]).strip()
                elif isinstance(res[0], str):
                    return res[0].strip()
    except Exception:
        pass
    return ""

def translate_universal(text: str, target: str, source: str = "auto") -> str:
    # 1. Primary Chrome-Ex Google API
    out = query_google_dict_api(text, target, source)
    if out and out.lower() != text.lower():
        return out

    # 2. Deep-Translator Google
    try:
        res = GoogleTranslator(source="auto", target=target).translate(text)
        if res and "Error 500" not in res and res.strip().lower() != text.lower():
            return res.strip()
    except Exception:
        pass

    # 3. Two-Step Bridge via English
    if target != "en":
        try:
            eng = query_google_dict_api(text, "en", source) or GoogleTranslator(source="auto", target="en").translate(text)
            if eng and eng.lower() != text.lower():
                final_res = query_google_dict_api(eng, target, "en") or GoogleTranslator(source="en", target=target).translate(eng)
                if final_res and final_res.strip().lower() != text.lower():
                    return final_res.strip()
        except Exception:
            pass

    # 4. MyMemory Fallback
    try:
        src = source if source != "auto" else "en"
        res = MyMemoryTranslator(source=src, target=target).translate(text)
        if res and "MYMEMORY WARNING" not in res:
            return res.strip()
    except Exception:
        pass

    return text

# ==================== VOICE / AUDIO ENGINE ====================

def generate_voice_audio(text: str, lang_code: str) -> io.BytesIO:
    mapped_code = TTS_MAP.get(lang_code, lang_code)
    
    # 1. Google Web TTS Direct Stream
    try:
        tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={mapped_code}&client=tw-ob&q={urllib.parse.quote(text)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(tts_url, headers=headers, timeout=6)
        if r.status_code == 200 and len(r.content) > 100:
            fp = io.BytesIO(r.content)
            fp.name = "audio.mp3"
            fp.seek(0)
            return fp
    except Exception:
        pass

    # 2. gTTS Standard Engine
    try:
        fp = io.BytesIO()
        fp.name = "audio.mp3"
        tts = gTTS(text=text, lang=mapped_code)
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception:
        pass

    return None

def recognize_audio_bytes(ogg_bytes: bytes, lang_code: str) -> str:
    try:
        audio_seg = AudioSegment.from_file(io.BytesIO(ogg_bytes), format="ogg")
        wav_io = io.BytesIO()
        audio_seg.export(wav_io, format="wav")
        wav_io.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)

        sr_lang = SR_MAP.get(lang_code, "auto")
        if sr_lang != "auto":
            return recognizer.recognize_google(audio_data, language=sr_lang)
        return recognizer.recognize_google(audio_data)
    except Exception as e:
        logging.warning(f"Voice recognition error: {e}")
        return ""

# ==================== TELEGRAM STARS PAYMENT ====================

async def send_stars_invoice(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    prices = [LabeledPrice("⭐️ 1 Month VIP Access", 25)]
    await context.bot.send_invoice(
        chat_id=chat_id,
        title="⭐️ 1 Month VIP Membership",
        description="Unlock 30 days of unlimited translations and priority features!",
        payload="vip_1month_stars_payment",
        currency="XTR",
        prices=prices,
        provider_token=""
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(context, update.effective_chat.id)

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload == "vip_1month_stars_payment":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Payment validation failed.")

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_data(context, user_id)
    expiry_date = datetime.date.today() + datetime.timedelta(days=VIP_DURATION_DAYS)
    context.user_data["vip_expiry"] = expiry_date.isoformat()
    await update.message.reply_text(
        f"🎉 **Payment Received!**\n\n⭐️ Your **1 Month VIP Access** is now active until **{expiry_date.strftime('%d %B %Y')}**!\n🚀 Enjoy unlimited translations!",
        parse_mode="Markdown"
    )

# ==================== COMMAND & CALLBACK HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_data(context, user_id)
    welcome = (
        "👋 **Welcome to TranslateMate!**\n\n"
        "💬 **Type or Speak 🎙️** in any language to translate instantly.\n"
        "⚙️ Use `/settings` to change languages or toggle voice audio.\n"
        "⭐️ Use `/buy` for 1 Month VIP Access (25 Stars)!"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")
    await update.message.reply_text(
        get_settings_text(context),
        reply_markup=get_settings_keyboard(context),
        parse_mode="Markdown"
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_data(context, user_id)
    await update.message.reply_text(
        get_settings_text(context),
        reply_markup=get_settings_keyboard(context),
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_data(context, user_id)
    target = context.user_data["target_lang"]
    mode = context.user_data["mode"]
    voice = "ON" if context.user_data["voice_enabled"] else "OFF"
    total_users = len(REGISTERED_USERS)
    vip_status = f"Active ⭐️ (Exp: {context.user_data.get('vip_expiry')})" if is_user_vip(context) else "Regular User"
    limit_status = f"Active ({DAILY_FREE_LIMIT}/day)" if is_limit_active() else "Disabled (Free Phase)"
    
    await update.message.reply_text(
        f"🟢 **Status: RUNNING (ON)**\n\n"
        f"👥 **Total Active Users:** {total_users}\n"
        f"⚡ **Daily Limit State:** {limit_status}\n"
        f"👑 **VIP Status:** {vip_status}\n"
        f"📚 **Target:** {LANGUAGES.get(target, target)}\n"
        f"🔄 **Mode:** {mode}\n"
        f"🔊 **Voice:** {voice}",
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    init_user_data(context, user_id)
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

# ==================== MESSAGE PIPELINE ====================

async def process_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, input_text: str, is_from_voice: bool = False):
    user_id = update.effective_user.id
    init_user_data(context, user_id)
    vip_active = is_user_vip(context)
    daily_count = context.user_data.get("daily_count", 0)

    if is_limit_active() and not vip_active and daily_count >= DAILY_FREE_LIMIT:
        limit_reached_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐️ Get 1 Month VIP (25 Stars)", callback_data="buy_stars_btn")]
        ])
        await update.message.reply_text(
            f"⚠️ **Daily Free Limit Reached!** ({DAILY_FREE_LIMIT}/{DAILY_FREE_LIMIT})\n\n"
            "You have used all 20 free translations for today.\n"
            "Get **1 Month Unlimited VIP Access** for just 25 Telegram Stars! ⭐️",
            reply_markup=limit_reached_keyboard,
            parse_mode="Markdown"
        )
        return

    native_lang = context.user_data["native_lang"]
    target_lang = context.user_data["target_lang"]
    mode = context.user_data["mode"]
    voice_enabled = context.user_data["voice_enabled"]

    target_name = LANGUAGES.get(target_lang, target_lang)

    await update.message.chat.send_action("typing")

    translated = translate_universal(input_text, target=target_lang, source=native_lang)

    counter_footer = ""
    if is_limit_active():
        if not vip_active:
            context.user_data["daily_count"] += 1
            counter_footer = f"\n\n📊 *({context.user_data['daily_count']}/{DAILY_FREE_LIMIT} daily free used)*"
        else:
            counter_footer = "\n\n⭐️ *VIP 1-Month Member*"

    origin_note = f"🎙️ *You said:* \"{input_text}\"\n\n" if is_from_voice else ""

    if mode == "Learning":
        reply_body = f"{origin_note}🔤 **[{target_name}]**\n\n{translated}\n\n💡 *Learning Tip:* Practice pronunciation aloud!{counter_footer}"
    else:
        reply_body = f"{origin_note}🔤 **[{target_name}]**\n\n{translated}{counter_footer}"

    await update.message.reply_text(reply_body, parse_mode="Markdown")

    # Generate Voice Audio
    if voice_enabled:
        try:
            await update.message.chat.send_action("record_voice")
            fp = await asyncio.to_thread(generate_voice_audio, translated, target_lang)
            if fp:
                await update.message.reply_voice(voice=fp)
        except Exception as e:
            logging.warning(f"Voice generation skipped: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    await process_and_reply(update, context, update.message.text.strip(), is_from_voice=False)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return

    user_id = update.effective_user.id
    init_user_data(context, user_id)
    native_lang = context.user_data.get("native_lang", "ml")

    await update.message.chat.send_action("record_voice")

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        voice_bytes = await voice_file.download_as_bytearray()

        recognized_text = await asyncio.to_thread(recognize_audio_bytes, bytes(voice_bytes), native_lang)

        if not recognized_text:
            await update.message.reply_text(
                "⚠️ *Could not recognize your voice message clearly.*\nPlease try speaking again or send text.",
                parse_mode="Markdown"
            )
            return

        await process_and_reply(update, context, recognized_text, is_from_voice=True)

    except Exception as e:
        logging.error(f"Voice processing error: {e}")
        await update.message.reply_text("⚠️ Failed to process audio. Please try again.")

# ==================== WEB SERVER & APP START ====================

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
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("🤖 Bot starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("🟢 Bot is running!")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
