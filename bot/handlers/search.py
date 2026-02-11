"""Search, check, and stats handlers."""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.database import check_link, get_stats, search_reports


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search reports by casino name."""
    if not context.args:
        await update.message.reply_text(
            "🔍 Guna: <code>/search nama_casino</code>\n"
            "Contoh: <code>/search hgbt.bet</code>",
            parse_mode="HTML",
        )
        return

    query = " ".join(context.args)
    reports = await search_reports(query)

    if not reports:
        await update.message.reply_text(
            f"❌ Tiada laporan ditemui untuk <b>{query}</b>.",
            parse_mode="HTML",
        )
        return

    lines = [f"🔍 <b>Hasil Carian: {query}</b>\n"]
    for r in reports:
        link_info = f" | 🔗 {r.casino_link}" if r.casino_link else ""
        amount_info = f" | 💰 RM{r.amount_lost}" if r.amount_lost else ""
        date = r.created_at.strftime("%d/%m/%Y") if r.created_at else "N/A"
        lines.append(
            f"#{r.id:04d} — <b>{r.casino_name}</b>{link_info}{amount_info} | 📅 {date}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if a link has been reported."""
    if not context.args:
        await update.message.reply_text(
            "🔗 Guna: <code>/check link_casino</code>\n"
            "Contoh: <code>/check hgbt.bet</code>",
            parse_mode="HTML",
        )
        return

    link = " ".join(context.args)
    reports = await check_link(link)

    if not reports:
        await update.message.reply_text(
            f"✅ Link <b>{link}</b> belum ada dalam database laporan.",
            parse_mode="HTML",
        )
        return

    lines = [f"⚠️ <b>Link {link} dah kena report {len(reports)} kali!</b>\n"]
    for r in reports:
        date = r.created_at.strftime("%d/%m/%Y") if r.created_at else "N/A"
        lines.append(f"#{r.id:04d} — <b>{r.casino_name}</b> | 📅 {date}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show report statistics."""
    stats = await get_stats()

    text = (
        "📊 <b>Statistik Laporan Scam Casino</b>\n\n"
        f"📋 <b>Jumlah Laporan:</b> {stats['total']}\n"
    )

    if stats["top_casinos"]:
        text += "\n🏆 <b>Top 5 Casino Paling Banyak Report:</b>\n"
        for i, (name, count) in enumerate(stats["top_casinos"], 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i - 1]
            text += f"{medal} <b>{name}</b> — {count} laporan\n"
    else:
        text += "\nBelum ada laporan lagi."

    # Handle both message and callback query
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


def get_search_handlers() -> list:
    """Return handlers for search module."""
    return [
        CommandHandler("search", search_command),
        CommandHandler("check", check_command),
        CommandHandler("stats", stats_command),
    ]
