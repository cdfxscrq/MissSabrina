from telegram import Update, Bot, ParseMode
from telegram.ext import run_async

from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher


@run_async
def shout(bot: Bot, update: Update, args):
    if not args:
        update.effective_message.reply_text("Please provide text to shout. Usage: /shout <text>")
        return

    text = " ".join(args)
    result = []

    # First line: spaced characters
    result.append(" ".join(text))

    # Diagonal pattern
    for i in range(1, len(text)):
        space_between = " " * (2 * i - 1)
        line = text[i] + space_between + text[i]
        result.append(line)

    final_msg = "\n".join(result)
    update.effective_message.reply_text(
        f"<pre>{final_msg}</pre>", parse_mode=ParseMode.HTML
    )


__help__ = """
A little piece of fun wording! Give a loud shout out in the chatroom.

- /shout <text>: Make me shout your word in a creative pattern.

Example:
/shout test

Output:
t e s t
e   e
s     s
t       t
"""

__mod_name__ = "Shout"

SHOUT_HANDLER = DisableAbleCommandHandler("shout", shout, pass_args=True)
dispatcher.add_handler(SHOUT_HANDLER)
