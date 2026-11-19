# Shameer Rose Bot

## Features
- Local SQLite database (no online PostgreSQL / DATABASE_URL required).
- Owner-only `/backup` command sends a consistent SQLite backup to Telegram.
- Automatic local backup every 24 hours; keeps the newest 14 backup files.
- Existing bot commands and game data schema retained.

## Setup
1. Install Python 3.12.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN`. `GEMINI_API_KEY` is optional.
4. Run `python main.py`.

SQLite database defaults to `data/bot.sqlite3`; backups default to `backups/`.
On ephemeral hosting, download backups using `/backup` regularly because local files can be erased on restart/redeploy.

## Admin panels
- Telegram: send `/admin` in a private chat as a configured owner.
- Web: set `ADMIN_WEB_USERNAME`, a strong `ADMIN_WEB_PASSWORD`, and `WEB_ADMIN_PORT`; open `https://YOUR-HOST/admin`.
- Set `OWNER_IDS` to comma-separated numeric Telegram user IDs. This is recommended because usernames can change.
- Both panels use the same local SQLite database and support statistics, user lookup, balance add/set, 30-day premium grant/removal, ship overview, and downloadable backup.
- Web panel is disabled unless `ADMIN_WEB_PASSWORD` is configured. Use HTTPS at the hosting provider and keep the password private.
