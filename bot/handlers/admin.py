"""Admin/Owner commands — ban, unban, delete reports."""

import logging
import os

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.database import (
    ban_user,
    delete_report,
    get_banned_list,
    get_report_by_id,
    unban_user,
)

logger = logging.getLogger(__name__)

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "")


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ban a user from submitting reports. Usage: /ban <user_id> [reason]"""
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 Arahan ini hanya untuk owner.")
        return

    if not context.args:
        await update.message.reply_text(
            "Guna: <code>/ban user_id alasan</code>\n"
            "Contoh: <code>/ban 123456789 spam fake report</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID mesti nombor.")
        return

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else None

    await ban_user(target_id, update.effective_user.id, reason)

    reason_text = f"\n📝 Sebab: {reason}" if reason else ""
    await update.message.reply_text(
        f"✅ User <code>{target_id}</code> telah di-ban.{reason_text}",
        parse_mode="HTML",
    )
    logger.info(f"User {target_id} banned by owner. Reason: {reason}")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unban a user. Usage: /unban <user_id>"""
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 Arahan ini hanya untuk owner.")
        return

    if not context.args:
        await update.message.reply_text(
            "Guna: <code>/unban user_id</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID mesti nombor.")
        return

    success = await unban_user(target_id)
    if success:
        await update.message.reply_text(
            f"✅ User <code>{target_id}</code> telah di-unban.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            f"❌ User <code>{target_id}</code> tiada dalam senarai ban.",
            parse_mode="HTML",
        )


async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all banned users."""
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 Arahan ini hanya untuk owner.")
        return

    banned = await get_banned_list()

    if not banned:
        await update.message.reply_text("✅ Tiada user yang di-ban.")
        return

    lines = ["🚫 <b>Senarai User Banned:</b>\n"]
    for b in banned:
        reason = f" — {b.reason}" if b.reason else ""
        date = b.banned_at.strftime("%d/%m/%Y") if b.banned_at else "N/A"
        lines.append(f"• <code>{b.user_id}</code>{reason} | 📅 {date}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a report. Usage: /delete <report_id>"""
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 Arahan ini hanya untuk owner.")
        return

    if not context.args:
        await update.message.reply_text(
            "Guna: <code>/delete report_id</code>",
            parse_mode="HTML",
        )
        return

    try:
        report_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Report ID mesti nombor.")
        return

    # Get report first to delete channel message
    report = await get_report_by_id(report_id)
    if not report:
        await update.message.reply_text(f"❌ Report #{report_id} tidak ditemui.")
        return

    # Delete from channel if posted
    if report.channel_message_id and CHANNEL_ID:
        try:
            await context.bot.delete_message(
                chat_id=CHANNEL_ID,
                message_id=report.channel_message_id,
            )
        except Exception as e:
            logger.warning(f"Failed to delete channel message: {e}")

    # Delete from database
    await delete_report(report_id)
    await update.message.reply_text(
        f"✅ Report #{report_id:04d} (<b>{report.casino_name}</b>) telah dipadam.",
        parse_mode="HTML",
    )
    logger.info(f"Report #{report_id} deleted by owner")


def get_admin_handlers() -> list:
    """Return handlers for admin module."""
    return [
        CommandHandler("ban", ban_command),
        CommandHandler("unban", unban_command),
        CommandHandler("banlist", banlist_command),
        CommandHandler("delete", delete_command),
    ]
