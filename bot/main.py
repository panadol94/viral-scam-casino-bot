"""Main entry point — bot startup with webhook."""

import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application

from bot.database import init_db
from bot.handlers.admin import get_admin_handlers
from bot.handlers.report import get_report_handler
from bot.handlers.search import get_search_handlers
from bot.handlers.start import get_start_handlers

load_dotenv()

# ── Config ────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
PORT = int(os.getenv("PORT", "8443"))

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


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
        ("help", "Bantuan"),
    ])
    logger.info("Bot commands set!")


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

    # Start bot
    if WEBHOOK_URL:
        # Webhook mode
        webhook_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
        logger.info(f"Starting webhook on port {PORT}, URL: {webhook_url}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH.lstrip("/"),
            webhook_url=webhook_url,
            drop_pending_updates=True,
        )
    else:
        # Polling mode (for local dev)
        logger.info("Starting in polling mode (no WEBHOOK_URL set)")
        application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
