from io import BytesIO
from time import sleep
from typing import List
from telegram import Bot, Update, ParseMode, Chat, Message, TelegramError
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from html import escape

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, LOGGER
from tg_bot.modules.helper_funcs.chat_status import bot_admin
from tg_bot.modules.helper_funcs.filters import CustomFilters
import tg_bot.modules.sql.users_sql as sql

USERS_GROUP = 4


def escape_html(word):
    return escape(word)


@run_async
def quickscope(bot: Bot, update: Update, args: List[str]):
    if len(args) < 2:
        update.effective_message.reply_text("Usage: /quickscope user_id chat_id")
        return
    to_kick, chat_id = args[0], args[1]
    try:
        bot.kick_chat_member(chat_id, to_kick)
        update.effective_message.reply_text(f"Attempted banning {to_kick} from {chat_id}")
    except BadRequest as excp:
        update.effective_message.reply_text(f"{excp.message} {to_kick}")


@run_async
def quickunban(bot: Bot, update: Update, args: List[str]):
    if len(args) < 2:
        update.effective_message.reply_text("Usage: /quickunban user_id chat_id")
        return
    to_unban, chat_id = args[0], args[1]
    try:
        bot.unban_chat_member(chat_id, to_unban)
        update.effective_message.reply_text(f"Attempted unbanning {to_unban} from {chat_id}")
    except BadRequest as excp:
        update.effective_message.reply_text(f"{excp.message} {to_unban}")


@run_async
def banall(bot: Bot, update: Update, args: List[str]):
    chat_id = str(args[0]) if args else str(update.effective_chat.id)
    all_mems = sql.get_chat_members(chat_id)

    for mems in all_mems:
        try:
            bot.kick_chat_member(chat_id, mems.user)
            update.effective_message.reply_text(f"Tried banning {mems.user}")
            sleep(0.1)
        except BadRequest as excp:
            update.effective_message.reply_text(f"{excp.message} {mems.user}")
            continue


@run_async
def snipe(bot: Bot, update: Update, args: List[str]):
    if not args:
        update.effective_message.reply_text("Please give me a chat ID and a message to send!")
        return
    chat_id = args[0]
    to_send = " ".join(args[1:])
    if len(to_send) < 2:
        update.effective_message.reply_text("Message too short!")
        return
    try:
        bot.send_message(chat_id=int(chat_id), text=to_send)
    except TelegramError:
        LOGGER.warning("Couldn't send to group %s", str(chat_id))
        update.effective_message.reply_text("Couldn't send the message. Perhaps I'm not in that group?")


@bot_admin
def leavechat(bot: Bot, update: Update, args: List[str]):
    if not args:
        update.effective_message.reply_text("You do not seem to be referring to a chat!")
        return
    chat_id = int(args[0])
    try:
        chat = bot.get_chat(chat_id)
        bot.send_message(chat_id, "`I Go Away!`", parse_mode=ParseMode.MARKDOWN)
        bot.leave_chat(chat_id)
        update.effective_message.reply_text(f"I left group {chat.title}")
    except BadRequest as excp:
        if excp.message == "Chat not found":
            update.effective_message.reply_text("Looks like I've already been removed from that group.")
        else:
            update.effective_message.reply_text(f"Error: {excp.message}")


@run_async
def slist(bot: Bot, update: Update):
    text1 = "👑 *My sudo users are:*"
    text2 = "🛠️ *My support users are:*"

    def format_user(user_id):
        try:
            user = bot.get_chat(user_id)
            name = user.first_name
            if user.last_name:
                name += f" {user.last_name}"
            return f"- [{escape_html(name)}](tg://user?id={user.id})"
        except BadRequest:
            return f"- `{user_id}` (not found)"

    text1 += "\n" + "\n".join([format_user(uid) for uid in SUDO_USERS])
    text2 += "\n" + "\n".join([format_user(uid) for uid in SUPPORT_USERS])

    update.effective_message.reply_text(text1, parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text(text2, parse_mode=ParseMode.MARKDOWN)


__help__ = """
*Special Admin Commands:*

*Owner only:*
- `/getlink <chatid>`: Get the invite link for a specific chat.
- `/banall`: Ban all members from a chat.
- `/snipe <chatid> <message>`: Send a message to a specific chat.
- `/leavechat <chatid>`: Leave a chat.

*Sudo / Owner only:*
- `/quickscope <user_id> <chat_id>`: Ban a user from a chat.
- `/quickunban <user_id> <chat_id>`: Unban a user from a chat.
- `/stats`: Check bot stats.
- `/chatlist`: Get list of chats.
- `/gbanlist`: List globally banned users.

*Support Users:*
- `/gban`: Globally ban a user.
- `/ungban`: Ungban a user.

*Sudo/Support Users:*
- `/slist`: List sudo and support users.
"""

__mod_name__ = "Special"

# Handlers
SNIPE_HANDLER = CommandHandler("snipe", snipe, pass_args=True, filters=Filters.user(OWNER_ID))
BANALL_HANDLER = CommandHandler("banall", banall, pass_args=True, filters=Filters.user(OWNER_ID))
QUICKSCOPE_HANDLER = CommandHandler("quickscope", quickscope, pass_args=True, filters=CustomFilters.sudo_filter)
QUICKUNBAN_HANDLER = CommandHandler("quickunban", quickunban, pass_args=True, filters=CustomFilters.sudo_filter)
LEAVECHAT_HANDLER = CommandHandler("leavechat", leavechat, pass_args=True, filters=Filters.user(OWNER_ID))
SLIST_HANDLER = CommandHandler("slist", slist, filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

# Add handlers
dispatcher.add_handler(SNIPE_HANDLER)
dispatcher.add_handler(BANALL_HANDLER)
dispatcher.add_handler(QUICKSCOPE_HANDLER)
dispatcher.add_handler(QUICKUNBAN_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)
dispatcher.add_handler(SLIST_HANDLER)
