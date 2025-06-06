import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import reporting_sql as sql

REPORT_GROUP = 5

@user_admin
def report_setting(update: Update, context):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message
    args: List[str] = context.args if context.args else []

    if chat.type == chat.PRIVATE:
        if args:
            if args[0].lower() in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text("Turned on reporting! You'll be notified whenever anyone reports something.")
            elif args[0].lower() in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Turned off reporting! You won't get any reports.")
        else:
            current = sql.user_should_report(chat.id)
            msg.reply_text(
                f"Your current report preference is: `{current}`",
                parse_mode="Markdown"
            )
    else:
        if args:
            if args[0].lower() in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text(
                    "Turned on reporting! Admins who have turned on reports will be notified when /report or @admin are called."
                )
            elif args[0].lower() in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text(
                    "Turned off reporting! No admins will be notified on /report or @admin."
                )
        else:
            current = sql.chat_should_report(chat.id)
            msg.reply_text(
                f"This chat's current setting is: `{current}`",
                parse_mode="Markdown"
            )

@user_not_admin
@loggable
def report(update: Update, context) -> str:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user: Optional[User] = message.reply_to_message.from_user
        chat_name = chat.title or chat.first_name or chat.username
        admin_list = chat.get_administrators()

        if chat.username and chat.type == Chat.SUPERGROUP:
            msg = (
                f"<b>{html.escape(chat.title)}:</b>"
                f"\n<b>Reported user:</b> {mention_html(reported_user.id, reported_user.first_name)} (<code>{reported_user.id}</code>)"
                f"\n<b>Reported by:</b> {mention_html(user.id, user.first_name)} (<code>{user.id}</code>)"
            )
            link = (
                f"\n<b>Link:</b> "
                f'<a href="http://t.me/{chat.username}/{message.message_id}">click here</a>'
            )
            should_forward = False
        else:
            msg = (
                f'{mention_html(user.id, user.first_name)} is calling for admins in "{html.escape(chat_name)}"!'
            )
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:
                continue
            if sql.user_should_report(admin.user.id):
                try:
                    context.bot.send_message(admin.user.id, msg + link, parse_mode="HTML")
                    if should_forward:
                        message.reply_to_message.forward(admin.user.id)
                        if message.text and len(message.text.split()) > 1:
                            message.forward(admin.user.id)
                except Unauthorized:
                    continue
                except BadRequest:
                    LOGGER.exception("Exception while reporting user")
        return msg
    return ""

def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)

def __chat_settings__(chat_id, user_id):
    return f"This chat is setup to send user reports to admins, via /report and @admin: `{sql.chat_should_report(chat_id)}`"

def __user_settings__(user_id):
    return (
        f"You receive reports from chats you're admin in: `{sql.user_should_report(user_id)}`.\n"
        "Toggle this with /reports in PM."
    )

__mod_name__ = "Reporting"

__help__ = """
 - /report <reason>: reply to a message to report it to admins.
 - @admin: reply to a message to report it to admins.
NOTE: neither of these will get triggered if used by admins

*Admin only:*
 - /reports <on/off>: change report setting, or view current status.
   - If done in pm, toggles your status.
   - If in chat, toggles that chat's status.
"""

REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = MessageHandler(Filters.regex(r"(?i)@admin(s)?"), report)

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
