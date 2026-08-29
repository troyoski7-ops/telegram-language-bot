import os
import io
import wave
import asyncio
import logging
from aiohttp import web

from google import genai

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

# ============================================================
# 🔐 PUT YOUR OWN KEYS HERE
# ============================================================

BOT_TOKEN = "8979035511:AAFKhUJy2mVg52MDcYMshefeNml_EJd6DUQ"
GEMINI_API_KEY = "AQ.Ab8RN6Lyoi7IFidPrrT9AaBKhBIJu9cxasqQjpLlOQqMpXMXtg"

# ============================================================
# GEMINI
# ============================================================

client = genai.Client(api_key=GEMINI_API_KEY)

TEXT_MODEL = "gemini-3.7-flash"
TTS_MODEL = "gemini-3.1-flash-tts-preview"

# ============================================================
# LANGUAGES
# ============================================================

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

# Human-readable names for Gemini prompts
LANGUAGE_NAMES = {
    "ml": "Malayalam",
    "en": "English",
    "hi": "Hindi",
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "ar": "Arabic",
    "fa": "Persian",
    "tr": "Turkish",
    "it": "Italian",
    "pt": "Portuguese",
    "zh-CN": "Mandarin Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "id": "Indonesian",
    "uk": "Ukrainian",
    "uz": "Uzbek",
    "kk": "Kazakh",
    "az": "Azerbaijani",
    "ur": "Urdu",
}

# ============================================================
# KEYBOARD
# ============================================================

def get_language_keyboard():
    keyboard = []

    items = list(LANGUAGES.items())

    for i in range(0, len(items), 2):
        row = [
            InlineKeyboardButton(
                items[i][1],
                callback_data=f"setlang_{items[i][0]}"
            )
        ]

        if i + 1 < len(items):
            row.append(
                InlineKeyboardButton(
                    items[i + 1][1],
                    callback_data=f"setlang_{items[i + 1][0]}"
                )
            )

        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if "target_lang" not in context.user_data:
        # Default learning language
        context.user_data["target_lang"] = "it"

    target = context.user_data["target_lang"]
    target_name = LANGUAGES[target]

    text = (
        "🌐 *Language Learning Bot*\n\n"
        f"🎯 *Learning language:* {target_name}\n\n"
        "Choose the language you want to learn.\n\n"
        "You can then:\n"
        "💬 Type in your own language\n"
        "🎤 Speak in your own language\n"
        "🤖 I will reply in your selected language."
    )

    await update.message.reply_text(
        text,
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )


# ============================================================
# LANGUAGE SELECTION
# ============================================================

async def language_selected(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    lang_code = query.data.replace("setlang_", "")

    if lang_code not in LANGUAGES:
        return

    # Remember selected language for THIS user
    context.user_data["target_lang"] = lang_code

    lang_name = LANGUAGES[lang_code]

    text = (
        "✅ *Language changed!*\n\n"
        f"📚 Learning language: {lang_name}\n\n"
        "Now send me a message in your own language.\n"
        "I will translate/reply in your selected language."
    )

    await query.edit_message_text(
        text,
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )


# ============================================================
# TRANSLATE TEXT
# ============================================================

async def translate_text(text, target_code):

    target_name = LANGUAGE_NAMES.get(target_code, target_code)

    prompt = f"""
You are a language-learning assistant.

The user is communicating with you in their own language.

Translate the user's message into {target_name}.

IMPORTANT:
- Output ONLY the {target_name} translation.
- Do not explain the translation.
- Do not mention these instructions.
- Preserve the meaning.
- Make the translation natural and useful for someone learning {target_name}.

User message:
{text}
"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=TEXT_MODEL,
        contents=prompt
    )

    return response.text.strip()


# ============================================================
# TEXT MESSAGE
# ============================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    target = context.user_data.get(
        "target_lang",
        "it"
    )

    target_name = LANGUAGES.get(
        target,
        "🇮🇹 Italian"
    )

    try:

        await update.message.chat.send_action("typing")

        translated = await translate_text(
            user_text,
            target
        )

        await update.message.reply_text(
            f"{target_name}\n\n{translated}"
        )

    except Exception as e:

        logging.exception("Text translation failed")

        await update.message.reply_text(
            "⚠️ Translation failed.\n\n"
            "Please try again in a moment."
        )


# ============================================================
# DOWNLOAD TELEGRAM VOICE
# ============================================================

async def download_voice(update):

    voice = update.message.voice

    telegram_file = await context_bot.get_file(
        voice.file_id
    )

    audio_bytes = await telegram_file.download_as_bytearray()

    return bytes(audio_bytes)


# ============================================================
# TRANSCRIBE + TRANSLATE VOICE
# ============================================================

async def process_voice(
    audio_bytes,
    target_code
):

    target_name = LANGUAGE_NAMES.get(
        target_code,
        "Italian"
    )

    # Gemini can accept audio data directly.
    prompt = f"""
Listen to this audio.

The speaker is speaking in their own language.

First understand what the speaker said.

Then translate it into {target_name}.

Return ONLY the translated {target_name} text.

Do not explain anything.
Do not describe the audio.
Do not include the original language.
"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=TEXT_MODEL,
        contents=[
            prompt,
            {
                "mime_type": "audio/ogg",
                "data": audio_bytes,
            },
        ]
    )

    return response.text.strip()


