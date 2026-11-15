"""Optional Telegram webhook runner. Configure WEBHOOK_URL and WEBHOOK_SECRET_TOKEN."""
import os
from fastapi import Request, HTTPException
from aiogram.types import Update
from app.bot import dp
from app.config import BOT_TOKEN
from aiogram import Bot
bot=Bot(BOT_TOKEN) if BOT_TOKEN else None
async def telegram_webhook(request:Request):
    secret=os.getenv("WEBHOOK_SECRET_TOKEN","")
    supplied=request.headers.get("X-Telegram-Bot-Api-Secret-Token","")
    if not secret or not supplied or not __import__("hmac").compare_digest(secret,supplied):
        raise HTTPException(403,"Invalid webhook secret")
    if not bot: raise HTTPException(503,"Bot token missing")
    payload=await request.json()
    update=Update.model_validate(payload,context={"bot":bot})
    await dp.feed_update(bot,update)
    return {"ok":True}
