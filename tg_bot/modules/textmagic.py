from typing import List
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

normiefont = list("abcdefghijklmnopqrstuvwxyz")
weebyfont = ['🅐', '🅑', '🅒', '🅓', '🅔', '🅕', '🅖', '🅗', '🅘', '🅙', '🅚', '🅛', '🅜',
             '🅝', '🅞', '🅟', '🅠', '🅡', '🅢', '🅣', '🅤', '🅥', '🅦', '🅧', '🅨', '🅩']

def blackout_text(input_text: str) -> str:
    transformed = ''
    for char in input_text.lower():
        if char in normiefont:
            index = normiefont.index(char)
            transformed += weebyfont[index]
        else:
            transformed += char
    return transformed

async def weebify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if context.args:
        input_text = ' '.join(context.args)
    elif message.reply_to_message and message.reply_to_message.text:
        input_text = message.reply_to_message.text
    else:
        await message.reply_text("❗ Provide some text or reply to a message to blackout.")
        return

    result = blackout_text(input_text)

    if message.reply_to_message:
        await message.reply_to_message.reply_text(result)
    else:
        await message.reply_text(result)

__help__ = """
🖤 /blackout <text> — Transforms your text into blackout (🅐🅑🅒...) style.

You can also reply to any message with /blackout to transform it.
"""

__mod_name__ = "Black Out"

blackout_handler = DisableAbleCommandHandler("blackout", weebify)
dispatcher.add_handler(blackout_handler)