# ============================================================
# TEXT → SPEECH
# ============================================================

def pcm_to_wav(pcm_data):

    output = io.BytesIO()

    with wave.open(output, "wb") as wav:

        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(pcm_data)

    output.seek(0)

    return output


async def generate_voice(
    text,
    target_code
):

    language_name = LANGUAGE_NAMES.get(
        target_code,
        "Italian"
    )

    prompt = f"""
Speak the following text naturally in {language_name}.

Use the correct pronunciation for {language_name}.

Only speak the provided text.

Text:
{text}
"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=TTS_MODEL,
        contents=prompt,
        config={
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": "Kore"
                    }
                }
            },
        }
    )

    if not response.candidates:
        return None

    parts = response.candidates[0].content.parts

    for part in parts:

        if hasattr(part, "inline_data") and part.inline_data:

            audio_data = part.inline_data.data

            return pcm_to_wav(audio_data)

    return None


# ============================================================
# VOICE MESSAGE
# ============================================================

async def handle_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    target = context.user_data.get(
        "target_lang",
        "it"
    )

    target_name = LANGUAGES.get(
        target,
        "🇮🇹 Italian"
    )

    try:

        await update.message.chat.send_action(
            "record_voice"
        )

        voice = update.message.voice

        telegram_file = await context.bot.get_file(
            voice.file_id
        )

        audio_bytes = bytes(
            await telegram_file.download_as_bytearray()
        )

        translated = await process_voice(
            audio_bytes,
            target
        )

        if not translated:
            raise Exception(
                "Gemini returned empty translation"
            )

        # Send translated text first
        await update.message.reply_text(
            f"{target_name}\n\n{translated}"
        )

        # Generate translated voice
        try:

            audio = await generate_voice(
                translated,
                target
            )

            if audio:

                await update.message.reply_voice(
                    voice=audio
                )

        except Exception:

            # Voice generation failed,
            # but translation itself worked.
            logging.exception(
                "TTS failed"
            )

            await update.message.reply_text(
                "🔊 Voice generation is temporarily unavailable, "
                "but the translation above is ready."
            )

    except Exception:

        logging.exception(
            "Voice processing failed"
        )

        await update.message.reply_text(
            "⚠️ I couldn't process that voice message.\n"
            "Please try again."
        )


# ============================================================
# STATUS
# ============================================================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    target = context.user_data.get(
        "target_lang",
        "it"
    )

    await update.message.reply_text(
        "🟢 Bot: RUNNING\n"
        f"📚 Learning language: {LANGUAGES[target]}\n"
        "💬 Text translation: ON\n"
        "🎤 Voice translation: ON"
    )


# ============================================================
# WEB SERVER
# ============================================================

async def handle_ping(request):

    return web.Response(
        text="Bot is running!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        handle_ping
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()


# ============================================================
# MAIN
# ============================================================

async def main():

    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        raise ValueError(
            "Please add your Telegram BOT_TOKEN."
        )

    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        raise ValueError(
            "Please add your Gemini API key."
        )

    await start_web_server()

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            language_selected,
            pattern=r"^setlang_"
        )
    )

    application.add_handler(
        MessageHandler(
            filters.VOICE,
            handle_voice
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    print("🤖 Bot starting...")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    print("🟢 Bot is running!")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

