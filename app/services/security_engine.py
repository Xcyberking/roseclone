"""Behaviour-based, explainable risk scoring. Never scores users by username or account age."""
import re, unicodedata
from collections import Counter
URL_RE=re.compile(r"https?://[^\s]+|t\.me/[^\s]+",re.I)
SHORT_HOSTS={"bit.ly","tinyurl.com","t.co","is.gd","cutt.ly","rb.gy"}
SUSPICIOUS_TERMS=("verify wallet","claim reward","urgent payment","seed phrase","password reset")
def analyze_message(text:str, recent_texts:list[str]|None=None)->dict:
    text=text or ""; recent_texts=recent_texts or []
    score=0; reasons=[]
    links=URL_RE.findall(text)
    if len(links)>=3: score+=25; reasons.append("multiple links in one message")
    if len(links)>=1 and any(h in text.lower() for h in SHORT_HOSTS): score+=20; reasons.append("URL shortener detected")
    if any(term in text.lower() for term in SUSPICIOUS_TERMS): score+=25; reasons.append("known social-engineering phrase")
    if any(text.strip().casefold()==x.strip().casefold() for x in recent_texts if x.strip()): score+=30; reasons.append("repeated message")
    if len(text)>0 and sum(1 for c in text if unicodedata.category(c)=="Cf")>2: score+=20; reasons.append("hidden formatting characters")
    letters=[c for c in text if c.isalpha()]
    if len(letters)>12 and sum(1 for c in letters if unicodedata.category(c)=="So")>len(letters)*.35: score+=10; reasons.append("unusual symbol density")
    score=min(score,100)
    level="low" if score<25 else "medium" if score<50 else "high" if score<80 else "critical"
    return {"score":score,"level":level,"reasons":reasons}
def should_auto_moderate(result:dict, threshold:int=70)->bool:
    return result["score"]>=threshold
