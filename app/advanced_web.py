import json, io
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select, desc
from app.db import Session
from app.models_advanced import URLPolicy, ScheduledMessage, TrustProfile, ReviewCase
from app.models_extra import AdminRole, AuditLog
from app.models_security import GroupSetting
from app.services.advanced_security import encrypt_value, decrypt_value
router=APIRouter()
def _allowed(req, permission):
    perms=set((req.session.get("permissions") or "").split(","))
    return req.session.get("role")=="owner" or permission in perms or "*" in perms
@router.get("/advanced",response_class=HTMLResponse)
async def advanced_home(request:Request):
    if not request.session.get("auth"): return RedirectResponse("/login",303)
    return HTMLResponse("""<h2>Advanced Security Console</h2><p><a href='/advanced/roles'>Roles</a> · <a href='/advanced/urls'>URL allowlist</a> · <a href='/advanced/schedules'>Scheduled messages</a> · <a href='/advanced/reviews'>Trust & manual review</a> · <a href='/advanced/backup'>Full backup</a></p>""")
@router.get("/advanced/urls",response_class=HTMLResponse)
async def urls(request:Request):
    if not request.session.get("auth"): return RedirectResponse("/login",303)
    async with Session() as s: rows=(await s.scalars(select(URLPolicy).order_by(URLPolicy.chat_id))).all()
    html="<h2>URL policy</h2><form method='post'><input name='chat_id' placeholder='Group chat ID' required><input name='domain' placeholder='example.com' required><select name='mode'><option value='allow'>Allow</option><option value='deny'>Block</option></select><button>Add policy</button></form>"
    html+="".join(f"<p>Group {x.chat_id}: {x.domain} — {x.mode}</p>" for x in rows)
    return HTMLResponse(html)
@router.post("/advanced/urls")
async def add_url(request:Request,chat_id:int=Form(...),domain:str=Form(...),mode:str=Form(...)):
    if not request.session.get("auth") or not _allowed(request,"manage_links"): raise HTTPException(403)
    domain=domain.lower().strip().removeprefix("https://").removeprefix("http://").removeprefix("www.").strip("/")
    if not domain or "/" in domain or mode not in ("allow","deny"): raise HTTPException(400,"Invalid domain or mode")
    async with Session() as s:
        row=await s.scalar(select(URLPolicy).where(URLPolicy.chat_id==chat_id,URLPolicy.domain==domain))
        if row: row.mode=mode
        else: s.add(URLPolicy(chat_id=chat_id,domain=domain,mode=mode,added_by=request.session.get("user_id",0)))
        await s.commit()
    return RedirectResponse("/advanced/urls",303)
@router.get("/advanced/schedules",response_class=HTMLResponse)
async def schedules(request:Request):
    if not request.session.get("auth"): return RedirectResponse("/login",303)
    async with Session() as s: rows=(await s.scalars(select(ScheduledMessage).order_by(ScheduledMessage.run_at))).all()
    html="<h2>Scheduled group messages</h2><form method='post'><input name='chat_id' placeholder='Group ID' required><textarea name='text' placeholder='Message' required></textarea><input name='run_at' type='datetime-local' required><button>Schedule</button></form>"
    html+="".join(f"<p>#{x.id} · {x.chat_id} · {x.run_at} · {'enabled' if x.enabled else 'paused'}</p>" for x in rows)
    return HTMLResponse(html)
@router.post("/advanced/schedules")
async def add_schedule(request:Request,chat_id:int=Form(...),text:str=Form(...),run_at:str=Form(...)):
    if not request.session.get("auth") or not _allowed(request,"manage_schedules"): raise HTTPException(403)
    dt=datetime.fromisoformat(run_at)
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    if dt<=datetime.now(timezone.utc): raise HTTPException(400,"Schedule must be in the future")
    async with Session() as s: s.add(ScheduledMessage(chat_id=chat_id,text=text[:4000],run_at=dt,created_by=request.session.get("user_id",0))); await s.commit()
    return RedirectResponse("/advanced/schedules",303)
@router.get("/advanced/reviews",response_class=HTMLResponse)
async def reviews(request:Request):
    if not request.session.get("auth"): return RedirectResponse("/login",303)
    async with Session() as s:
        profiles=(await s.scalars(select(TrustProfile).order_by(TrustProfile.score).limit(300))).all()
        cases=(await s.scalars(select(ReviewCase).where(ReviewCase.status=="open").order_by(desc(ReviewCase.created_at)))).all()
    html="<h2>Trust scores & manual review</h2><h3>Open cases</h3>"
    html+="".join(f"<form method='post' action='/advanced/reviews/{x.id}'><p>Group {x.chat_id} · User {x.user_id} · {x.reason}</p><button name='decision' value='clear'>Mark reviewed</button><button name='decision' value='ban'>Confirm ban recommendation</button></form>" for x in cases)
    html+="<h3>Trust profiles</h3>"+"".join(f"<p>Group {p.chat_id} · User {p.user_id} · score {p.score:.0f}/100 · flags {p.flags} · {p.review_status}</p>" for p in profiles)
    return HTMLResponse(html)
