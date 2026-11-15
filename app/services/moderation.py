from aiogram import Bot
from aiogram.types import ChatPermissions
from datetime import datetime, timedelta, timezone
async def restrict_user(bot:Bot,chat_id:int,user_id:int,minutes:int=10):
    until=datetime.now(timezone.utc)+timedelta(minutes=max(1,min(minutes,10080)))
    return await bot.restrict_chat_member(chat_id,user_id,permissions=ChatPermissions(can_send_messages=False),until_date=until)
async def restore_user(bot:Bot,chat_id:int,user_id:int):
    return await bot.restrict_chat_member(chat_id,user_id,permissions=ChatPermissions(can_send_messages=True,can_send_audios=True,can_send_documents=True,can_send_photos=True,can_send_videos=True,can_send_video_notes=True,can_send_voice_notes=True,can_send_polls=True,can_send_other_messages=True,can_add_web_page_previews=True))
