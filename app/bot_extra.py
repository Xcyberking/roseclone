from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from app.db import Session
from app.models import Group, Member, ModerationLog
from app.models_security import GroupSetting, UserReport
from app.config import OWNER_ID

def register_extra(dp):
    @dp.message(Command("rules"))
    async def rules(m:Message):
        async with Session() as s:
            g=await s.scalar(select(GroupSetting).where(GroupSetting.chat_id==m.chat.id))
        await m.answer(g.rules_text if g else "Group rules have not been configured.")

    @dp.message(Command("report"))
    async def report(m:Message):
        if not m.reply_to_message or not m.reply_to_message.from_user:
            return await m.answer("Reply to the message you want to report, then send /report [reason].")
        target=m.reply_to_message.from_user
        reason=(m.text or "").partition(" ")[2] or "Community report"
        async with Session() as s:
            s.add(UserReport(chat_id=m.chat.id,reporter_id=m.from_user.id,target_id=target.id,reason=reason[:1000]))
            await s.commit()
        await m.answer("Your report was submitted for admin review.")

    @dp.message(Command("stats"))
    async def stats(m:Message):
        if m.from_user.id!=OWNER_ID: return
        async with Session() as s:
            groups=await s.scalar(select(func.count()).select_from(Group))
            members=await s.scalar(select(func.count()).select_from(Member))
            actions=await s.scalar(select(func.count()).select_from(ModerationLog))
        await m.answer(f"CyberX stats\nGroups: {groups}\nObserved members: {members}\nSecurity actions: {actions}")

    @dp.message(Command("groups"))
    async def group_list(m:Message):
        if m.from_user.id!=OWNER_ID: return
        async with Session() as s:
            rows=(await s.scalars(select(Group).limit(50))).all()
        await m.answer("Connected groups:\n"+"\n".join(f"{x.title} · {x.chat_id}" for x in rows) if rows else "No groups observed yet.")

    @dp.message(Command("health"))
    async def health(m:Message):
        if m.from_user.id!=OWNER_ID: return
        await m.answer("Bot process is responding. Database connectivity is checked on each request.")
