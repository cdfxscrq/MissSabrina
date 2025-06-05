import importlib 
import re
import html
import logging
from typing import Optional, List, Dict, Set

from telegram import Message, Chat, Update, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    DispatcherHandlerStop,
    filters
)
from telegram.helpers import escape_markdown

# Local imports
from tg_bot import (
    dispatcher,
    updater,
    TOKEN,
    WEBHOOK,
    OWNER_ID,
    DONATION_LINK,
    CERT_PATH,
    PORT,
    URL,
    LOGGER,
    ALLOW_EXCL
)
from tg_bot.modules import ALL_MODULES
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.translations.strings import tld
from tg_bot.modules.connection import connected
from tg_bot.modules.helper_funcs.misc import paginate_modules

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PM_START_TEXT = """
Hey there! I'm Rose - your group management assistant. Use /help to discover my full capabilities.

Add me to your group: [Click here](http://telegram.me/MissRose_0_Bot?startgroup=botstart) 
"""

HELP_STRINGS = f"""
Hi! I'm Rose, your group management bot. I help maintain order with features like:

- Flood control
- Warning system
- Note keeping
- Automated responses

**Essential Commands:**
- /start: Initialize the bot
- /help: Show this help message
- /donate: Support my development

Need help? Contact [My Developer](t.me/unknown_hacker_x)
""".strip()

DONATE_STRING = """Support my development!
Server costs add up - your donations help keep me running:

- [Donate via PayPal](https://paypal.com/donate)
- [Support via Ko-fi](https://ko-fi.com/developer)

All contributions directly support server costs and improvements.
"""

# Module initialization
IMPORTED: Dict[str, object] = {}
MIGRATEABLE: List[object] = []
HELPABLE: Dict[str, object] = {}
STATS: List[object] = []
USER_INFO: List[object] = []
DATA_IMPORT: List[object] = []
DATA_EXPORT: List[object] = []
CHAT_SETTINGS: Dict[str, object] = {}
USER_SETTINGS: Dict[str, object] = {}

for module_name in ALL_MODULES:
    try:
        imported_module = importlib.import_module(f"tg_bot.modules.{module_name}")
        
        if not hasattr(imported_module, "__mod_name__"):
            imported_module.__mod_name__ = imported_module.__name__
            
        mod_name_lower = imported_module.__mod_name__.lower()
        
        if mod_name_lower in IMPORTED:
            raise AttributeError(f"Duplicate module name: {mod_name_lower}")
            
        IMPORTED[mod_name_lower] = imported_module
        
        if hasattr(imported_module, "__help__") and imported_module.__help__:
            HELPABLE[mod_name_lower] = imported_module
            
        for attr in ["__migrate__", "__stats__", "__user_info__", 
                     "__import_data__", "__export_data__", 
                     "__chat_settings__", "__user_settings__"]:
            if hasattr(imported_module, attr):
                getattr(globals()[attr[2:].upper()], "append" if attr.endswith("__") else "update")(
                    {mod_name_lower: imported_module} if attr in ["__chat_settings__", "__user_settings__"] 
                    else imported_module
                )
                
    except Exception as e:
        LOGGER.exception(f"Error loading module {module_name}: {e}")


async def send_help(chat_id: int, text: str, keyboard: Optional[InlineKeyboardMarkup] = None) -> None:
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
        
    await dispatcher.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


