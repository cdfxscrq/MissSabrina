import html
from typing import Optional, List

from telegram import Message, Update, Bot, User, ParseMode, MAX_MESSAGE_LENGTH
from telegram.utils.helpers import escape_markdown
from telegram.ext import CallbackContext

import tg_bot.modules.sql.userinfo_sql as sql
from tg_bot import dispatcher, SUDO_USERS, OWNER_ID
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user


def about_me(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    user_id = extract_user(message, context.args)

    user = update.effective_user if not user_id else context.bot.get_chat(user_id)
    info = sql.get_user_me_info(user.id)

    if info:
        message.reply_text(
            f"*{user.first_name}*:\n{escape_markdown(info)}",
            parse_mode=ParseMode.MARKDOWN
        )
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        message.reply_text(f"{username} hasn't shared any information yet!")
    else:
        message.reply_text("You haven't added any information about yourself yet.")


def set_about_me(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    user_id = update.effective_user.id

    info_text = message.text.split(None, 1)
    if len(info_text) == 2:
        content = info_text[1]
        if len(content) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, content)
            message.reply_text("Your information has been saved successfully.")
        else:
            message.reply_text(
                f"Text too long! Limit: {MAX_MESSAGE_LENGTH // 4} characters. You used: {len(content)}."
            )
    else:
        message.reply_text("Please provide some information after the command.")


def about_bio(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    user_id = extract_user(message, context.args)

    user = update.effective_user if not user_id else context.bot.get_chat(user_id)
    info = sql.get_user_bio(user.id)

    if info:
        message.reply_text(
            f"*{user.first_name}*:\n{escape_markdown(info)}",
            parse_mode=ParseMode.MARKDOWN
        )
    elif message.reply_to_message:
        username = user.first_name
        message.reply_text(f"{username} hasn't added a bio yet!")
    else:
        message.reply_text("You haven't set a bio yet.")


def set_about_bio(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    sender: Optional[User] = update.effective_user

    if not message.reply_to_message:
        message.reply_text("Reply to someone's message to set their bio.")
        return

    replied_user = message.reply_to_message.from_user
    user_id = replied_user.id

    if user_id == sender.id:
        message.reply_text("Just use /setme to set your own info.")
        return
    if user_id == context.bot.id and sender.id not in SUDO_USERS:
        message.reply_text("Only sudo users can update my bio.")
        return
    if user_id == OWNER_ID:
        message.reply_text("You can't modify the owner's bio 😏.")
        return

    bio_text = message.text.split(None, 1)
    if len(bio_text) == 2:
        content = bio_text[1]
        if len(content) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_bio(user_id, content)
            message.reply_text(f"Updated {replied_user.first_name}'s bio.")
        else:
            message.reply_text(
                f"Bio too long! Limit: {MAX_MESSAGE_LENGTH // 4}, you used: {len(content)}."
            )
    else:
        message.reply_text("Please add bio text after the command.")


def __user_info__(user_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return f"<b>About user:</b>\n{me}\n\n<b>What others say:</b>\n{bio}"
    elif bio:
        return f"<b>What others say:</b>\n{bio}"
    elif me:
        return f"<b>About user:</b>\n{me}"
    else:
        return ""


__help__ = """
- /setbio <text>: (while replying) Set another user's bio.
- /bio: Get your or another user's bio. Can't set your own.
- /setme <text>: Set your own personal info.
- /me: Get your or another user's info.
"""

__mod_name__ = "Bios & Abouts"

# Handlers
SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, pass_args=True)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)
