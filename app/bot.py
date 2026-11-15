import asyncio, time, csv, io
from collections import defaultdict, deque
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ChatMemberUpdated, BufferedInputFile
from sqlalchemy import select, func, delete
from app.config import BOT_TOKEN, OWNER_ID
from app.db import Session
from app.models import Group, Member, ModerationLog, Warning
from app.services.security_engine import analyze_message, should_auto_moderate

dp=Dispatcher()
from app.bot_extra import register_extra
register_extra(dp)
recent=defaultdict(deque)
def is_owner(uid): return uid == OWNER_ID and OWNER_ID != 0
async def is_admin(bot, chat_id, uid):
    if is_owner(uid): return True
    try:
        m=await bot.get_chat_member(chat_id,uid)
        return m.status in ("administrator","creator")
    except Exception: return False
async def observe(chat_id,user,status="seen"):
    if user.is_bot: return
    async with Session() as s:
        row=await s.scalar(select(Member).where(Member.chat_id==chat_id,Member.user_id==user.id))
        if row:
            row.username=user.username; row.full_name=user.full_name; row.status=status; row.last_seen=datetime.now(timezone.utc)
        else:
            s.add(Member(chat_id=chat_id,user_id=user.id,username=user.username,full_name=user.full_name,status=status))
        await s.commit()
async def get_group(chat):
    async with Session() as s:
        g=await s.scalar(select(Group).where(Group.chat_id==chat.id))
        if not g:
            g=Group(chat_id=chat.id,title=chat.title or str(chat.id)); s.add(g); await s.commit(); await s.refresh(g)
        elif g.title != (chat.title or str(chat.id)):
            g.title=chat.title or str(chat.id); await s.commit()
        return {k:getattr(g,k) for k in ("welcome_enabled","welcome_text","antiflood_enabled","antilink_enabled","max_messages","window_seconds")}
async def log(chat,user,action,reason=""):
    async with Session() as s:
        s.add(ModerationLog(chat_id=chat,user_id=user,action=action,reason=reason)); await s.commit()
@dp.message(CommandStart())
async def start(m:Message):
    await m.answer("🛡️ CyberX Security Bot is online. Add me to a group as admin and use /help.")
