import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN","")
OWNER_ID=int(os.getenv("OWNER_TELEGRAM_ID","0") or 0)
DASHBOARD_PASSWORD=os.getenv("DASHBOARD_PASSWORD","")
SESSION_SECRET=os.getenv("SESSION_SECRET","change-me")
DATABASE_URL=os.getenv("DATABASE_URL","sqlite+aiosqlite:///./data/cyberx.db")
REDIS_URL=os.getenv("REDIS_URL","")
WEB_HOST=os.getenv("WEB_HOST","0.0.0.0")
WEB_PORT=int(os.getenv("WEB_PORT","8080"))
