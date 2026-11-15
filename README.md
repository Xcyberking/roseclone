# CyberX Security Bot

Fresh project for Telegram group safety. No legacy Roseclone/Rosebot code is used.

## Features
- Aiogram 3 bot: join/member observation, welcome messages, admin commands, flood protection, optional link moderation, warnings and audit logs.
- Multi-group settings stored in SQLite (default) or PostgreSQL (via DATABASE_URL).
- Web dashboard with overview, group controls, member directory, moderation logs, customization, super-admin tools, JSON backup/export and CSV member export.
- Roles: owner (OWNER_TELEGRAM_ID), dashboard password login, group administrators verified through Telegram.
- Privacy-aware: only records users the bot actually observes; Telegram does not expose a complete historic member list. No phone numbers or private message collection.

## Run
1. Create a Telegram bot with BotFather and add it to your group. Give it admin rights needed for deleting messages/restricting members.
2. Copy .env.example to .env and set BOT_TOKEN, OWNER_TELEGRAM_ID and DASHBOARD_PASSWORD.
3. Install Python 3.11+: `pip install -r requirements.txt`
4. Start: `python -m app`
5. Dashboard: `http://localhost:8080`

For production set a strong DASHBOARD_PASSWORD, SESSION_SECRET and DATABASE_URL. Set WEB_HOST=0.0.0.0 behind HTTPS reverse proxy. Docker Compose includes PostgreSQL and Redis; Redis is optional in this starter.

## Commands
/start, /help, /security, /antiflood on|off, /antilink on|off, /welcome on|off, /warn, /warnings, /unwarn, /members, /export

Only Telegram group admins can use moderation commands. The super-admin dashboard is protected by the configured dashboard password. Do not expose it publicly without HTTPS and a strong password.