async def start(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    args = context.args
    
    if chat.type == "private":
        if args and args[0].lower() == "help":
            help_text = tld(chat.id, "send-help").format("" if not ALLOW_EXCL else tld(chat.id, "\nAll commands work with `/` or `!`\n"))
            await send_help(chat.id, help_text)
            return
            
        elif args and args[0].lower().startswith("stngs_"):
            match = re.match(r"stngs_(.+)", args[0].lower())
            if match:
                target_chat = await context.bot.get_chat(match.group(1))
                if is_user_admin(target_chat, update.effective_user.id):
                    await send_settings(match.group(1), update.effective_user.id, False)
                else:
                    await send_settings(match.group(1), update.effective_user.id, True)
            return
            
        elif args and args[0][1:].isdigit() and "rules" in IMPORTED:
            await IMPORTED["rules"].send_rules(update, args[0], from_pm=True)
            return
            
    await send_start(update, context)


async def send_start(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    user = update.effective_user
    text = PM_START_TEXT.format(
        escape_markdown(user.first_name),
        escape_markdown(context.bot.first_name),
        OWNER_ID
    )
                
    keyboard = [
        [
            InlineKeyboardButton(
                tld(chat.id, '🥳 Add To Group'),
                url="https://t.me/MissSabrina_bot?startgroup=true"
            ),
            InlineKeyboardButton(
                "❓ Help",
                callback_data="help_back"
            )
        ],
        [
            InlineKeyboardButton(
                tld(chat.id, '👥 Support Group'), 
                url="https://t.me/SabrinaChat"
            )
        ]
    ]

    if update.callback_query:
        try:
            await update.callback_query.message.delete()
        except (BadRequest, TelegramError) as e:
            logger.warning(f"Error deleting message: {e}")
            
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        await update.effective_message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )


async def help_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    pattern_match = {
        "module": re.compile(r"help_module\((.+?)\)"),
        "prev": re.compile(r"help_prev\((.+?)\)"),
        "next": re.compile(r"help_next\((.+?)\)"),
        "back": re.compile(r"help_back")
    }
    
    try:
        if mod_match := pattern_match["module"].match(query.data):
            module = mod_match.group(1)
            text = f"*{HELPABLE[module].__mod_name__} Module Help:*\n{HELPABLE[module].__help__}"
            await query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("◀️ Back", callback_data="help_back")]]
                )
            )
            
        elif prev_match := pattern_match["prev"].match(query.data):
            curr_page = int(prev_match.group(1))
            await query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                )
            )
            
        elif next_match := pattern_match["next"].match(query.data):
            next_page = int(next_match.group(1))
            await query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                )
            )
            
        elif pattern_match["back"].match(query.data):
            await query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                )
            )
            
        await context.bot.answer_callback_query(query.id)
        
    except BadRequest as excp:
        if excp.message not in ["Message is not modified", "Query_id_invalid", "Message can't be deleted"]:
            logger.exception(f"Exception in help buttons: {query.data}")


async def get_help(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    args = context.args
    
    if chat.type != "private":
        await update.effective_message.reply_text(
            "Contact me in PM for commands:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Help",
                    url=f"t.me/{context.bot.username}?start=help"
                )
            ]])
        )
        return
        
    if len(args) >= 1 and any(args[0].lower() == x for x in HELPABLE):
        module = args[0].lower()
        text = f"*{HELPABLE[module].__mod_name__} Module Help:*\n{HELPABLE[module].__help__}"
        await send_help(
            chat.id,
            text,
            InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Back", callback_data="help_back")]]
            )
        )
    else:
        await send_help(chat.id, HELP_STRINGS)


async def migrate_chats(update: Update, context: CallbackContext) -> None:
    msg = update.effective_message
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    logger.info(f"Migrating from {old_chat} to {new_chat}")
    for mod in MIGRATEABLE:
        if hasattr(mod, "__migrate__"):
            mod.__migrate__(old_chat, new_chat)

    logger.info("Migration completed")
    raise DispatcherHandlerStop


def main() -> None:
    # Handlers configuration
    handlers = [
        DisableAbleCommandHandler("start", start, run_async=True),
        DisableAbleCommandHandler("help", get_help, run_async=True),
        DisableAbleCommandHandler("settings", get_settings, run_async=True),
        CommandHandler("donate", donate, run_async=True),
        MessageHandler(filters.StatusUpdate.MIGRATE, migrate_chats),
        CallbackQueryHandler(help_button, pattern=r"help_", run_async=True),
        CallbackQueryHandler(settings_button, pattern=r"stngs_", run_async=True)
    ]

    for handler in handlers:
        dispatcher.add_handler(handler)

    # Error handling
    dispatcher.add_error_handler(error_callback)

    # Start bot
    if WEBHOOK:
        logger.info("Starting webhook...")
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=URL + TOKEN,
            cert=CERT_PATH if CERT_PATH else None
        )
    else:
        logger.info("Starting polling...")
        updater.start_polling(
            timeout=15,
            read_latency=4,
            drop_pending_updates=True
        )

    updater.idle()


if __name__ == '__main__':
    logger.info(f"Loaded modules: {', '.join(ALL_MODULES)}")
    main()
