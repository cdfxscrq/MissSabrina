import sys

# Prevent using sample_config.py directly
if not __name__.endswith("sample_config"):
    print(
        "❌ You're running the sample config directly!\n"
        "Please create a new 'config.py' file by extending this file.\n"
        "Don't just rename and change values here — it will backfire.\n"
        "Bot quitting.",
        file=sys.stderr
    )
    sys.exit(1)

# ─────────────────────────────────────────────────────────
# Base Configuration Class - Extend this in your config.py
# ─────────────────────────────────────────────────────────
class Config(object):
    LOGGER = True  # Enable or disable logging

    # REQUIRED
    API_KEY = ""  # Your bot token from @BotFather
    OWNER_ID = "594813047"  # Run /id in PM to @MissRose_bot to get your user ID
    OWNER_USERNAME = "refundisillegal"  # Owner's Telegram username (without @)

    # RECOMMENDED
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@hostname:port/db_name'
    MESSAGE_DUMP = None  # Optional: Chat ID to store replied messages
    LOAD = []  # Modules to load explicitly
    NO_LOAD = ['translation', 'rss']  # Modules to skip loading
    WEBHOOK = False  # Use webhook or polling
    URL = None  # Webhook URL (if any)

    # OPTIONAL ACCESS LISTS
    SUDO_USERS = []  # List of user IDs with sudo privileges
    SUPPORT_USERS = []  # List of user IDs with limited mod access (can gban, but can be banned)
    WHITELIST_USERS = []  # List of user IDs immune to bans/kicks

    # OPTIONAL CONFIG
    DONATION_LINK = None  # e.g., PayPal, BuyMeACoffee
    CERT_PATH = None  # Path to SSL certificate (for webhooks)
    PORT = 5000  # Port for webhooks
    DEL_CMDS = False  # Delete "blue text" command messages
    STRICT_GBAN = False  # Enforce gbans in all groups, including new ones
    WORKERS = 8  # Number of subthreads to use
    BAN_STICKER = 'CAADAgADOwADPPEcAXkko5EB3YGYAg'  # Sticker file_id used on ban
    KICK_STICKER = False  # Optional: Sticker to use on kick
    ALLOW_EXCL = False  # Allow ! commands in addition to /
    API_OPENWEATHER = False  # Your OpenWeatherMap API key (optional)
    TEMPORARY_DATA = None  # For backup/restore purposes, e.g., session temp storage


# ───────────────────────────────
# Deployment-specific extensions
# ───────────────────────────────
class Production(Config):
    LOGGER = False


class Development(Config):
    LOGGER = True
