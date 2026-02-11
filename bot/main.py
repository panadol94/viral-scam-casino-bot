"""Main entry point — bot startup with webhook (self-signed SSL)."""

import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from telegram import ChatMemberUpdated, Update
from telegram.ext import Application, ChatMemberHandler, ContextTypes, MessageHandler, filters

from bot.database import deactivate_chat, init_db, upsert_chat
from bot.handlers.admin import get_admin_handlers
from bot.handlers.broadcast import get_broadcast_handlers
from bot.handlers.report import get_report_handler
from bot.handlers.search import get_search_handlers
from bot.handlers.start import get_start_handlers

load_dotenv()

# ── Config ────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
PORT = int(os.getenv("PORT", "8443"))

CERT_DIR = Path("/app/certs")
CERT_FILE = CERT_DIR / "cert.pem"
KEY_FILE = CERT_DIR / "key.pem"

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _generate_self_signed_cert() -> None:
    """Generate self-signed SSL certificate for webhook."""
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    if CERT_FILE.exists() and KEY_FILE.exists():
        logger.info("SSL certs already exist, reusing.")
        return

    # Extract IP/domain from WEBHOOK_URL for the CN
    from urllib.parse import urlparse
    parsed = urlparse(WEBHOOK_URL)
    cn = parsed.hostname or "localhost"

    logger.info(f"Generating self-signed SSL cert for CN={cn}...")
    subprocess.run(
        [
            "openssl", "req", "-newkey", "rsa:2048",
            "-sha256", "-nodes",
            "-keyout", str(KEY_FILE),
            "-x509", "-days", "3650",
            "-out", str(CERT_FILE),
            "-subj", f"/C=MY/ST=KL/L=KL/O=ScamBot/CN={cn}",
        ],
        check=True,
        capture_output=True,
    )
    logger.info("SSL cert generated!")


async def post_init(application: Application) -> None:
    """Initialize database after bot starts."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready!")

    # Set bot commands
    await application.bot.set_my_commands([
        ("start", "Mula / Menu utama"),
        ("report", "Buat laporan scam casino"),
        ("search", "Cari casino dalam database"),
        ("check", "Semak link casino"),
        ("stats", "Statistik laporan"),
        ("broadcast", "📢 Broadcast (Owner)"),
        ("help", "Bantuan"),
    ])
    logger.info("Bot commands set!")


# ── Auto-tracking helpers ────────────────────────────────────────


async def _track_bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Track when bot is added/removed from groups or channels."""
    member_update: ChatMemberUpdated = update.my_chat_member
    chat = member_update.chat
    new_status = member_update.new_chat_member.status

    if new_status in ("member", "administrator"):
        # Bot added to a chat
        await upsert_chat(
            chat_id=chat.id,
            chat_type=chat.type,
            title=chat.title,
            username=chat.username,
        )
        logger.info(f"Bot added to {chat.type} '{chat.title}' ({chat.id})")
    elif new_status in ("left", "kicked"):
        # Bot removed from chat
        await deactivate_chat(chat.id)
        logger.info(f"Bot removed from {chat.type} '{chat.title}' ({chat.id})")


async def _track_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Passively track groups the bot is already in when messages arrive."""
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        await upsert_chat(
            chat_id=chat.id,
            chat_type=chat.type,
            title=chat.title,
            username=chat.username,
        )


def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN env var is required!")

    builder = Application.builder().token(BOT_TOKEN)
    application = builder.post_init(post_init).build()

    # Register handlers
    for handler in get_start_handlers():
        application.add_handler(handler)

    application.add_handler(get_report_handler())

    for handler in get_search_handlers():
        application.add_handler(handler)

    for handler in get_admin_handlers():
        application.add_handler(handler)

    for handler in get_broadcast_handlers():
        application.add_handler(handler)

    # ── Auto-tracking: groups/channels ────────────────────────────
    application.add_handler(
        ChatMemberHandler(_track_bot_status, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), _track_group_message),
        group=-1,  # run before other handlers, won't consume update
    )

    # Start bot
    if WEBHOOK_URL:
        # Generate self-signed cert for webhook SSL
        _generate_self_signed_cert()

        webhook_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
        logger.info(f"Starting webhook on port {PORT}, URL: {webhook_url}")

        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH.lstrip("/"),
            webhook_url=webhook_url,
            cert=str(CERT_FILE),
            key=str(KEY_FILE),
            drop_pending_updates=True,
        )
    else:
        # Polling mode (for local dev)
        logger.info("Starting in polling mode (no WEBHOOK_URL set)")
        application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
