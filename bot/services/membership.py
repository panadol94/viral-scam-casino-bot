"""Membership check — force join channel + group before using bot."""

import logging
import os

from telegram import Bot, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

CHANNEL_ID = os.getenv("CHANNEL_ID", "")
GROUP_ID = os.getenv("GROUP_ID", "")


async def check_membership(bot: Bot, user_id: int) -> dict:
    """
    Check if user is a member of both channel and group.
    Returns dict with 'channel' and 'group' booleans.
    """
    result = {"channel": False, "group": False}

    # Check channel membership
    if CHANNEL_ID:
        try:
            member = await bot.get_chat_member(chat_id=int(CHANNEL_ID), user_id=user_id)
            result["channel"] = member.status in (
                ChatMember.MEMBER,
                ChatMember.ADMINISTRATOR,
                ChatMember.OWNER,
            )
        except Exception as e:
            logger.warning(f"Failed to check channel membership for {user_id}: {e}")

    # Check group membership
    if GROUP_ID:
        try:
            member = await bot.get_chat_member(chat_id=int(GROUP_ID), user_id=user_id)
            result["group"] = member.status in (
                ChatMember.MEMBER,
                ChatMember.ADMINISTRATOR,
                ChatMember.OWNER,
                ChatMember.RESTRICTED,
            )
        except Exception as e:
            logger.warning(f"Failed to check group membership for {user_id}: {e}")

    return result


async def is_member_of_all(bot: Bot, user_id: int) -> bool:
    """Check if user is member of BOTH channel and group."""
    membership = await check_membership(bot, user_id)
    return membership["channel"] and membership["group"]


def get_join_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with join buttons + verify button."""
    buttons = []

    if CHANNEL_ID:
        # Convert -100xxx to public link format or use invite link
        buttons.append(
            InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/c/{str(CHANNEL_ID).replace('-100', '')}")
        )

    if GROUP_ID:
        buttons.append(
            InlineKeyboardButton("👥 Join Group", url=f"https://t.me/c/{str(GROUP_ID).replace('-100', '')}")
        )

    keyboard = []
    if buttons:
        keyboard.append(buttons)
    keyboard.append([InlineKeyboardButton("✅ Saya Sudah Join", callback_data="verify_join")])

    return InlineKeyboardMarkup(keyboard)


NOT_JOINED_TEXT = (
    "⚠️ <b>Anda perlu join channel dan group kami terlebih dahulu!</b>\n\n"
    "Sila join kedua-dua di bawah, kemudian tekan '✅ Saya Sudah Join'."
)
