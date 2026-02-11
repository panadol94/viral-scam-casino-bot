"""Broadcast handler — owner-only, forward message to all tracked chats."""

import asyncio
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Forbidden, BadRequest, TimedOut, NetworkError
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.database import deactivate_chat, get_all_active_chats

logger = logging.getLogger(__name__)

OWNER_ID = int(os.getenv("OWNER_ID", "0"))


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /broadcast — Reply to any message with this command to broadcast it.
    Owner only.
    """
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 Arahan ini hanya untuk owner.")
        return

    # Must be a reply to a message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "📢 <b>Cara guna /broadcast:</b>\n\n"
            "1️⃣ Hantar mesej yang nak broadcast (text/foto/video)\n"
            "2️⃣ Reply mesej tu dengan <code>/broadcast</code>\n\n"
            "Bot akan forward mesej tu ke semua user, group, dan channel.",
            parse_mode="HTML",
        )
        return

    # Get active chats count
    chats = await get_all_active_chats()
    if not chats:
        await update.message.reply_text("❌ Tiada chat aktif dalam database.")
        return

    # Count by type
    private_count = sum(1 for c in chats if c.chat_type == "private")
    group_count = sum(1 for c in chats if c.chat_type in ("group", "supergroup"))
    channel_count = sum(1 for c in chats if c.chat_type == "channel")

    # Store the message to broadcast in context
    context.user_data["broadcast_msg_id"] = update.message.reply_to_message.message_id
    context.user_data["broadcast_chat_id"] = update.message.chat_id

    keyboard = [
        [
            InlineKeyboardButton("✅ Ya, Broadcast!", callback_data="broadcast_confirm"),
            InlineKeyboardButton("❌ Batal", callback_data="broadcast_cancel"),
        ]
    ]

    await update.message.reply_text(
        f"📢 <b>Confirm Broadcast</b>\n\n"
        f"Mesej akan dihantar ke:\n"
        f"👤 Users: <b>{private_count}</b>\n"
        f"👥 Groups: <b>{group_count}</b>\n"
        f"📣 Channels: <b>{channel_count}</b>\n"
        f"📊 Jumlah: <b>{len(chats)}</b>\n\n"
        f"Teruskan?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def broadcast_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle broadcast confirmation."""
    query = update.callback_query
    await query.answer()

    if not _is_owner(query.from_user.id):
        return

    msg_id = context.user_data.get("broadcast_msg_id")
    from_chat_id = context.user_data.get("broadcast_chat_id")

    if not msg_id or not from_chat_id:
        await query.edit_message_text("❌ Sesi broadcast tamat. Sila cuba semula.")
        return

    # Update message to show progress
    await query.edit_message_text("📢 Broadcasting... Sila tunggu ⏳")

    chats = await get_all_active_chats()
    success = 0
    failed = 0
    blocked = 0

    for chat in chats:
        try:
            await context.bot.copy_message(
                chat_id=chat.chat_id,
                from_chat_id=from_chat_id,
                message_id=msg_id,
            )
            success += 1
            # Small delay to avoid flood limits
            await asyncio.sleep(0.05)
        except Forbidden:
            # Bot blocked or kicked
            await deactivate_chat(chat.chat_id)
            blocked += 1
        except (BadRequest, TimedOut, NetworkError) as e:
            logger.warning(f"Broadcast fail for {chat.chat_id}: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast unexpected error for {chat.chat_id}: {e}")
            failed += 1

    # Clean up context
    context.user_data.pop("broadcast_msg_id", None)
    context.user_data.pop("broadcast_chat_id", None)

    # Send summary
    await query.edit_message_text(
        f"📢 <b>Broadcast Selesai!</b>\n\n"
        f"✅ Berjaya: <b>{success}</b>\n"
        f"🚫 Blocked/Kicked: <b>{blocked}</b>\n"
        f"❌ Gagal: <b>{failed}</b>\n"
        f"📊 Jumlah: <b>{success + failed + blocked}</b>",
        parse_mode="HTML",
    )
    logger.info(f"Broadcast done: {success} ok, {blocked} blocked, {failed} failed")


async def broadcast_cancel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle broadcast cancellation."""
    query = update.callback_query
    await query.answer()

    if not _is_owner(query.from_user.id):
        return

    context.user_data.pop("broadcast_msg_id", None)
    context.user_data.pop("broadcast_chat_id", None)

    await query.edit_message_text("❌ Broadcast dibatalkan.")


def get_broadcast_handlers() -> list:
    """Return handlers for broadcast module."""
    return [
        CommandHandler("broadcast", broadcast_command),
        CallbackQueryHandler(broadcast_confirm_callback, pattern=r"^broadcast_confirm$"),
        CallbackQueryHandler(broadcast_cancel_callback, pattern=r"^broadcast_cancel$"),
    ]
