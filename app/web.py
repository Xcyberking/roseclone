import csv, io, json, secrets
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select, func, desc
from app.config import DASHBOARD_PASSWORD, SESSION_SECRET, OWNER_ID
from app.db import Session
from app.models import Group, Member, ModerationLog, Warning

app=FastAPI(title="CyberX Security Dashboard")
app.add_middleware(SessionMiddleware,secret_key=SESSION_SECRET,same_site="lax",https_only=False)
def page(title,body):
    return f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>{title} · CyberX</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#f4f8ff;color:#15345b;font:15px Arial}}header{{background:#155eef;color:white;padding:18px 20px;font-size:21px;font-weight:800}}nav{{display:flex;gap:8px;overflow:auto;padding:12px;background:white;position:sticky;top:0}}nav a{{white-space:nowrap;color:#155eef;text-decoration:none;border:1px solid #d7e4ff;border-radius:12px;padding:10px}}main{{max-width:1100px;margin:auto;padding:16px}}.card{{background:white;border:1px solid #e2ebff;border-radius:18px;padding:17px;margin:12px 0;box-shadow:0 6px 22px #164a8a0b}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px}}.num{{font-size:28px;font-weight:800;color:#155eef}}input,select,textarea,button{{width:100%;padding:12px;border:1px solid #cbdaf5;border-radius:10px;margin:6px 0;font:inherit}}button{{background:#155eef;color:white;border:0;font-weight:700}}table{{width:100%;border-collapse:collapse}}td,th{{padding:9px;border-bottom:1px solid #e5edfb;text-align:left}}small{{color:#637a9c}}.danger{{color:#b42318}}</style></head><body><header>🛡️ CyberX Security · {title}</header><nav><a href='/'>Overview</a><a href='/groups'>Groups</a><a href='/members'>Members</a><a href='/security'>Security</a><a href='/customize'>Customize</a><a href='/superadmin'>Super Admin</a><a href='/backup'>Backup</a><a href='/logout'>Logout</a></nav><main>{body}</main></body></html>"""
def auth(req):
    return bool(req.session.get("auth"))
@app.get("/login",response_class=HTMLResponse)
async def login_page():
    return page("Login","<div class='card'><h2>Dashboard Login</h2><form method='post'><input type='password' name='password' placeholder='Dashboard password' required><button>Sign in</button></form></div>")
@app.post("/login")
async def login(password:str=Form(...)):
    if not DASHBOARD_PASSWORD or not secrets.compare_digest(password,DASHBOARD_PASSWORD): return RedirectResponse("/login?error=1",303)
    r=RedirectResponse("/",303); r.set_cookie("cx-login","1",httponly=True,samesite="lax"); return r
@app.middleware("http")
async def session_gate(request,call_next):
    if request.url.path in ("/login","/health"): return await call_next(request)
    if not request.session.get("auth"): return RedirectResponse("/login",303)
    return await call_next(request)
@app.get("/logout")
async def logout():
    r=RedirectResponse("/login",303); r.delete_cookie("cx-login"); return r
@app.get("/health")
async def health(): return {"status":"ok","service":"cyberx"}
@app.get("/",response_class=HTMLResponse)
async def home():
    async with Session() as s:
        groups=await s.scalar(select(func.count()).select_from(Group)); members=await s.scalar(select(func.count()).select_from(Member)); logs=await s.scalar(select(func.count()).select_from(ModerationLog)); warns=await s.scalar(select(func.count()).select_from(Warning))
    body=f"<div class='grid'>{''.join(f'<div class=card><small>{k}</small><div class=num>{v}</div></div>' for k,v in [('Groups',groups),('Observed members',members),('Security actions',logs),('Warnings',warns)])}</div><div class=card><h3>Security center</h3><p>Manage group protection, member records, logs, exports and appearance settings.</p><small>Member directory contains observed users only, not a full Telegram group roster.</small></div>"
    return page("Overview",body)
@app.get("/groups",response_class=HTMLResponse)
async def groups():
    async with Session() as s: rows=(await s.scalars(select(Group).order_by(Group.id.desc()))).all()
    body="<h2>Connected groups</h2>"+''.join(f"<div class=card><b>{g.title}</b><p>ID: {g.chat_id}</p><small>Anti-flood: {g.antiflood_enabled} · Anti-link: {g.antilink_enabled} · Welcome: {g.welcome_enabled}</small></div>" for g in rows)
    return page("Groups",body)
