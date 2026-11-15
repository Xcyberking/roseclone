import asyncio, time, csv, io, re
from collections import defaultdict, deque
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ChatMemberUpdated, BufferedInputFile
from sqlalchemy import select, func
from app.config import BOT_TOKEN, OWNER_ID
from app.db import Session
from app.models import Group, Member, ModerationLog, Warning
from app.models_security import GroupSetting, BlockedUser, CustomFilter, BlockedDomain
from app.services.security_engine import analyze_message, should_auto_moderate
from app.bot_extra import register_extra
from app.services.advanced_security import allow_request, url_allowed, update_trust
from app.services.moderation import restrict_user

dp=Dispatcher()
register_extra(dp)
flood=defaultdict(deque)
recent_text=defaultdict(lambda: deque(maxlen=6))
emoji_count=defaultdict(lambda: deque())
def owner(uid): return bool(OWNER_ID and uid==OWNER_ID)
async def is_admin(bot,chat_id,uid):
    if owner(uid): return True
    try:
        cm=await bot.get_chat_member(chat_id,uid)
        return cm.status in ("administrator","creator")
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
async def get_features(chat_id):
    async with Session() as s:
        g=await s.scalar(select(GroupSetting).where(GroupSetting.chat_id==chat_id))
        return g
async def log(chat,user,action,reason=""):
    async with Session() as s:
        s.add(ModerationLog(chat_id=chat,user_id=user,action=action,reason=reason[:1000])); await s.commit()
async def delete_and_log(m,action,reason):
    try:
        await m.delete()
        await log(m.chat.id,m.from_user.id,action,reason)
        return True
    except Exception:
        return False

@dp.message(CommandStart())
async def start(m:Message):
    await m.answer("🛡️ CyberX Security Bot is online. Add me to your group as admin and use /help.")
@dp.message(Command("help"))
async def help_cmd(m:Message):
    await m.answer("/security — protection status\n/antiflood on|off\n/antilink on|off\n/welcome on|off\n/warn (reply) [reason]\n/warnings (reply)\n/unwarn (reply)\n/members — observed member count\n/export — CSV export\n/rules — group rules\n/report (reply) [reason]\n/stats, /groups, /health — owner only")
@dp.my_chat_member()
async def added(ev:ChatMemberUpdated):
    if ev.chat.type in ("group","supergroup"):
        await get_group(ev.chat)
@dp.chat_member()
async def member_update(ev:ChatMemberUpdated):
    if ev.chat.type not in ("group","supergroup"): return
    u=ev.new_chat_member.user
    new_status=ev.new_chat_member.status
    old_status=ev.old_chat_member.status
    joined=new_status in ("member","administrator","creator") and old_status in ("left","kicked")
    left=new_status in ("left","kicked")
    await observe(ev.chat.id,u,"left" if left else "member")
    if joined:
        # Anti-raid is an alert/temporary hold only when group admin enables verification.
        cfg=await get_group(ev.chat)
        feat=await get_features(ev.chat.id)
        if cfg["welcome_enabled"]:
            try: await ev.bot.send_message(ev.chat.id,cfg["welcome_text"].replace("{name}",u.full_name).replace("{id}",str(u.id)))
            except Exception: pass
        if feat and feat.raid_mode:
            await log(ev.chat.id,u.id,"raid_join_review","New join while raid mode enabled")
    if left:
        feat=await get_features(ev.chat.id)
        if feat and feat.goodbye_text:
            try: await ev.bot.send_message(ev.chat.id,feat.goodbye_text.replace("{name}",u.full_name))
            except Exception: pass

