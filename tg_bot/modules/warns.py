import html
import re
from typing import Optional, List, Dict, Tuple

from telegram import (
    Update,
    User,
    Chat,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ParseMode
)
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.error import BadRequest

from tg_bot import dispatcher, BAN_STICKER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    is_user_admin, 
    bot_admin, 
    user_admin, 
    can_restrict
)
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text, extract_user
from tg_bot.modules.helper_funcs.string_handling import split_quotes
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import warns_sql as sql

# Constants
WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>Current warning filters in this chat:</b>\n"
DEFAULT_WARN_LIMIT = 3
MAX_WARN_REASONS_DISPLAY = 10

# Not async
def warn_user(
    user: User,
    chat: Chat,
    reason: str,
    message: Message,
    warner: User = None
) -> Tuple[Optional[str], Optional[Message]]:
    """Warn a user and handle consequences"""
    if is_user_admin(chat, user.id):
        message.reply_text("Admins can't be warned!")
        return None, None

    warner_tag = mention_html(warner.id, warner.first_name) if warner else "Automated warning system"
    limit, soft_warn = sql.get_warn_setting(chat.id) or (DEFAULT_WARN_LIMIT, True)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # Kick
            chat.unban_member(user.id)
            action = "kicked"
        else:  # Ban
            chat.ban_member(user.id)
            action = "banned"
        
        reply_text = f"⚠️ {mention_html(user.id, user.first_name)} has been {action} for reaching {limit} warnings!"
        if reasons:
            reply_text += "\n\n<b>Warn Reasons:</b>"
            for i, warn_reason in enumerate(reasons[:MAX_WARN_REASONS_DISPLAY], 1):
                reply_text += f"\n{i}. {html.escape(warn_reason)}"
            if len(reasons) > MAX_WARN_REASONS_DISPLAY:
                reply_text += f"\n...and {len(reasons) - MAX_WARN_REASONS_DISPLAY} more"
        
        sent_msg = message.reply_text(reply_text, parse_mode=ParseMode.HTML)
        message.bot.send_sticker(chat.id, BAN_STICKER)  # Ban sticker
        
        log_reason = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#WARN_{action.upper()}\n"
            f"<b>Admin:</b> {warner_tag}\n"
            f"<b>User:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Reason:</b> {reason}\n"
            f"<b>Count:</b> {num_warns}/{limit}"
        )
        return log_reason, sent_msg
    
    # Under warning limit
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "❌ Remove warn", 
            callback_data=f"rm_warn_{user.id}"
        )
    ]])
    
    reply_text = (
        f"⚠️ {mention_html(user.id, user.first_name)} has been warned by {warner_tag}\n"
        f"Warnings: {num_warns}/{limit}"
    )
    if reason:
        reply_text += f"\n\n<b>Reason:</b>\n{html.escape(reason)}"
    
    try:
        sent_msg = message.reply_text(
            reply_text, 
            reply_markup=keyboard, 
            parse_mode=ParseMode.HTML
        )
    except BadRequest:
        # Try without quoting if reply fails
        sent_msg = message.reply_text(
            reply_text, 
            reply_markup=keyboard, 
            parse_mode=ParseMode.HTML,
            quote=False
        )
    
    log_reason = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#WARN\n"
        f"<b>Admin:</b> {warner_tag}\n"
        f"<b>User:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Reason:</b> {reason}\n"
        f"<b>Count:</b> {num_warns}/{limit}"
    )
    return log_reason, sent_msg

@user_admin
@bot_admin
@loggable
def warn_command(update: Update, context: CallbackContext) -> str:
    """Handle /warn command"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    args = context.args
    
    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("Please specify a user to warn!")
        return ""
    
    if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
        target_user = message.reply_to_message.from_user
    else:
        try:
            target_user = context.bot.get_chat_member(chat.id, user_id).user
        except BadRequest:
            message.reply_text("Couldn't find that user!")
            return ""
    
    log_reason, _ = warn_user(target_user, chat, reason, message, user)
    return log_reason

@user_admin
@bot_admin
@loggable
def reset_warns_command(update: Update, context: CallbackContext) -> str:
    """Handle /resetwarns command"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    args = context.args
    
    user_id = extract_user(message, args) if args else None
    if not user_id:
        message.reply_text("Please specify a user!")
        return ""
    
    try:
        target_user = context.bot.get_chat_member(chat.id, user_id).user
    except BadRequest:
        message.reply_text("Couldn't find that user!")
        return ""
    
    sql.reset_warns(user_id, chat.id)
    message.reply_text(f"⚠️ Warnings for {target_user.first_name} have been reset!")
    
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESETWARNS\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(target_user.id, target_user.first_name)}"
    )

