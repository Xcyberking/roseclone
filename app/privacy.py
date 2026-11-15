from sqlalchemy import delete
from app.db import Session
from app.models import Member, Warning, ModerationLog
async def delete_user_data(user_id:int, chat_id:int|None=None):
    """Delete stored member, warning and log records for a user."""
    async with Session() as s:
        for model in (Member,Warning,ModerationLog):
            stmt=delete(model).where(model.user_id==user_id)
            if chat_id is not None: stmt=stmt.where(model.chat_id==chat_id)
            await s.execute(stmt)
        await s.commit()
