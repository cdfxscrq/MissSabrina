import html
import re
import time
from typing import Optional, List, Dict, Tuple

from telegram import Message, Chat, Update, Bot, User, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext
)
from telegram.helpers import mention_html, escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER, MESSAGE_DUMP
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_ban_protected
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_welcome_type
from tg_bot.modules.helper_funcs.string_handling import markdown_parser, escape_invalid_curly_brackets
from tg_bot.modules.log_channel import loggable

# Constants
VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']
SECURITY_MODES = ["off", "soft", "hard"]
DEFAULT_MUTE_DURATION = 24 * 60 * 60  # 24 hours

# Message handler mapping
ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}

def escape_html(word: str) -> str:
    """Escape HTML special characters"""
    return html.escape(word)

def send_welcome_message(
    update: Update,
    message: str,
    keyboard: Optional[InlineKeyboardMarkup],
    backup_message: str
) -> Optional[Message]:
    """Send welcome message with proper error handling"""
    try:
        return update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except (IndexError, KeyError, BadRequest) as e:
        error_type = "Markdown issues" if isinstance(e, (IndexError, KeyError)) else "URL issues"
        error_msg = f"{backup_message}\n\n⚠️ Note: The welcome message had {error_type}. Using default message."
        LOGGER.warning("Welcome message error: %s", str(e))
        return update.effective_message.reply_text(
            markdown_parser(error_msg),
            parse_mode=ParseMode.MARKDOWN
        )

def new_member(update: Update, context: CallbackContext) -> None:
    """Handle new members joining the group"""
    chat = update.effective_chat
    bot = context.bot
    
    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    if not should_welc:
        return
    
    new_members = update.effective_message.new_chat_members
    for new_mem in new_members:
        # Special handling for bot owner
        if new_mem.id == OWNER_ID:
            update.effective_message.reply_text("My Master has arrived! Welcome back! 🤗")
            continue
        
        # Bot added to group
        if new_mem.id == bot.id:
            bot.send_message(
                MESSAGE_DUMP or OWNER_ID,
                f"Added to group: {chat.title}\nID: <code>{chat.id}</code>",
                parse_mode=ParseMode.HTML
            )
            update.effective_message.reply_text(
                "Thanks for adding me! Need help? Check @ctrlsupport!"
            )
            continue
        
        # Welcome message logic
        first_name = new_mem.first_name or "PersonWithNoName"
        last_name = new_mem.last_name or ""
        fullname = f"{first_name} {last_name}".strip()
        mention = mention_html(new_mem.id, first_name)
        username = f"@{escape_html(new_mem.username)}" if new_mem.username else mention
        count = chat.get_members_count()
        
        if cust_welcome:
            # Format custom welcome message
            valid_format = escape_invalid_curly_brackets(
                cust_welcome, VALID_WELCOME_FORMATTERS
            )
            res = valid_format.format(
                first=escape_html(first_name),
                last=escape_html(last_name),
                fullname=escape_html(fullname),
                username=username,
                mention=mention,
                count=count,
                chatname=escape_html(chat.title),
                id=new_mem.id
            )
            buttons = sql.get_welc_buttons(chat.id)
            keyb = build_keyboard(buttons)
            keyboard = InlineKeyboardMarkup(keyb) if keyb else None
        else:
            res = sql.DEFAULT_WELCOME.format(first=first_name)
            keyboard = None
        
        # Send welcome message
        sent = send_welcome_message(
            update,
            res,
            keyboard,
            sql.DEFAULT_WELCOME.format(first=first_name)
        )
        
        # Clean service message if enabled
        if sql.clean_service(chat.id):
            try:
                bot.delete_message(chat.id, update.message.message_id)
            except (BadRequest, TelegramError):
                pass
        
        # Apply security measures
        security_mode = sql.welcome_security(chat.id)
        if security_mode == "soft":
            # Restrict media for 24 hours
            bot.restrict_chat_member(
                chat.id,
                new_mem.id,
                until_date=int(time.time() + DEFAULT_MUTE_DURATION),
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )
        elif security_mode == "hard":
            # Mute completely until verification
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "✅ I'm not a BOT!",
                    callback_data=f"verify_user_{new_mem.id}"
                )
            ]])
            update.effective_message.reply_text(
                f"Hi {first_name}, please verify you're human:",
                reply_markup=keyboard
            )
            bot.restrict_chat_member(
                chat.id,
                new_mem.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        
        # Clean previous welcome message if enabled
        if sent and sql.get_clean_pref(chat.id):
            try:
                prev_welc = sql.get_clean_pref(chat.id)
                if prev_welc:
                    bot.delete_message(chat.id, prev_welc)
            except (BadRequest, TelegramError):
                pass
            sql.set_clean_welcome(chat.id, sent.message_id)

def verify_user(update: Update, context: CallbackContext) -> None:
    """Handle user verification button clicks"""
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    bot = context.bot
    
    match = re.match(r"verify_user_(\d+)", query.data)
    if not match:
        query.answer("Invalid verification request!")
        return
    
    user_id = int(match.group(1))
    if user_id == user.id:
        # Unmute the user
        bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions.all_permissions()
        )
        try:
            bot.delete_message(chat.id, query.message.message_id)
        except (BadRequest, TelegramError):
            pass
        query.answer("Verification successful! You can now chat.")
    else:
        query.answer("This verification is not for you!")