def get_warns_command(update: Update, context: CallbackContext):
    """Handle /warns command"""
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)
    
    if not result or result[0] == 0:
        message.reply_text("This user has no warnings!")
        return
    
    num_warns, reasons = result
    limit, _ = sql.get_warn_setting(chat.id) or (DEFAULT_WARN_LIMIT, True)
    
    if reasons:
        text = (
            f"⚠️ {mention_html(user_id, 'this user' if user_id != update.effective_user.id else 'you')} "
            f"has {num_warns}/{limit} warnings:\n\n"
        )
        for i, reason in enumerate(reasons, 1):
            text += f"{i}. {html.escape(reason)}\n"
        message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        message.reply_text(
            f"User has {num_warns}/{limit} warnings, but no reasons were recorded",
            parse_mode=ParseMode.HTML
        )

@user_admin
@loggable
def remove_warn_button(update: Update, context: CallbackContext) -> str:
    """Handle remove warn button callback"""
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    
    # Extract user ID from callback data
    match = re.match(r"rm_warn_(\d+)", query.data)
    if not match:
        query.answer("Invalid request!")
        return ""
    
    user_id = match.group(1)
    res = sql.remove_warn(user_id, chat.id)
    
    if res:
        query.answer("Warn removed!")
        query.edit_message_text(
            f"✅ Warn removed by {mention_html(user.id, user.first_name)}",
            parse_mode=ParseMode.HTML
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#UNWARN\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>User:</b> {mention_html(int(user_id), 'the user')}"
        )
    else:
        query.answer("No warn to remove!")
        return ""

# Warning filter handlers (similar pattern as above)
@user_admin
def add_warn_filter(update: Update, context: CallbackContext):
    # Implementation here (similar to original but updated)
    pass

@user_admin
def remove_warn_filter(update: Update, context: CallbackContext):
    # Implementation here
    pass

def list_warn_filters(update: Update, context: CallbackContext):
    # Implementation here
    pass

@user_admin
@loggable
def set_warn_limit(update: Update, context: CallbackContext) -> str:
    """Set warning limit"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    args = context.args
    
    if not args or not args[0].isdigit():
        limit, _ = sql.get_warn_setting(chat.id) or (DEFAULT_WARN_LIMIT, True)
        message.reply_text(f"Current warning limit: {limit}")
        return ""
    
    new_limit = int(args[0])
    if new_limit < 3:
        message.reply_text("Minimum warn limit is 3!")
        return ""
    
    sql.set_warn_limit(chat.id, new_limit)
    message.reply_text(f"✅ Warning limit updated to {new_limit}")
    
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WARN_LIMIT\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Set warn limit to {new_limit}"
    )

@user_admin
@loggable
def set_warn_strength(update: Update, context: CallbackContext) -> str:
    """Set warning strength (kick/ban)"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    args = context.args
    
    if not args:
        _, soft_warn = sql.get_warn_setting(chat.id) or (DEFAULT_WARN_LIMIT, True)
        action = "kick" if soft_warn else "ban"
        message.reply_text(f"Current action on exceeding warnings: {action}")
        return ""
    
    arg = args[0].lower()
    if arg in ("on", "yes", "ban"):
        sql.set_warn_strength(chat.id, False)
        message.reply_text("⚠️ Exceeding warnings will now result in a BAN")
        action = "ban"
    elif arg in ("off", "no", "kick"):
        sql.set_warn_strength(chat.id, True)
        message.reply_text("⚠️ Exceeding warnings will now result in a KICK")
        action = "kick"
    else:
        message.reply_text("Please use 'on/yes/ban' or 'off/no/kick'")
        return ""
    
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WARN_STRENGTH\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Set warn action to {action}"
    )

# Module registration
__help__ = """
⚠️ **Warning System**

Keep your group safe with a configurable warning system:

- `/warn <user> [reason]`: Warn a user
- `/warns <user>`: Check a user's warnings
- `/resetwarns <user>`: Reset a user's warnings
- `/warnlimit <number>`: Set warning limit (min 3)
- `/warnaction <kick/ban>`: Set action on max warnings

*Admin only commands*
"""

__mod_name__ = "Warnings"

# Handlers
dispatcher.add_handler(CommandHandler(
    "warn", warn_command, filters=filters.ChatType.GROUPS
))
dispatcher.add_handler(CommandHandler(
    "resetwarns", reset_warns_command, filters=filters.ChatType.GROUPS
))
dispatcher.add_handler(CommandHandler(
    "warns", get_warns_command, filters=filters.ChatType.GROUPS
))
dispatcher.add_handler(CommandHandler(
    "warnlimit", set_warn_limit, filters=filters.ChatType.GROUPS
))
dispatcher.add_handler(CommandHandler(
    "warnaction", set_warn_strength, filters=filters.ChatType.GROUPS
))
dispatcher.add_handler(CallbackQueryHandler(
    remove_warn_button, pattern=r"rm_warn_"
))

# Add handlers for warn filters
# dispatcher.add_handler(CommandHandler(...))
