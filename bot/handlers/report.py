"""Report conversation handler — step-by-step scam report submission."""

import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.database import create_report, is_banned
from bot.services.channel import post_report_to_channel
from bot.services.membership import NOT_JOINED_TEXT, get_join_keyboard, is_member_of_all

logger = logging.getLogger(__name__)

# Conversation states
CASINO_NAME, CASINO_LINK, AMOUNT_LOST, DESCRIPTION, SCREENSHOTS, CONFIRM = range(6)


async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the report conversation."""
    user = update.effective_user

    # Check membership first
    if not await is_member_of_all(context.bot, user.id):
        await update.message.reply_text(
            NOT_JOINED_TEXT,
            parse_mode="HTML",
            reply_markup=get_join_keyboard(),
        )
        return ConversationHandler.END

    # Check ban
    if await is_banned(user.id):
        await update.message.reply_text(
            "🚫 Akaun anda telah di-ban dari menghantar laporan.",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["screenshots"] = []

    await update.message.reply_text(
        "📝 <b>Laporan Scam Casino Baru</b>\n\n"
        "Sila masukkan <b>nama casino</b> yang menipu.\n\n"
        "Contoh: <i>Mega888, 918Kiss, Lucky Palace</i>\n\n"
        "Tekan /cancel untuk batal.",
        parse_mode="HTML",
    )
    return CASINO_NAME


async def receive_casino_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive casino name."""
    context.user_data["casino_name"] = update.message.text.strip()

    await update.message.reply_text(
        "🔗 Masukkan <b>link/URL casino</b> tersebut.\n\n"
        "Contoh: <i>www.mega888.com</i>\n\n"
        "Tekan /skip untuk langkau.",
        parse_mode="HTML",
    )
    return CASINO_LINK


async def receive_casino_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive casino link."""
    context.user_data["casino_link"] = update.message.text.strip()
    return await _ask_amount(update)


async def skip_casino_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip casino link."""
    context.user_data["casino_link"] = None
    return await _ask_amount(update)


async def _ask_amount(update: Update) -> int:
    await update.message.reply_text(
        "💰 Berapa jumlah <b>kerugian (RM)</b>?\n\n"
        "Contoh: <i>500</i>, <i>1000</i>, <i>50000</i>\n\n"
        "Tekan /skip untuk langkau.",
        parse_mode="HTML",
    )
    return AMOUNT_LOST


async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive amount lost."""
    context.user_data["amount_lost"] = update.message.text.strip()
    return await _ask_description(update)


async def skip_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip amount."""
    context.user_data["amount_lost"] = None
    return await _ask_description(update)


async def _ask_description(update: Update) -> int:
    await update.message.reply_text(
        "📝 Ceritakan <b>apa yang berlaku</b>.\n\n"
        "Terangkan bagaimana casino tersebut menipu anda.\n\n"
        "<i>Contoh: Saya deposit RM500 tapi bila menang dan nak withdraw, "
        "akaun terus kena block. Customer service tak respond.</i>",
        parse_mode="HTML",
    )
    return DESCRIPTION


async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive description."""
    context.user_data["description"] = update.message.text.strip()

    await update.message.reply_text(
        "📸 Hantar <b>screenshot bukti</b>.\n\n"
        "Boleh hantar banyak gambar satu-satu. "
        "Bila dah habis, tekan /done.\n\n"
        "Tekan /skip kalau tiada screenshot.",
        parse_mode="HTML",
    )
    return SCREENSHOTS


async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive a screenshot photo."""
    if update.message.photo:
        # Get highest resolution photo
        photo = update.message.photo[-1]
        context.user_data["screenshots"].append(photo.file_id)

        count = len(context.user_data["screenshots"])
        await update.message.reply_text(
            f"✅ Screenshot #{count} diterima!\n\n"
            f"Hantar lagi atau tekan /done bila selesai.\n"
            f"(Max 9 screenshot untuk grid yang cantik)",
            parse_mode="HTML",
        )

        # Auto-done if 9 screenshots
        if count >= 9:
            return await _show_preview(update, context)

    return SCREENSHOTS


async def done_screenshots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User is done sending screenshots."""
    return await _show_preview(update, context)


async def skip_screenshots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip screenshots."""
    context.user_data["screenshots"] = []
    return await _show_preview(update, context)


async def _show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show report preview for confirmation."""
    data = context.user_data
    ss_count = len(data.get("screenshots", []))

    preview = (
        "📋 <b>Preview Laporan:</b>\n\n"
        f"🎰 <b>Casino:</b> {data['casino_name']}\n"
    )
    if data.get("casino_link"):
        preview += f"🔗 <b>Link:</b> {data['casino_link']}\n"
    if data.get("amount_lost"):
        preview += f"💰 <b>Rugi:</b> RM {data['amount_lost']}\n"

    preview += (
        f"\n📝 <b>Keterangan:</b>\n{data['description']}\n"
        f"\n📸 <b>Screenshot:</b> {ss_count} gambar\n"
        f"\n<b>Sahkan untuk hantar?</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Hantar", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Batal", callback_data="confirm_no"),
        ]
    ]

    await update.message.reply_text(
        preview,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CONFIRM


async def confirm_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirm/cancel buttons."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("❌ Laporan dibatalkan.")
        context.user_data.clear()
        return ConversationHandler.END

    # Confirmed — save report
    user = update.effective_user
    data = context.user_data

    await query.edit_message_text("⏳ Menghantar laporan...")

    try:
        report = await create_report(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            casino_name=data["casino_name"],
            casino_link=data.get("casino_link"),
            amount_lost=data.get("amount_lost"),
            description=data["description"],
            screenshot_ids=data.get("screenshots", []),
        )

        # Post to channel
        await post_report_to_channel(context.bot, report)

        await query.message.reply_text(
            f"✅ <b>Laporan #{report.id:04d} berjaya dihantar!</b>\n\n"
            "Laporan anda telah dipaparkan di channel. "
            "Terima kasih kerana membantu komuniti! 🙏",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Failed to submit report: {e}")
        await query.message.reply_text(
            "❌ Maaf, ada masalah teknikal. Sila cuba lagi.",
            parse_mode="HTML",
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the report conversation."""
    context.user_data.clear()
    await update.message.reply_text("❌ Laporan dibatalkan.", parse_mode="HTML")
    return ConversationHandler.END


def get_report_handler() -> ConversationHandler:
    """Return the ConversationHandler for reports."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("report", report_start),
        ],
        states={
            CASINO_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_casino_name),
            ],
            CASINO_LINK: [
                CommandHandler("skip", skip_casino_link),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_casino_link),
            ],
            AMOUNT_LOST: [
                CommandHandler("skip", skip_amount),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount),
            ],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
            ],
            SCREENSHOTS: [
                CommandHandler("done", done_screenshots),
                CommandHandler("skip", skip_screenshots),
                MessageHandler(filters.PHOTO, receive_screenshot),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_report, pattern=r"^confirm_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_report),
        ],
        per_user=True,
        per_chat=True,
    )
