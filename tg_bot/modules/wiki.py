import wikipedia
from telegram import Update, Bot, ParseMode
from telegram.ext import CommandHandler
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

def wiki(update: Update, context):
    query = " ".join(context.args).strip()
    if not query:
        update.message.reply_text("Please provide a search term after /wiki.")
        return

    try:
        summary = wikipedia.summary(query, sentences=3)
        page = wikipedia.page(query)
        reply_text = f"{summary} <a href=\"{page.url}\">more</a>"
        update.message.reply_text(reply_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except wikipedia.DisambiguationError as e:
        update.message.reply_text(
            "Your search term is ambiguous. Possible options:\n" + "\n".join(e.options[:10]),
            disable_web_page_preview=True,
        )
    except wikipedia.PageError:
        update.message.reply_text("No Wikipedia page found for your query.")
    except Exception as e:
        update.message.reply_text(f"An error occurred: {e}")

__help__ = """
 - /wiki text: Returns a summary from Wikipedia for the input text.
"""
__mod_name__ = "WikiPedia"

WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki)
dispatcher.add_handler(WIKI_HANDLER)
