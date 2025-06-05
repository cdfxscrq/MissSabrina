from telegram import Update, ParseMode
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, CommandHandler
from googletrans import Translator
from emoji import UNICODE_EMOJI
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

def remove_emojis(text: str) -> str:
    for emoji in UNICODE_EMOJI:
        text = text.replace(emoji, '')
    return text

async def totranslate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not context.args:
        await msg.reply_text(
            "❗ Usage:\n`/tr ml` — Auto-detect source, translate to Malayalam\n"
            "`/tr en-ta` — Translate from English to Tamil\n\nYou can reply to a message or add the text inline.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        lang_code = context.args[0].lower()
        if "-" in lang_code:
            src_lang, dest_lang = lang_code.split("-", 1)
        else:
            src_lang, dest_lang = None, lang_code

        # Check if reply or inline text
        if msg.reply_to_message and msg.reply_to_message.text:
            text = msg.reply_to_message.text
        else:
            if len(context.args) < 2:
                await msg.reply_text("❗ Please include the text to translate.", parse_mode=ParseMode.MARKDOWN)
                return
            text = " ".join(context.args[1:])

        text = remove_emojis(text)

        await msg.chat.send_action(action=ChatAction.TYPING)
        translator = Translator()

        if src_lang:
            result = translator.translate(text, src=src_lang, dest=dest_lang)
            source_info = src_lang
        else:
            detected = translator.detect(text)
            result = translator.translate(text, dest=dest_lang)
            source_info = detected.lang

        await msg.reply_text(
            f"🌐 *Translated from* `{source_info}` *to* `{dest_lang}`:\n"
            f"`{result.text}`",
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await msg.reply_text(f"⚠️ Translation failed: `{e}`", parse_mode=ParseMode.MARKDOWN)


__help__ = """
🌐 /tr <lang> [text] — Translate text into target language.
🌐 /tr <src>-<target> [text] — Translate with both source and destination languages.

Examples:
- `/tr ml Hello` → Translates to Malayalam
- `/tr en-ta How are you?` → English to Tamil
- Or just reply to a message with `/tr ml`
"""

__mod_name__ = "Translator"

translator_handler = DisableAbleCommandHandler("tr", totranslate)
dispatcher.add_handler(translator_handler)