@router.post("/advanced/reviews/{case_id}")
async def review_case(case_id:int,request:Request,decision:str=Form(...)):
    if not request.session.get("auth") or not _allowed(request,"review_trust"): raise HTTPException(403)
    async with Session() as s:
        case=await s.get(ReviewCase,case_id)
        if not case: raise HTTPException(404)
        case.status="reviewed" if decision in ("clear","ban") else "open"; case.reviewer_id=request.session.get("user_id")
        profile=await s.scalar(select(TrustProfile).where(TrustProfile.chat_id==case.chat_id,TrustProfile.user_id==case.user_id))
        if profile: profile.review_status="reviewed" if decision=="clear" else "flagged"
        await s.commit()
    return RedirectResponse("/advanced/reviews",303)
@router.get("/advanced/roles",response_class=HTMLResponse)
async def roles(request:Request):
    if not request.session.get("auth"): return RedirectResponse("/login",303)
    async with Session() as s: rows=(await s.scalars(select(AdminRole))).all()
    html="<h2>Role-based access</h2><p>Owner: all permissions. Roles: moderator, reviewer, link_manager, scheduler, viewer.</p><form method='post'><input name='chat_id' placeholder='Group ID' required><input name='user_id' placeholder='Telegram user ID' required><select name='role'><option>moderator</option><option>reviewer</option><option>link_manager</option><option>scheduler</option><option>viewer</option></select><button>Assign role</button></form>"
    html+="".join(f"<p>Group {x.chat_id} · {x.user_id} · {x.role} · {x.permissions}</p>" for x in rows)
    return HTMLResponse(html)
@router.post("/advanced/roles")
async def assign_role(request:Request,chat_id:int=Form(...),user_id:int=Form(...),role:str=Form(...)):
    if not request.session.get("auth") or request.session.get("role")!="owner": raise HTTPException(403)
    mapping={"moderator":"moderate,view_logs","reviewer":"review_trust,view_logs","link_manager":"manage_links,view_logs","scheduler":"manage_schedules,view_logs","viewer":"view_logs"}
    if role not in mapping: raise HTTPException(400)
    async with Session() as s:
        row=await s.scalar(select(AdminRole).where(AdminRole.chat_id==chat_id,AdminRole.user_id==user_id))
        if row: row.role=role; row.permissions=mapping[role]
        else: s.add(AdminRole(chat_id=chat_id,user_id=user_id,role=role,permissions=mapping[role]))
        await s.commit()
    return RedirectResponse("/advanced/roles",303)
@router.get("/advanced/backup")
async def full_backup(request:Request):
    if not request.session.get("auth") or request.session.get("role")!="owner": raise HTTPException(403)
    from app import models,models_extra,models_security,models_advanced
    from app.db import Base
    payload={}
    async with Session() as s:
        for table in Base.metadata.sorted_tables:
            result=await s.execute(select(table))
            payload[table.name]=[dict(row._mapping) for row in result]
    def clean(v):
        if isinstance(v,datetime): return v.isoformat()
        return v
    data=json.dumps(payload,default=clean,ensure_ascii=False).encode()
    return StreamingResponse(io.BytesIO(data),media_type="application/json",headers={"Content-Disposition":"attachment; filename=cyberx-full-backup.json"})
@router.post("/advanced/restore")
async def restore_backup(request:Request,file:UploadFile=File(...)):
    if not request.session.get("auth") or request.session.get("role")!="owner": raise HTTPException(403)
    if not file.filename.endswith(".json"): raise HTTPException(400,"JSON backup required")
    raw=await file.read()
    if len(raw)>20_000_000: raise HTTPException(413,"Backup exceeds 20 MB")
    try: data=json.loads(raw)
    except Exception: raise HTTPException(400,"Invalid JSON")
    allowed={"groups","members","moderation_logs","warnings","admins","blocked_domains","custom_filters","verification","reports","bot_settings","subscriptions","audit_logs","users","group_settings","blocked_users","url_policies","scheduled_messages","trust_profiles","review_cases","verification_challenges"}
    if not isinstance(data,dict) or not set(data).issubset(allowed): raise HTTPException(400,"Unsupported backup structure")
    # Import is deliberately append-only and validates table/column names. Duplicate primary keys are skipped.
    from sqlalchemy import text
    async with Session() as s:
        for table,rows in data.items():
            if not isinstance(rows,list): raise HTTPException(400,"Each table must contain a list")
            for row in rows:
                if not isinstance(row,dict): continue
                safe={k:v for k,v in row.items() if k.replace("_","").isalnum()}
                if not safe: continue
                cols=",".join('"'+k+'"' for k in safe)
                binds=",".join(":"+k for k in safe)
                try: await s.execute(text(f'INSERT INTO "{table}" ({cols}) VALUES ({binds}) ON CONFLICT DO NOTHING'),safe)
                except Exception: await s.rollback(); raise HTTPException(400,f"Restore failed in table {table}")
        await s.commit()
    return {"status":"restored","mode":"append-only; existing rows preserved"}
