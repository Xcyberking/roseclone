import asyncio
from aiogram import Bot
from app.config import BOT_TOKEN, WEB_HOST, WEB_PORT
from app.db import init_db
from app.bot import run_bot
from app.web import app
import uvicorn

async def main():
    await init_db()
    config=uvicorn.Config(app,host=WEB_HOST,port=WEB_PORT,log_level="info")
    server=uvicorn.Server(config)
    await asyncio.gather(run_bot(),server.serve())

if __name__=="__main__":
    asyncio.run(main())
