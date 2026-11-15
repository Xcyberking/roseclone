import asyncio, os
import uvicorn
from aiogram import Bot
from app.config import BOT_TOKEN, WEB_HOST, WEB_PORT
from app.db import init_db
from app.bot import run_bot
from app.web import app
from app.services.scheduler_service import dispatch_due
from app.webhook import telegram_webhook, bot as webhook_bot
app.add_api_route("/telegram/webhook",telegram_webhook,methods=["POST"])
async def scheduled_loop(bot):
    while True:
        try: await dispatch_due(bot)
        except Exception: pass
        await asyncio.sleep(15)
async def main():
    await init_db()
    server=uvicorn.Server(uvicorn.Config(app,host=WEB_HOST,port=WEB_PORT,log_level="info"))
    if os.getenv("WEBHOOK_URL"):
        if not webhook_bot: raise RuntimeError("BOT_TOKEN is required for webhook mode")
        await webhook_bot.set_webhook(os.environ["WEBHOOK_URL"],secret_token=os.getenv("WEBHOOK_SECRET_TOKEN",""))
        await asyncio.gather(scheduled_loop(webhook_bot),server.serve())
    else:
        bot=Bot(BOT_TOKEN)
        await asyncio.gather(run_bot(),scheduled_loop(bot),server.serve())
if __name__=="__main__": asyncio.run(main())
