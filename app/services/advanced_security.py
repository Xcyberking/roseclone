import os, re, hashlib, hmac, time
from collections import defaultdict, deque
from urllib.parse import urlparse
from cryptography.fernet import Fernet, InvalidToken
from app.config import REDIS_URL
from app.db import Session
from app.models_advanced import URLPolicy, TrustProfile, ReviewCase
from sqlalchemy import select
try:
    import redis.asyncio as redis
except Exception:
    redis=None
_local=defaultdict(deque)
_client=None
def _fernet():
    key=os.getenv("DATA_ENCRYPTION_KEY","")
    if not key: return None
    try: return Fernet(key.encode())
    except Exception: return None
def encrypt_value(value:str)->str:
    f=_fernet()
    if not f: raise RuntimeError("Set a valid DATA_ENCRYPTION_KEY before encrypting sensitive data")
    return f.encrypt(value.encode()).decode()
def decrypt_value(value:str)->str:
    f=_fernet()
    if not f: raise RuntimeError("DATA_ENCRYPTION_KEY is not configured")
    try: return f.decrypt(value.encode()).decode()
    except InvalidToken as exc: raise ValueError("Encrypted value cannot be decrypted with current key") from exc
async def allow_request(key:str,limit:int,window:int)->bool:
    global _client
    if REDIS_URL and redis:
        try:
            if _client is None: _client=redis.from_url(REDIS_URL,decode_responses=True)
            n=await _client.incr(key)
            if n==1: await _client.expire(key,window)
            return n<=limit
        except Exception:
            pass
    now=time.monotonic(); q=_local[key]
    while q and now-q[0]>window: q.popleft()
    if len(q)>=limit: return False
    q.append(now); return True
def extract_domains(text:str)->list[str]:
    out=[]
    for raw in re.findall(r'(?i)(?:https?://|www\\.)[^\\s<>]+',text or ""):
        host=(urlparse(raw if "://" in raw else "https://"+raw).hostname or "").lower().rstrip(".")
        if host: out.append(host.removeprefix("www."))
    return out
async def url_allowed(chat_id:int,text:str)->tuple[bool,str]:
    domains=extract_domains(text)
    if not domains: return True,""
    async with Session() as s:
        rows=(await s.scalars(select(URLPolicy).where(URLPolicy.chat_id==chat_id))).all()
    policies={x.domain.lower():x.mode for x in rows}
    for host in domains:
        matches=[mode for domain,mode in policies.items() if host==domain or host.endswith("."+domain)]
        if "deny" in matches: return False,host
        if policies and "allow" not in matches and any(x.mode=="allow" for x in rows):
            return False,host
    return True,""
async def update_trust(chat_id:int,user_id:int,delta:float,flag:bool=False,reason:str=""):
    async with Session() as s:
        p=await s.scalar(select(TrustProfile).where(TrustProfile.chat_id==chat_id,TrustProfile.user_id==user_id))
        if not p:
            p=TrustProfile(chat_id=chat_id,user_id=user_id); s.add(p)
        p.score=max(0,min(100,p.score+delta)); p.messages_seen+=1
        if flag: p.flags+=1
        p.updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        if p.score<30:
            p.review_status="review"
            exists=await s.scalar(select(ReviewCase).where(ReviewCase.chat_id==chat_id,ReviewCase.user_id==user_id,ReviewCase.status=="open"))
            if not exists: s.add(ReviewCase(chat_id=chat_id,user_id=user_id,reason=reason or "Trust score fell below review threshold"))
        await s.commit()
        return p.score