@dp.message(F.chat.type.in_({"group","supergroup"}))
async def group_messages(m:Message):
    if not m.from_user: return
    if not await allow_request(f"msg:{m.chat.id}:{m.from_user.id}",30,10):
        await delete_and_log(m,"redis_rate_limit","Rate limit exceeded")
        return
    await observe(m.chat.id,m.from_user)
    if await is_admin(m.bot,m.chat.id,m.from_user.id): return
    cfg=await get_group(m.chat)
    feat=await get_features(m.chat.id)
    body=m.text or m.caption or ""
    key=(m.chat.id,m.from_user.id)
    # Behaviour-based scoring: username and account age are deliberately excluded.
    threat=analyze_message(body,list(recent_text[key]))
    await update_trust(m.chat.id,m.from_user.id,(-min(20,threat["score"]/5) if threat["score"] else 0.15),flag=threat["score"]>=50,reason=", ".join(threat["reasons"]))
    if body: recent_text[key].append(body)
    # Media/forward lock policies configured by group admins.
    if feat:
        if feat.forward_lock and (m.forward_origin is not None):
            if await delete_and_log(m,"forward_lock","Forwarding disabled"): return
        if feat.media_lock and (m.photo or m.video or m.document or m.animation or m.audio or m.voice or m.sticker):
            if await delete_and_log(m,"media_lock","Media disabled"): return
        if feat.poll_lock and m.poll:
            if await delete_and_log(m,"poll_lock","Polls disabled"): return
    # Custom phrase filters
    async with Session() as s:
        filters=(await s.scalars(select(CustomFilter).where(CustomFilter.chat_id==m.chat.id,CustomFilter.enabled==True))).all()
        blocked=(await s.scalars(select(BlockedDomain))).all()
        blocked_users=await s.scalar(select(BlockedUser).where(BlockedUser.chat_id==m.chat.id,BlockedUser.user_id==m.from_user.id))
    if blocked_users:
        try: await m.delete()
        except Exception: pass
        return
    lowered=body.casefold()
    for item in filters:
        if item.phrase.casefold() in lowered:
            await delete_and_log(m,"custom_filter",f"Matched configured filter: {item.phrase}")
            return
    for domain in blocked:
        if domain.domain.casefold() in lowered:
            await delete_and_log(m,"blocked_domain",f"Blocked domain: {domain.domain}")
            return
    # URL rules (invite links, shorteners and unknown external links are covered by anti-link toggle)
    urls=re.findall(r"(?:https?://|www\.|t\.me/)[^\s]+",lowered)
    if cfg["antilink_enabled"] and urls:
        await delete_and_log(m,"link_removed","Link policy")
        return
    # Duplicate/repeated and behaviour-based high-risk message detection
    if should_auto_moderate(threat,threshold=85):
        await delete_and_log(m,"smart_engine_delete",", ".join(threat["reasons"]))
        try:
            await restrict_user(m.bot,m.chat.id,m.from_user.id,minutes=10)
            await log(m.chat.id,m.from_user.id,"auto_restrict","Critical behaviour score; temporary 10-minute restriction")
        except Exception:
            pass
        return
    # Flood protection, emoji/sticker and forward burst limits.
    now=time.monotonic()
    q=flood[key]; q.append(now)
    while q and now-q[0]>cfg["window_seconds"]: q.popleft()
    if cfg["antiflood_enabled"] and len(q)>cfg["max_messages"]:
        await delete_and_log(m,"delete_flood","Message flood threshold")
        return
    emoji_count[key].append((now,1 if m.sticker else 0))
    while emoji_count[key] and now-emoji_count[key][0][0]>10: emoji_count[key].popleft()
    if sum(x[1] for x in emoji_count[key])>=5:
        await delete_and_log(m,"sticker_spam","Sticker burst threshold")
        emoji_count[key].clear()

@dp.message(Command("security"))
async def security(m:Message):
    if not m.from_user or not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    c=await get_group(m.chat)
    await m.answer(f"🛡️ Security for {m.chat.title}\nAnti-flood: {c['antiflood_enabled']}\nAnti-link: {c['antilink_enabled']}\nWelcome: {c['welcome_enabled']}")
async def set_flag(m,field,value):
    if not m.from_user or not await is_admin(m.bot,m.chat.id,m.from_user.id): return
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
    if not m.from_user or not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.from_user: return await m.answer("Reply to a member's message: /warn [reason]")
    target=m.reply_to_message.from_user; reason=(m.text or "").partition(" ")[2] or "No reason provided"
    async with Session() as s:
        s.add(Warning(chat_id=m.chat.id,user_id=target.id,reason=reason))
        s.add(ModerationLog(chat_id=m.chat.id,user_id=target.id,action="warn",reason=reason))
        await s.commit()
        count=await s.scalar(select(func.count()).select_from(Warning).where(Warning.chat_id==m.chat.id,Warning.user_id==target.id))
    await m.answer(f"⚠️ Warning recorded for {target.full_name}. Total: {count}")
@dp.message(Command("warnings"))
async def warnings(m:Message):
    if not m.from_user or not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.from_user: return await m.answer("Reply to a member.")
    async with Session() as s:
        n=await s.scalar(select(func.count()).select_from(Warning).where(Warning.chat_id==m.chat.id,Warning.user_id==m.reply_to_message.from_user.id))
    await m.answer(f"Warnings: {n}")
@dp.message(Command("unwarn"))
async def unwarn(m:Message):
    if not m.from_user or not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    if not m.reply_to_message or not m.reply_to_message.from_user: return await m.answer("Reply to a member.")
    async with Session() as s:
        row=await s.scalar(select(Warning).where(Warning.chat_id==m.chat.id,Warning.user_id==m.reply_to_message.from_user.id).order_by(Warning.id.desc()))
        if row: await s.delete(row)
        await s.commit()
    await m.answer("Latest warning removed." if row else "No warning found.")
@dp.message(Command("members"))
async def members(m:Message):
    if not m.from_user or not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    async with Session() as s:
        n=await s.scalar(select(func.count()).select_from(Member).where(Member.chat_id==m.chat.id))
    await m.answer(f"Observed members: {n}\nTelegram does not provide bots a full historic member list.")
@dp.message(Command("export"))
async def export(m:Message):
    if not m.from_user or not await is_admin(m.bot,m.chat.id,m.from_user.id): return
    async with Session() as s: rows=(await s.scalars(select(Member).where(Member.chat_id==m.chat.id))).all()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["user_id","username","full_name","status","first_seen","last_seen"])
    for x in rows: w.writerow([x.user_id,x.username,x.full_name,x.status,x.first_seen,x.last_seen])
    await m.answer_document(BufferedInputFile(out.getvalue().encode(),filename="observed-members.csv"))
async def run_bot():
    if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN is missing")
    bot=Bot(BOT_TOKEN)
    await dp.start_polling(bot)
