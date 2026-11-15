# CyberX Security Bot Privacy Notes

- The bot stores Telegram user IDs, usernames, display names, observed membership status and timestamps for groups where it is installed.
- It stores moderation events, warnings, reports and group configuration.
- It does not collect phone numbers, private chat histories, passwords or message contents as a general archive.
- Message text is inspected transiently for configured moderation rules; moderation logs store a short reason, not the full deleted message.
- Group administrators should disclose the bot's use to members and configure retention to meet their local requirements.
- Members can ask the group owner to remove records. A developer deletion helper is included in app/privacy.py.
- Telegram bots cannot retrieve a complete historic member list. The member directory contains users observed after the bot is added or users who interact with it.
- Secure the dashboard with a strong password and SESSION_SECRET, use HTTPS, restrict network access and protect database backups.
