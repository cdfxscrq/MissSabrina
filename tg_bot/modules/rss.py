import html
import re
from typing import List

from feedparser import parse
from telegram import ParseMode, constants, Update
from telegram.ext import CommandHandler, CallbackContext

from tg_bot import dispatcher, updater
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.sql import rss_sql as sql

def show_url(update: Update, context: CallbackContext) -> None:
    tg_chat_id = str(update.effective_chat.id)
    args = context.args

    if not args or len(args) < 1:
        update.effective_message.reply_text("URL missing")
        return

    tg_feed_link = args[0]
    link_processed = parse(tg_feed_link)

    if link_processed.bozo != 0:
        update.effective_message.reply_text("This link is not an RSS Feed link")
        return

    feed_title = link_processed.feed.get("title", "Unknown")
    feed_description = "<i>{}</i>".format(
        re.sub('<[^<]+?>', '', link_processed.feed.get("description", "Unknown")))
    feed_link = link_processed.feed.get("link", "Unknown")

    feed_message = (
        f"<b>Feed Title:</b>\n{html.escape(feed_title)}"
        f"\n\n<b>Feed Description:</b>\n{feed_description}"
        f"\n\n<b>Feed Link:</b>\n{html.escape(feed_link)}"
    )

    entry_message = ""
    if link_processed.entries:
        entry = link_processed.entries[0]
        entry_title = entry.get("title", "Unknown")
        entry_description = "<i>{}</i>".format(
            re.sub('<[^<]+?>', '', entry.get("description", "Unknown")))
        entry_link = entry.get("link", "Unknown")

        entry_message = (
            f"\n\n<b>Entry Title:</b>\n{html.escape(entry_title)}"
            f"\n\n<b>Entry Description:</b>\n{entry_description}"
            f"\n\n<b>Entry Link:</b>\n{html.escape(entry_link)}"
        )

    final_message = feed_message + entry_message
    context.bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)

def list_urls(update: Update, context: CallbackContext) -> None:
    tg_chat_id = str(update.effective_chat.id)
    user_data = sql.get_urls(tg_chat_id)
    links_list: List[str] = [row.feed_link for row in user_data]
    final_content = "\n\n".join(links_list)

    if not final_content:
        context.bot.send_message(chat_id=tg_chat_id, text="This chat is not subscribed to any links")
    elif len(final_content) <= constants.MAX_MESSAGE_LENGTH:
        context.bot.send_message(
            chat_id=tg_chat_id,
            text="This chat is subscribed to the following links:\n" + final_content
        )
    else:
        context.bot.send_message(
            chat_id=tg_chat_id,
            parse_mode=ParseMode.HTML,
            text="<b>Warning:</b> The message is too long to be sent"
        )

@user_admin
def add_url(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args or len(args) < 1:
        update.effective_message.reply_text("URL missing")
        return

    tg_chat_id = str(update.effective_chat.id)
    tg_feed_link = args[0]
    link_processed = parse(tg_feed_link)

    if link_processed.bozo != 0:
        update.effective_message.reply_text("This link is not an RSS Feed link")
        return

    tg_old_entry_link = ""
    if link_processed.entries and len(link_processed.entries[0].get("link", "")) > 0:
        tg_old_entry_link = link_processed.entries[0].get("link", "")

    row = sql.check_url_availability(tg_chat_id, tg_feed_link)
    if row:
        update.effective_message.reply_text("This URL has already been added")
    else:
        sql.add_url(tg_chat_id, tg_feed_link, tg_old_entry_link)
        update.effective_message.reply_text("Added URL to subscription")

@user_admin
def remove_url(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args or len(args) < 1:
        update.effective_message.reply_text("URL missing")
        return

    tg_chat_id = str(update.effective_chat.id)
    tg_feed_link = args[0]
    link_processed = parse(tg_feed_link)

    if link_processed.bozo != 0:
        update.effective_message.reply_text("This link is not an RSS Feed link")
        return

    user_data = sql.check_url_availability(tg_chat_id, tg_feed_link)
    if user_data:
        sql.remove_url(tg_chat_id, tg_feed_link)
        update.effective_message.reply_text("Removed URL from subscription")
    else:
        update.effective_message.reply_text("You haven't subscribed to this URL yet")

def rss_update(context: CallbackContext) -> None:
    user_data = sql.get_all()
    for row in user_data:
        row_id = row.id
        tg_chat_id = row.chat_id
        tg_feed_link = row.feed_link
        feed_processed = parse(tg_feed_link)
        tg_old_entry_link = row.old_entry_link

        new_entry_links = []
        new_entry_titles = []

        for entry in feed_processed.entries:
            entry_link = entry.get("link", "")
            entry_title = entry.get("title", "")
            if entry_link != tg_old_entry_link:
                new_entry_links.append(entry_link)
                new_entry_titles.append(entry_title)
            else:
                break

        if new_entry_links:
            sql.update_url(row_id, new_entry_links)

        max_send = 5
        entries_to_send = list(zip(reversed(new_entry_links[-max_send:]), reversed(new_entry_titles[-max_send:])))
        for link, title in entries_to_send:
            final_message = f"<b>{html.escape(title)}</b>\n\n{html.escape(link)}"
            if len(final_message) <= constants.MAX_MESSAGE_LENGTH:
                context.bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)
            else:
                context.bot.send_message(chat_id=tg_chat_id, text="<b>Warning:</b> The message is too long to be sent", parse_mode=ParseMode.HTML)

        if len(new_entry_links) > max_send:
            context.bot.send_message(
                chat_id=tg_chat_id,
                parse_mode=ParseMode.HTML,
                text=f"<b>Warning: </b>{len(new_entry_links) - max_send} occurrences have been left out to prevent spam"
            )

def rss_set(context: CallbackContext) -> None:
    user_data = sql.get_all()
    for row in user_data:
        row_id = row.id
        tg_feed_link = row.feed_link
        tg_old_entry_link = row.old_entry_link

        feed_processed = parse(tg_feed_link)
        new_entry_links = []
        new_entry_titles = []

        for entry in feed_processed.entries:
            entry_link = entry.get("link", "")
            entry_title = entry.get("title", "")
            if entry_link != tg_old_entry_link:
                new_entry_links.append(entry_link)
                new_entry_titles.append(entry_title)
            else:
                break

        if new_entry_links:
            sql.update_url(row_id, new_entry_links)

__help__ = """
 - /addrss <link>: add an RSS link to the subscriptions.
 - /removerss <link>: removes the RSS link from the subscriptions.
 - /rss <link>: shows the link's data and the last entry, for testing purposes.
 - /listrss: shows the list of rss feeds that the chat is currently subscribed to.

NOTE: In groups, only admins can add/remove RSS links to the group's subscription
"""

__mod_name__ = "RSS Feed"

job = updater.job_queue
job_rss_set = job.run_once(rss_set, 5)
job_rss_update = job.run_repeating(rss_update, interval=60, first=60)
job_rss_set.enabled = True
job_rss_update.enabled = True

SHOW_URL_HANDLER = CommandHandler("rss", show_url, pass_args=True)
ADD_URL_HANDLER = CommandHandler("addrss", add_url, pass_args=True)
REMOVE_URL_HANDLER = CommandHandler("removerss", remove_url, pass_args=True)
LIST_URLS_HANDLER = CommandHandler("listrss", list_urls)

dispatcher.add_handler(SHOW_URL_HANDLER)
dispatcher.add_handler(ADD_URL_HANDLER)
dispatcher.add_handler(REMOVE_URL_HANDLER)
dispatcher.add_handler(LIST_URLS_HANDLER)