@app.get("/members",response_class=HTMLResponse)
async def members():
    async with Session() as s: rows=(await s.scalars(select(Member).order_by(desc(Member.last_seen)).limit(300))).all()
    body="<h2>Observed members</h2><div class=card><table><tr><th>User</th><th>ID</th><th>Status</th></tr>"+''.join(f"<tr><td>{m.full_name}<br><small>@{m.username or 'no-username'}</small></td><td>{m.user_id}</td><td>{m.status}</td></tr>" for m in rows)+"</table></div>"
    return page("Members",body)
@app.get("/security",response_class=HTMLResponse)
async def security():
    async with Session() as s: rows=(await s.scalars(select(ModerationLog).order_by(desc(ModerationLog.created_at)).limit(100))).all()
    body="<h2>Security audit log</h2>"+''.join(f"<div class=card><b>{x.action}</b> · user {x.user_id}<p>{x.reason}</p><small>{x.created_at}</small></div>" for x in rows)
    return page("Security",body)
@app.get("/customize",response_class=HTMLResponse)
async def customize():
    async with Session() as s: rows=(await s.scalars(select(Group))).all()
    body="<h2>Customization system</h2><p>Set per-group welcome copy and protection toggles.</p>"+''.join(f"""<div class=card><h3>{g.title}</h3><form method=post action='/customize/{g.chat_id}'><label>Welcome message (supports {{name}} and {{id}})</label><textarea name=welcome_text>{g.welcome_text}</textarea><label><input style='width:auto' type=checkbox name=welcome_enabled {'checked' if g.welcome_enabled else ''}> Welcome enabled</label><label><input style='width:auto' type=checkbox name=antiflood_enabled {'checked' if g.antiflood_enabled else ''}> Anti-flood enabled</label><label><input style='width:auto' type=checkbox name=antilink_enabled {'checked' if g.antilink_enabled else ''}> Anti-link enabled</label><button>Save settings</button></form></div>""" for g in rows)
    return page("Customize",body)
@app.post("/customize/{chat_id}")
async def save_custom(chat_id:int,welcome_text:str=Form(...),welcome_enabled:str|None=Form(None),antiflood_enabled:str|None=Form(None),antilink_enabled:str|None=Form(None)):
    async with Session() as s:
        g=await s.scalar(select(Group).where(Group.chat_id==chat_id))
        if g: g.welcome_text=welcome_text[:1000]; g.welcome_enabled=bool(welcome_enabled); g.antiflood_enabled=bool(antiflood_enabled); g.antilink_enabled=bool(antilink_enabled); await s.commit()
    return RedirectResponse("/customize",303)
@app.get("/superadmin",response_class=HTMLResponse)
async def superadmin():
    async with Session() as s:
        groups=await s.scalars(select(Group)); rows=list(groups)
    body="<h2>Super Admin Panel</h2><div class=card><b>Global overview</b><p>Groups managed: "+str(len(rows))+"</p><p>Owner Telegram ID configured: "+("Yes" if OWNER_ID else "No")+"</p><small>Global destructive actions are intentionally not exposed without a second confirmation workflow.</small></div>"
    return page("Super Admin",body)
@app.get("/backup")
async def backup():
    async with Session() as s:
        gs=(await s.scalars(select(Group))).all(); ms=(await s.scalars(select(Member))).all(); ls=(await s.scalars(select(ModerationLog))).all(); ws=(await s.scalars(select(Warning))).all()
    payload={"groups":[{"chat_id":g.chat_id,"title":g.title,"welcome_enabled":g.welcome_enabled,"welcome_text":g.welcome_text,"antiflood_enabled":g.antiflood_enabled,"antilink_enabled":g.antilink_enabled} for g in gs],"members":[{"chat_id":m.chat_id,"user_id":m.user_id,"username":m.username,"full_name":m.full_name,"status":m.status} for m in ms],"logs":[{"chat_id":x.chat_id,"user_id":x.user_id,"action":x.action,"reason":x.reason} for x in ls],"warnings":[{"chat_id":w.chat_id,"user_id":w.user_id,"reason":w.reason} for w in ws]}
    data=json.dumps(payload,ensure_ascii=False,indent=2).encode()
    return StreamingResponse(io.BytesIO(data),media_type="application/json",headers={"Content-Disposition":"attachment; filename=cyberx-backup.json"})
