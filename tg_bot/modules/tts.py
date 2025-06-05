from datetime import datetime
from gtts import gTTS
from telegram import Update, ChatAction
from telegram.ext import ContextTypes, CommandHandler
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler
import os

SUPPORTED_LANGS = ["en", "ml", "ta", "hi", "fr", "es"]  # Add more as needed

async def tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not context.args:
        await message.reply_text("Please provide text to convert. Usage: /tts [lang] <text>")
        return

    # Optional language support
    lang = "ml"  # default
    if context.args[0].lower() in SUPPORTED_LANGS:
        lang = context.args[0].lower()
        text = " ".join(context.args[1:])
    else:
        text = " ".join(context.args)

    if not text.strip():
        await message.reply_text("Text is empty. Please provide something to convert.")
        return

    try:
        await update.effective_chat.send_action(ChatAction.RECORD_VOICE)

        tts = gTTS(text=text, lang=lang)
        filename = f"{datetime.now().strftime('%d%m%y-%H%M%S')}.mp3"
        tts.save(filename)

        with open(filename, "rb") as speech:
            await message.reply_voice(speech, quote=False)

        os.remove(filename)
    except Exception as e:
        await message.reply_text(f"Failed to convert to speech. Try using English. Error: {e}")


__mod_name__ = "Text To Speech"

__help__ = """
🗣️ /tts <text> — Converts your text into speech (Malayalam default)
🗣️ /tts <lang_code> <text> — Set language manually. Example:
   - /tts en Hello there!
   - /tts ta வணக்கம்
   - /tts hi नमस्ते
Supported languages: en, ml, ta, hi, fr, es
"""

tts_handler = DisableAbleCommandHandler("tts", tts)
dispatcher.add_handler(tts_handler)
