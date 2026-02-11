"""Start and help command handlers."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes


WELCOME_TEXT = (
    "🚨 <b>Viral Scam Casino Bot</b> 🚨\n"
    "\n"
    "Selamat datang! Bot ini untuk <b>melaporkan casino online yang menipu</b>.\n"
    "\n"
    "Semua laporan akan dipaparkan secara automatik di channel kami sebagai amaran kepada orang ramai.\n"
    "\n"
    "📌 <b>Arahan:</b>\n"
    "• /report — Buat laporan baru\n"
    "• /search — Cari casino dalam database\n"
    "• /check — Semak link casino\n"
    "• /stats — Statistik laporan\n"
    "• /help — Bantuan\n"
)

HELP_TEXT = (
    "📖 <b>Cara Guna Bot</b>\n"
    "\n"
    "1️⃣ Tekan /report untuk mula buat laporan\n"
    "2️⃣ Masukkan nama casino, link, jumlah rugi, dan cerita\n"
    "3️⃣ Hantar screenshot bukti (boleh banyak)\n"
    "4️⃣ Confirm dan laporan akan dipost ke channel\n"
    "\n"
    "🔍 <b>Cari Laporan:</b>\n"
    "• <code>/search nama_casino</code> — Cari by nama\n"
    "• <code>/check link_casino</code> — Semak link\n"
    "• <code>/stats</code> — Lihat statistik\n"
    "\n"
    "⚠️ Sila hantar laporan yang sahih sahaja. Akaun yang menyalahgunakan bot akan di-ban."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    keyboard = [
        [InlineKeyboardButton("📝 Buat Laporan", callback_data="start_report")],
        [
            InlineKeyboardButton("🔍 Cari Casino", callback_data="start_search"),
            InlineKeyboardButton("📊 Statistik", callback_data="start_stats"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks from /start menu."""
    query = update.callback_query
    await query.answer()

    if query.data == "start_report":
        await query.message.reply_text(
            "📝 Tekan /report untuk mula buat laporan scam casino.",
            parse_mode="HTML",
        )
    elif query.data == "start_search":
        await query.message.reply_text(
            "🔍 Guna: <code>/search nama_casino</code>\n"
            "Contoh: <code>/search mega888</code>",
            parse_mode="HTML",
        )
    elif query.data == "start_stats":
        # Trigger stats directly
        from bot.handlers.search import stats_command
        await stats_command(update, context)


def get_start_handlers() -> list:
    """Return handlers for start module."""
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CallbackQueryHandler(button_callback, pattern=r"^start_"),
    ]
