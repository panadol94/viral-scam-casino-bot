# Viral Scam Casino Bot 🎰🚨

Telegram bot untuk melaporkan casino online yang menipu. Laporan auto-post ke channel Telegram dengan grid collage screenshot.

## Features

- 📝 **Report System** — Step-by-step scam casino report
- 🖼️ **Auto Grid Collage** — Multiple screenshots combined into one image
- 📢 **Auto Channel Post** — Reports auto-posted to Telegram channel
- 🔍 **Search & Check** — Search by casino name or check link
- 📊 **Statistics** — Total reports & top scam casinos
- 🚫 **Ban System** — Owner can ban users from submitting reports

## Setup

1. Copy `.env.example` to `.env` and fill in your values:

   ```
   cp .env.example .env
   ```

2. Run with Docker Compose:

   ```
   docker-compose up -d
   ```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `CHANNEL_ID` | Telegram channel ID (e.g. -100xxxxxxxxxx) |
| `OWNER_ID` | Your Telegram user ID |
| `DATABASE_URL` | PostgreSQL connection string |
| `WEBHOOK_URL` | Public URL for webhook (leave empty for polling) |
| `WEBHOOK_PATH` | Webhook path (default: /webhook) |
| `PORT` | Webhook port (default: 8443) |

## Commands

### User Commands

- `/start` — Main menu
- `/report` — Submit a scam report
- `/search <name>` — Search casino by name
- `/check <link>` — Check if a link has been reported
- `/stats` — View statistics
- `/help` — Help

### Owner Commands

- `/ban <user_id> [reason]` — Ban a user
- `/unban <user_id>` — Unban a user
- `/banlist` — List banned users
- `/delete <report_id>` — Delete a report
