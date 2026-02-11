"""Auto-post reports to Telegram channel."""

import io
import logging
import os
from datetime import timezone

from telegram import Bot

from bot.database import Report, update_report_channel_msg
from bot.services.collage import create_grid_collage

logger = logging.getLogger(__name__)

CHANNEL_ID = os.getenv("CHANNEL_ID", "")


def _format_report_caption(report: Report) -> str:
    """Build the formatted channel post caption."""
    lines = [
        f"🚨 <b>SCAM REPORT #{report.id:04d}</b>",
        "",
        f"🎰 <b>Casino:</b> {_escape(report.casino_name)}",
    ]

    if report.casino_link:
        lines.append(f"🔗 <b>Link:</b> {_escape(report.casino_link)}")

    if report.amount_lost:
        lines.append(f"💰 <b>Rugi:</b> RM {_escape(report.amount_lost)}")

    lines.extend([
        "",
        f"📝 <b>Keterangan:</b>",
        _escape(report.description),
        "",
    ])

    # Reporter attribution
    if report.username:
        lines.append(f"👤 <b>Report oleh:</b> @{report.username}")
    elif report.first_name:
        lines.append(f"👤 <b>Report oleh:</b> {_escape(report.first_name)}")
    else:
        lines.append(f"👤 <b>Report oleh:</b> User {report.user_id}")

    if report.created_at:
        local_time = report.created_at.astimezone(timezone.utc)
        lines.append(f"📅 <b>Tarikh:</b> {local_time.strftime('%d/%m/%Y %H:%M UTC')}")

    lines.extend([
        "",
        "#ScamCasino #Report #Scam",
    ])

    return "\n".join(lines)


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def post_report_to_channel(bot: Bot, report: Report) -> None:
    """Post a report to the configured Telegram channel."""
    caption = _format_report_caption(report)
    screenshot_ids = report.get_screenshots()

    try:
        if screenshot_ids:
            # Download all screenshots and create grid collage
            image_bytes_list: list[bytes] = []
            for file_id in screenshot_ids:
                try:
                    file = await bot.get_file(file_id)
                    buf = io.BytesIO()
                    await file.download_to_memory(buf)
                    image_bytes_list.append(buf.getvalue())
                except Exception as e:
                    logger.warning(f"Failed to download screenshot {file_id}: {e}")

            if image_bytes_list:
                # Generate grid collage
                grid_bytes = create_grid_collage(image_bytes_list)
                grid_file = io.BytesIO(grid_bytes)
                grid_file.name = "scam_report.jpg"

                msg = await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=grid_file,
                    caption=caption,
                    parse_mode="HTML",
                )
                await update_report_channel_msg(report.id, msg.message_id)
                logger.info(f"Report #{report.id} posted to channel with grid collage")
                return

        # No screenshots — send text only
        msg = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=caption,
            parse_mode="HTML",
        )
        await update_report_channel_msg(report.id, msg.message_id)
        logger.info(f"Report #{report.id} posted to channel (text only)")

    except Exception as e:
        logger.error(f"Failed to post report #{report.id} to channel: {e}")
        raise
