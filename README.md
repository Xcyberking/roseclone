# CyberX Security Bot

A fresh Telegram group-moderation project. This repository does not use legacy Rosebot/Roseclone application code.

## Implemented in this starter
- Python 3.12+, Aiogram 3, FastAPI dashboard, SQLAlchemy async.
- SQLite development database and PostgreSQL URL support.
- Observed-member directory, join/leave events, welcome/goodbye message storage, group rules, CSV member export.
- Anti-flood, configurable anti-link switch, repeated-message scoring, suspicious phrase heuristics, hidden-format-character detection, blocked-domain/custom-phrase checks, sticker burst and media/forward/poll lock hooks.
- Warnings, warning counts/removal, community reports, moderation logs and owner statistics commands.
- Responsive blue/white dashboard: overview KPIs, groups, observed members, security history, customization, super-admin overview, JSON backup and CSV security reports.
- Behaviour-based threat score (low/medium/high/critical). It does not classify users from username or account age.
- Additional database tables for admins, group settings, custom filters, blocked domains/users, verification records, reports, subscriptions, bot settings and audit logs.
- Dockerfile, Compose file and a compile-check GitHub Actions workflow.

## Setup
1. Create a bot with Telegram's BotFather and add it to your group.
2. Give the bot the Telegram permissions needed for the moderation actions you enable.
3. Copy .env.example to .env, then set BOT_TOKEN, OWNER_TELEGRAM_ID, DASHBOARD_PASSWORD and a random SESSION_SECRET.
4. Install dependencies: pip install -r requirements.txt
5. Run: python -m app
6. Open http://localhost:8080 for the dashboard. Put it behind HTTPS before exposing it outside a trusted network.

## Commands
/start, /help, /security, /antiflood on|off, /antilink on|off, /welcome on|off, /warn (reply), /warnings (reply), /unwarn (reply), /members, /export, /rules, /report (reply), /stats, /groups, /health.

## Important implementation limits
This is a working foundation, not a claim that every item in a large feature specification is already production-complete. CAPTCHA challenge flow, full allowlist UI, configurable mute/kick escalation, scheduled-message management UI, encrypted field storage/key rotation, webhook deployment mode, automated restore/import workflow, Redis-backed distributed limits, and complete role-management screens still need dedicated implementation and integration tests. APScheduler and Redis dependencies are present for those follow-up modules; the current runtime uses in-process rate tracking.

Telegram Bot API does not let bots enumerate all historic group members. This app records only members it observes after installation or interaction. The Smart Security Engine is rule-based and explainable, not an AI classifier; review high-risk decisions before enabling automatic punitive actions.

## Privacy
See PRIVACY.md. Configure a retention policy and tell group members what the bot stores.
