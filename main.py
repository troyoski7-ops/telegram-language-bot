import os
import json
import tempfile
from datetime import datetime
from google import genai
from gTTS import gTTS
import gtts.lang
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

# --- PASTE YOUR 2 KEYS HERE ---
GEMINI_API_KEY = AQ.Ab8RN6Lyoi7IFidPrrT9AaBKhBIJu9cxasqQjpLlOQqMpXMXtg
TELEGRAM_BOT_TOKEN =8979035511:AAFKhUJy2mVg52MDcYMshefeNml_EJd6DUQ

DAILY_FREE_MESSAGES = 10
VIP_PRICE_STARS = 50

client = genai.Client(api_key=GEMINI_API_KEY)
ALL_TTS_LANGS = gtts.lang.tts_langs()

GLOBAL_LANGUAGES = [
    ("Russian", "🇷🇺"), ("German", "🇩🇪"), ("French", "🇫🇷"),
    ("Spanish", "🇪🇸"), ("Italian", "🇮🇹"), ("Portuguese", "🇧🇷"),
    ("Mandarin Chinese", "🇨🇳"), ("Japanese", "🇯🇵"), ("Korean", "🇰🇷"),
    ("Arabic", "🇪🇬"), ("Turkish", "🇹🇷"), ("Persian (Farsi)", "🇮🇷"),
    ("Ukrainian", "🇺🇦"), ("Uzbek", "🇺🇿"), ("Kazakh", "🇰🇿"),
    ("Indonesian", "🇮🇩"), ("Azerbaijani", "🇦🇿"),
    ("Malayalam", "🇮🇳"), ("Hindi", "🇮🇳"), ("English", "🇬🇧"),
    ("Tamil", "🇮🇳"), ("Telugu", "🇮🇳"), ("Kannada", "🇮🇳"),
    ("Bengali", "🇮🇳"), ("Marathi", "🇮🇳"), ("Gujarati", "🇮🇳"),
    ("Punjabi", "🇮🇳"), ("Odia", "🇮🇳"), ("Assamese", "🇮🇳"),
    ("Urdu", "🇵🇰")
]

USERS_DB = {}

