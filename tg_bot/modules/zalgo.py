from telegram import Bot, Update
from telegram.ext import CommandHandler
from datetime import datetime
from tg_bot import dispatcher
from zalgo_text import zalgo

def zal(update: Update, context):
    # Prefer context.args for args (modern PTB style)
    args = context.args

    # If replying to a message, use its text instead of args
    if update.message.reply_to_message and update.message.reply_to_message.text:
        args = update.message.reply_to_message.text.split()

    input_text = " ".join(args).strip()
    if not input_text:
        update.message.reply_text("Type in some text!")
        return

    zalgofied_text = zalgo.zalgo().zalgofy(input_text)
    update.message.reply_text(zalgofied_text)

# Register the handler
dispatcher.add_handler(CommandHandler('zal', zal))