@dp.message(Command("help"))
async def help_cmd(m:Message):
    await m.answer("/security — group status
/antiflood on|off
/antilink on|off
/welcome on|off
/warn (reply) [reason]
/warnings (reply)
/unwarn (reply)
/members — observed member count
/export — CSV of observed members")
@dp.my_chat_member()
async def added(ev:ChatMemberUpdated):
    if ev.chat.type in ("group","supergroup"):
        await get_group(ev.chat)
@dp.chat_member()
async def member_update(ev:ChatMemberUpdated):
    if ev.chat.type not in ("group","supergroup"): return
    u=ev.new_chat_member.user
    status="left" if ev.new_chat_member.status in ("left","kicked") else "member"
    await observe(ev.chat.id,u,status)
    if status=="member" and ev.old_chat_member.status in ("left","kicked"):
        cfg=await get_group(ev.chat)
        if cfg["welcome_enabled"]:
            try: await ev.bot.send_message(ev.chat.id,cfg["welcome_text"].replace("{name}",u.full_name).replace("{id}",str(u.id)))
            except Exception: pass
@dp.message(F.chat.type.in_({"group","supergroup"}))
async def group_messages(m:Message):
    if not m.from_user: return
    await observe(m.chat.id,m.from_user)
    if await is_admin(m.bot,m.chat.id,m.from_user.id): return
    cfg=await get_group(m.chat)
    if cfg["antilink_enabled"] and m.text and ("http://" in m.text.lower() or "https://" in m.text.lower() or "t.me/" in m.text.lower()):
        try:
            await m.delete(); await log(m.chat.id,m.from_user.id,"delete_link","Link policy")
        except Exception: pass
        return
    if cfg["antiflood_enabled"]:
        key=(m.chat.id,m.from_user.id); q=recent[key]; now=time.monotonic(); q.append(now)
        while q and now-q[0]>cfg["window_seconds"]: q.popleft()
        if len(q)>cfg["max_messages"]:
            try:
                await m.delete(); await log(m.chat.id,m.from_user.id,"delete_flood","Flood threshold")
            except Exception: pass
@dp.message(Command("security"))
async def security(m:Message):
    if not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    c=await get_group(m.chat)
    await m.answer(f"🛡️ Security for {m.chat.title}
Anti-flood: {c['antiflood_enabled']}
Anti-link: {c['antilink_enabled']}
Welcome: {c['welcome_enabled']}")
async def set_flag(m,field,value):
    if not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    async with Session() as s:
        g=await s.scalar(select(Group).where(Group.chat_id==m.chat.id))
        if not g: g=Group(chat_id=m.chat.id,title=m.chat.title or "Group"); s.add(g)
        setattr(g,field,value=="on"); await s.commit()
    await m.answer(f"{field.replace('_',' ').title()} {value}.")
@dp.message(Command("antiflood"))
async def antiflood(m:Message):
    a=(m.text or "").split()
    if len(a)==2 and a[1] in ("on","off"): await set_flag(m,"antiflood_enabled",a[1])
    else: await m.answer("Usage: /antiflood on|off")
@dp.message(Command("antilink"))
async def antilink(m:Message):
    a=(m.text or "").split()
    if len(a)==2 and a[1] in ("on","off"): await set_flag(m,"antilink_enabled",a[1])
    else: await m.answer("Usage: /antilink on|off")
@dp.message(Command("welcome"))
async def welcome(m:Message):
    a=(m.text or "").split()
    if len(a)==2 and a[1] in ("on","off"): await set_flag(m,"welcome_enabled",a[1])
    else: await m.answer("Usage: /welcome on|off")
@dp.message(Command("warn"))
async def warn(m:Message):
    if not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.from_user: return await m.answer("Reply to a member's message: /warn [reason]")
    target=m.reply_to_message.from_user; reason=(m.text or "").partition(" ")[2] or "No reason provided"
    async with Session() as s:
        s.add(Warning(chat_id=m.chat.id,user_id=target.id,reason=reason)); s.add(ModerationLog(chat_id=m.chat.id,user_id=target.id,action="warn",reason=reason)); await s.commit()
        count=await s.scalar(select(func.count()).select_from(Warning).where(Warning.chat_id==m.chat.id,Warning.user_id==target.id))
    await m.answer(f"⚠️ Warning recorded for {target.full_name}. Total: {count}")
@dp.message(Command("warnings"))
async def warnings(m:Message):
    if not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.from_user: return await m.answer("Reply to a member.")
    async with Session() as s:
        n=await s.scalar(select(func.count()).select_from(Warning).where(Warning.chat_id==m.chat.id,Warning.user_id==m.reply_to_message.from_user.id))
    await m.answer(f"Warnings: {n}")
@dp.message(Command("unwarn"))
async def unwarn(m:Message):
    if not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.from_user: return await m.answer("Reply to a member.")
    async with Session() as s:
        row=await s.scalar(select(Warning).where(Warning.chat_id==m.chat.id,Warning.user_id==m.reply_to_message.from_user.id).order_by(Warning.id.desc()))
        if row: await s.delete(row)
        await s.commit()
    await m.answer("Latest warning removed." if row else "No warning found.")
@dp.message(Command("members"))
async def members(m:Message):
    if not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    async with Session() as s:
        n=await s.scalar(select(func.count()).select_from(Member).where(Member.chat_id==m.chat.id))
    await m.answer(f"Observed members: {n}
Note: only members the bot has observed are listed.")
@dp.message(Command("export"))
async def export(m:Message):
    if not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    async with Session() as s: rows=(await s.scalars(select(Member).where(Member.chat_id==m.chat.id))).all()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["user_id","username","full_name","status","first_seen","last_seen"])
    for x in rows: w.writerow([x.user_id,x.username,x.full_name,x.status,x.first_seen,x.last_seen])
    await m.answer_document(BufferedInputFile(out.getvalue().encode(),filename="observed-members.csv"))
async def run_bot():
    if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN is missing")
    bot=Bot(BOT_TOKEN)
    await dp.start_polling(bot)