def get_user_record(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in USERS_DB:
        USERS_DB[user_id] = {
            "native": "Malayalam",
            "target": "German",
            "is_vip": False,
            "usage_date": today,
            "messages_today": 0
        }
    if USERS_DB[user_id]["usage_date"] != today:
        USERS_DB[user_id]["usage_date"] = today
        USERS_DB[user_id]["messages_today"] = 0
    return USERS_DB[user_id]

def build_lang_menu(mode, page=0, per_page=6):
    total = len(GLOBAL_LANGUAGES)
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total)
    batch = GLOBAL_LANGUAGES[start_idx:end_idx]

    keyboard = []
    for i in range(0, len(batch), 2):
        row = [InlineKeyboardButton(f"{flag} {lang}", callback_data=f"sel_{mode}_{lang}") for lang, flag in batch[i:i+2]]
        keyboard.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{mode}_{page-1}"))
    if end_idx < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{mode}_{page+1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("🔙 Back to Settings", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user_record(user_id)
    vip_badge = "👑 VIP Member" if user["is_vip"] else f"🆓 Free ({user['messages_today']}/{DAILY_FREE_MESSAGES} daily used)"

    keyboard = [
        [InlineKeyboardButton(f"🗣️ Native: {user['native']}", callback_data="open_native_0")],
        [InlineKeyboardButton(f"🎯 Learn: {user['target']}", callback_data="open_target_0")],
        [InlineKeyboardButton("⭐ Upgrade to Unlimited VIP", callback_data="buy_vip")],
        [InlineKeyboardButton("✅ Start Practicing", callback_data="close_menu")]
    ]

    welcome = (
        f"👋 **Universal AI Language Tutor**\n\n"
        f"• **Status:** {vip_badge}\n"
        f"• **Native Language:** {user['native']}\n"
        f"• **Learning Language:** {user['target']}\n\n"
        f"Choose languages below or send a message / voice note to begin!"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = [LabeledPrice(label="Lifetime VIP Unlimited Pass", amount=VIP_PRICE_STARS)]
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="🌟 Unlimited VIP Language Access",
        description="Unlock 24/7 unlimited speaking practice, voice pronunciation, and corrections!",
        payload="vip_subscription_payload",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="vip-upgrade"
    )

async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_record(update.effective_user.id)
    user["is_vip"] = True
    await update.message.reply_text("🎉 **Payment Received! You are now a Lifetime VIP Member.**", parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = get_user_record(query.from_user.id)

    if data == "main_menu":
        await start(update, context)
    elif data == "buy_vip":
        await buy_vip(update, context)
    elif data == "close_menu":
        await query.edit_message_text(
            f"🚀 **All Set!**\n• Practicing: **{user['target']}**\n• Translations: **{user['native']}**\n\nSend a text or voice note now!", 
            parse_mode="Markdown"
        )
    elif data.startswith("open_native_"):
        page = int(data.split("_")[2])
        await query.edit_message_text("👇 **Select your Native Language:**", reply_markup=build_lang_menu("native", page), parse_mode="Markdown")
    elif data.startswith("open_target_"):
        page = int(data.split("_")[2])
        await query.edit_message_text("👇 **Select Target Language to Learn:**", reply_markup=build_lang_menu("target", page), parse_mode="Markdown")
    elif data.startswith("page_"):
        _, mode, page_num = data.split("_")
        await query.edit_message_text(f"👇 **Select {mode.upper()} Language:**", reply_markup=build_lang_menu(mode, int(page_num)), parse_mode="Markdown")
    elif data.startswith("sel_"):
        _, mode, lang = data.split("_")
        user[mode] = lang
        await start(update, context)

def generate_ai_response(user_content, native_lang, target_lang):
    system_prompt = f"""
    You are an expert conversational language coach.
    User Native Language: {native_lang}
    User Target Language: {target_lang}

    1. Respond naturally in {target_lang}.
    2. Give the exact translation/meaning in {native_lang}.
    3. If the user spoke or typed in {target_lang} with errors, give a helpful correction note in {native_lang}.
    4. Provide the correct 2-letter ISO 639-1 code for {target_lang} for text-to-speech.
    5. Provide appropriate emoji flags.

    Output strictly valid JSON:
    {{
        "target_reply": "Reply in {target_lang}",
        "native_meaning": "Translation in {native_lang}",
        "correction_tip": "Grammar/pronunciation tip or null",
        "tts_lang_code": "2-letter ISO code",
        "target_flag": "flag",
        "native_flag": "flag"
    }}
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_content,
        config={"system_instruction": system_prompt, "response_mime_type": "application/json"}
    )
    try:
        return json.loads(response.text)
    except Exception:
        return {"target_reply": response.text, "native_meaning": "", "correction_tip": None, "tts_lang_code": "en", "target_flag": "🌐", "native_flag": "🌐"}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_record(update.effective_user.id)

    if not user["is_vip"] and user["messages_today"] >= DAILY_FREE_MESSAGES:
        keyboard = [[InlineKeyboardButton(f"⭐ Unlock VIP ({VIP_PRICE_STARS} Stars)", callback_data="buy_vip")]]
        await update.message.reply_text("🔒 **Daily Limit Reached!** Upgrade to VIP for unlimited practice.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    user["messages_today"] += 1
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if update.message.voice:
        voice_file = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_voice:
            await voice_file.download_to_drive(custom_path=temp_voice.name)
            with open(temp_voice.name, "rb") as f:
                audio_bytes = f.read()
        user_content = [
            genai.types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
            f"User audio. Native: {user['native']}, Learning: {user['target']}."
        ]
    else:
        user_content = update.message.text

    ai_data = generate_ai_response(user_content, user["native"], user["target"])
    target_reply = ai_data.get("target_reply", "")
    native_meaning = ai_data.get("native_meaning", "")
    correction = ai_data.get("correction_tip")
    tts_code = ai_data.get("tts_lang_code", "en")
    target_flag = ai_data.get("target_flag", "🌐")
    native_flag = ai_data.get("native_flag", "🌐")

    reply_text = f"{target_flag} **{target_reply}**\n{native_flag} *Meaning:* {native_meaning}"
    if correction:
        reply_text += f"\n\n💡 *Tip:* {correction}"

    if not user["is_vip"]:
        reply_text += f"\n\n_(Free tier: {DAILY_FREE_MESSAGES - user['messages_today']} messages left today)_"

    await update.message.reply_text(reply_text, parse_mode="Markdown")

    if target_reply:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
        selected_code = tts_code if tts_code in ALL_TTS_LANGS else "en"
        try:
            tts = gTTS(text=target_reply, lang=selected_code, slow=False)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
                tts.save(temp_audio.name)
                with open(temp_audio.name, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)
        except Exception:
            pass

def main():
    print("🚀 Starting Bot Server with All Global & Indian Languages...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "languages", "vip"], start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
