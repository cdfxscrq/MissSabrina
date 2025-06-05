from io import BytesIO
from time import sleep
from typing import Optional

from telegram import Update, Bot, Chat, Message, TelegramError
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackContext

import tg_bot.modules.sql.users_sql as sql
from tg_bot import SUDO_USERS, OWNER_ID, dispatcher, LOGGER
from tg_bot.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4


def get_user_id(username: str) -> Optional[int]:
    if len(username) <= 5:
        return None

    if username.startswith('@'):
        username = username[1:]

    users = sql.get_userid_by_name(username)

    if not users:
        return None
    elif len(users) == 1:
        return users[0].user_id

    for user_obj in users:
        try:
            user_data = dispatcher.bot.get_chat(user_obj.user_id)
            if user_data.username == username:
                return user_data.id
        except BadRequest as excp:
            if excp.message != 'Chat not found':
                LOGGER.exception("Error extracting user ID")
    return None


def broadcast(update: Update, context: CallbackContext):
    msg = update.effective_message
    if len(context.args) < 1:
        msg.reply_text("Please provide a message to broadcast.")
        return

    broadcast_text = " ".join(context.args)
    chats = sql.get_all_chats() or []
    failed = 0

    for chat in chats:
        try:
            context.bot.send_message(chat_id=int(chat.chat_id), text=broadcast_text)
            sleep(0.1)
        except TelegramError:
            failed += 1
            LOGGER.warning("Couldn't send broadcast to %s (%s)", str(chat.chat_id), str(chat.chat_name))

    msg.reply_text(f"Broadcast complete. {failed} groups failed to receive the message.")


def log_user(update: Update, context: CallbackContext):
    msg: Message = update.effective_message
    chat: Chat = update.effective_chat

    sql.update_user(msg.from_user.id, msg.from_user.username, chat.id, chat.title)

    if msg.reply_to_message:
        sql.update_user(msg.reply_to_message.from_user.id,
                        msg.reply_to_message.from_user.username,
                        chat.id, chat.title)

    if msg.forward_from:
        sql.update_user(msg.forward_from.id, msg.forward_from.username)


def chats(update: Update, context: CallbackContext):
    all_chats = sql.get_all_chats() or []
    chatfile = 'List of chats:\n'
    for chat in all_chats:
        chatfile += f"{chat.chat_name} - ({chat.chat_id})\n"

    with BytesIO(chatfile.encode()) as output:
        output.name = "chatlist.txt"
        update.effective_message.reply_document(document=output, filename="chatlist.txt",
                                                caption="Here is the list of chats in the database.")


def rem_chat(update: Update, context: CallbackContext):
    msg = update.effective_message
    chats = sql.get_all_chats()
    kicked_chats = 0

    for chat in chats:
        chat_id = chat.chat_id
        sleep(0.1)  # floodwait protection
        try:
            context.bot.get_chat(chat_id)
        except (BadRequest, Unauthorized):
            sql.rem_chat(chat_id)
            kicked_chats += 1

    if kicked_chats:
        msg.reply_text(f"Done! {kicked_chats} chats were removed from the database.")
    else:
        msg.reply_text("No chats needed to be removed.")


def __user_info__(user_id: int) -> str:
    if user_id == dispatcher.bot.id:
        return "I'm in every chat they're in... Oh wait, it's me."
    num_chats = sql.get_user_num_chats(user_id)
    return f"I've seen them in <code>{num_chats}</code> chats in total."


def __stats__() -> str:
    return f"{sql.num_users()} users, across {sql.num_chats()} chats"


def __migrate__(old_chat_id: int, new_chat_id: int):
    sql.migrate_chat(old_chat_id, new_chat_id)


# Register command handlers
BROADCAST_HANDLER = CommandHandler("broadcast", broadcast, filters=Filters.user(user_id=OWNER_ID))
USER_HANDLER = MessageHandler(Filters.all & Filters.group, log_user)
CHATLIST_HANDLER = CommandHandler("chatlist", chats, filters=CustomFilters.sudo_filter)
DELETE_CHATS_HANDLER = CommandHandler("cleanchats", rem_chat, filters=Filters.user(user_id=OWNER_ID))

# Dispatcher assignments
dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
dispatcher.add_handler(DELETE_CHATS_HANDLER)

# Help text
__help__ = """
- /broadcast <msg>: Send a message to all groups (Owner only).
- /chatlist: List all groups the bot is in (Sudo only).
- /cleanchats: Remove left/kicked groups from the database (Owner only).
"""
__mod_name__ = "Users"