def left_member(update: Update, context: CallbackContext) -> None:
    """Handle members leaving the group"""
    chat = update.effective_chat
    bot = context.bot
    
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
    if not should_goodbye:
        return
    
    left_mem = update.effective_message.left_chat_member
    if not left_mem or left_mem.id == bot.id:
        return
    
    # Special handling for bot owner
    if left_mem.id == OWNER_ID:
        update.effective_message.reply_text("My Master has left. We'll miss you! 🤒")
        return
    
    # Format goodbye message
    first_name = left_mem.first_name or "PersonWithNoName"
    last_name = left_mem.last_name or ""
    fullname = f"{first_name} {last_name}".strip()
    mention = mention_html(left_mem.id, first_name)
    username = f"@{escape_html(left_mem.username)}" if left_mem.username else mention
    count = chat.get_members_count()
    
    if cust_goodbye:
        valid_format = escape_invalid_curly_brackets(
            cust_goodbye, VALID_WELCOME_FORMATTERS
        )
        res = valid_format.format(
            first=escape_html(first_name),
            last=escape_html(last_name),
            fullname=escape_html(fullname),
            username=username,
            mention=mention,
            count=count,
            chatname=escape_html(chat.title),
            id=left_mem.id
        )
        buttons = sql.get_gdbye_buttons(chat.id)
        keyb = build_keyboard(buttons)
        keyboard = InlineKeyboardMarkup(keyb) if keyb else None
    else:
        res = sql.DEFAULT_GOODBYE
        keyboard = None
    
    # Send goodbye message
    send_welcome_message(update, res, keyboard, sql.DEFAULT_GOODBYE)

# ADMIN COMMANDS
@user_admin
def welcome_cmd(update: Update, context: CallbackContext) -> None:
    """Handle /welcome command"""
    chat = update.effective_chat
    args = context.args
    
    if not args or args[0].lower() == "noformat":
        noformat = bool(args) and args[0].lower() == "noformat"
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            f"Welcome setting: `{pref}`\n*Welcome message:*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                update.effective_message.reply_text(
                    welcome_m + revert_buttons(buttons)
                )
            else:
                keyboard = InlineKeyboardMarkup(build_keyboard(buttons))
                send_welcome_message(
                    update,
                    welcome_m,
                    keyboard,
                    sql.DEFAULT_WELCOME
                )
        else:
            ENUM_FUNC_MAP[welcome_type](
                chat.id,
                welcome_m,
                parse_mode=None if noformat else ParseMode.MARKDOWN
            )
    
    elif args[0].lower() in ("on", "yes", "y"):
        sql.set_welc_preference(str(chat.id), True)
        update.effective_message.reply_text("I'll welcome new members!")
    
    elif args[0].lower() in ("off", "no", "n"):
        sql.set_welc_preference(str(chat.id), False)
        update.effective_message.reply_text("I'll stop welcoming new members.")
    
    else:
        update.effective_message.reply_text("Please use 'yes' or 'no'!")

# Similar updates for goodbye_cmd, set_welcome, reset_welcome, set_goodbye, reset_goodbye
# ... [Implement similar pattern for other commands] ...

@user_admin
def security_cmd(update: Update, context: CallbackContext) -> None:
    """Handle /welcomesecurity command"""
    chat = update.effective_chat
    args = context.args
    
    if not args:
        mode = sql.welcome_security(chat.id)
        update.effective_message.reply_text(
            f"Current security mode: `{mode}`\n"
            "Options: off, soft (media restriction), hard (verification required)"
        )
        return
    
    mode = args[0].lower()
    if mode not in SECURITY_MODES:
        update.effective_message.reply_text(
            "Invalid mode! Use: off, soft, or hard"
        )
        return
    
    sql.set_welcome_security(chat.id, mode)
    responses = {
        "off": "Welcome security disabled",
        "soft": "New members will have media restricted for 24 hours",
        "hard": "New members must verify they're human before chatting"
    }
    update.effective_message.reply_text(responses[mode])

# MODULE SETUP
__help__ = """
Welcome messages can be personalized with variables:
- `{first}`: User's first name
- `{last}`: User's last name
- `{fullname}`: User's full name
- `{username}`: User's username
- `{mention}`: Mention the user
- `{id}`: User's ID
- `{count}`: User's member number
- `{chatname}`: Chat name

Admin commands:
- /welcome <on/off>: Toggle welcome messages
- /setwelcome <text>: Set custom welcome message
- /resetwelcome: Reset to default welcome
- /welcomesecurity <off/soft/hard>: Set security mode
- /cleanservice <on/off>: Clean service messages
"""

__mod_name__ = "Welcomes"

# Handlers
NEW_MEM_HANDLER = MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member)
LEFT_MEM_HANDLER = MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member)
WELCOME_CMD_HANDLER = CommandHandler("welcome", welcome_cmd, filters=filters.ChatType.GROUPS)
SECURITY_HANDLER = CommandHandler("welcomesecurity", security_cmd, filters=filters.ChatType.GROUPS)
VERIFY_HANDLER = CallbackQueryHandler(verify_user, pattern=r"verify_user_\d+")

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELCOME_CMD_HANDLER)
dispatcher.add_handler(SECURITY_HANDLER)
dispatcher.add_handler(VERIFY_HANDLER)
