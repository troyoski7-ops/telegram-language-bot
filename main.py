import os
import logging
import asyncio
from aiohttp import web
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
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Fetch secret token securely from Render Environment Variables
TOKEN = os.getenv("BOT_TOKEN")

# Supported Languages
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
    
    # Telegram Stars Upgrade button
    keyboard.append([InlineKeyboardButton("⭐️ Buy VIP Access (Telegram Stars)", callback_data="buy_stars_btn")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "target_lang" not in context.user_data:
        context.user_data["target_lang"] = "ml"

    current_code = context.user_data["target_lang"]
    current_name = LANGUAGES.get(current_code, "🇮🇳 Malayalam")

    welcome_text = (
        "🌐 **Universal Language Translator Bot**\n\n"
        f"🎯 **Active Target Language:** {current_name}\n\n"
        "👇 **Tap a language below to set your translation output:**\n"
        "⭐️ Type `/buy` to support or unlock VIP Access with Stars!"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Status: **RUNNING (ON)**\nBot is active and ready.", parse_mode="Markdown")

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

async def send_stars_invoice(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    title = "⭐️ VIP Translator Access"
    description = "Support the bot and get lifetime VIP translation access!"
    payload = "vip_stars_payment"
    currency = "XTR"  # Telegram Stars
    prices = [LabeledPrice("VIP Access", 25)]  # 25 Stars

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        currency=currency,
        prices=prices,
        provider_token=""  # Must be empty for Stars
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(context, update.effective_chat.id)

async def stars_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_stars_invoice(context, query.message.chat_id)

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload != "vip_stars_payment":
        await query.answer(ok=False, error_message="Payment error, please try again.")
    else:
        await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["is_vip"] = True
    await update.message.reply_text(
        "🎉 **Payment Received!**\n\n"
        "Thank you for supporting with Telegram Stars! Your VIP status is active. ⭐️",
        parse_mode="Markdown"
    )

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return

    target = context.user_data.get("target_lang", "ml")
    target_name = LANGUAGES.get(target, target)

    translated = None
    for attempt in range(2):
        try:
            translated = GoogleTranslator(source="auto", target=target).translate(user_text)
            if translated:
                break
        except Exception as e:
            logging.error(f"Attempt {attempt+1} error: {e}")
            await asyncio.sleep(0.5)

    if translated:
        response = f"🔤 **[{target_name}]**\n\n{translated}"
        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Translation server was busy. Please send the message again.")

async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Please send text messages only for translation.")

# Lightweight web server to keep Render service alive and prevent timeout
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
