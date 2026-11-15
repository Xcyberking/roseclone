from datetime import datetime, timezone
from sqlalchemy import select
from app.db import Session
from app.models_advanced import ScheduledMessage
async def dispatch_due(bot):
    now=datetime.now(timezone.utc)
    async with Session() as s:
        rows=(await s.scalars(select(ScheduledMessage).where(ScheduledMessage.enabled==True,ScheduledMessage.run_at<=now,ScheduledMessage.sent_at.is_(None)).limit(100))).all()
        jobs=[(x.id,x.chat_id,x.text) for x in rows]
    for job_id,chat_id,text in jobs:
        try:
            await bot.send_message(chat_id,text)
            async with Session() as s:
                row=await s.get(ScheduledMessage,job_id)
                if row: row.sent_at=now; await s.commit()
        except Exception:
            # Keep unsent for retry on next scheduler tick.
            continue
