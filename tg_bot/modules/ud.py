from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher

import requests
import html


async def ud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not context.args:
        await message.reply_text("Please provide a word to look up. Example: /ud telegram")
        return

    term = " ".join(context.args).strip()
    url = f"http://api.urbandictionary.com/v0/define?term={term}"

    try:
        results = requests.get(url).json()
        if not results["list"]:
            await message.reply_text(f"No results found for *{term}*.", parse_mode="Markdown")
            return

        definition = results["list"][0]["definition"].strip()
        example = results["list"][0].get("example", "").strip()

        reply_text = f"*Word:* {html.escape(term)}\n\n"
        reply_text += f"*Definition:*\n{html.escape(definition)}"

        if example:
            reply_text += f"\n\n*Example:*\n_{html.escape(example)}_"

        await message.reply_text(reply_text, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text("An error occurred while fetching the definition. Try again later.")


__help__ = """
- `/ud <word>`: Get the Urban Dictionary definition of a word.
  • Example: `/ud telegram`
"""

__mod_name__ = "Urban Dictionary"

ud_handler = DisableAbleCommandHandler("ud", ud)
dispatcher.add_handler(ud_handler)
