from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db import Base
def utcnow(): return datetime.now(timezone.utc)
class AdminRole(Base):
    __tablename__="admins"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    role: Mapped[str]=mapped_column(String(30),default="moderator")
    permissions: Mapped[str]=mapped_column(Text,default="moderate,view_logs")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__=(UniqueConstraint("chat_id","user_id"),)
class BlockedDomain(Base):
    __tablename__="blocked_domains"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    domain: Mapped[str]=mapped_column(String(255),unique=True,index=True)
    reason: Mapped[str]=mapped_column(Text,default="")
class CustomFilter(Base):
    __tablename__="custom_filters"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    phrase: Mapped[str]=mapped_column(String(300))
    action: Mapped[str]=mapped_column(String(20),default="delete")
    enabled: Mapped[bool]=mapped_column(Boolean,default=True)
class Verification(Base):
    __tablename__="verification"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    code_hash: Mapped[str]=mapped_column(String(128))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    verified: Mapped[bool]=mapped_column(Boolean,default=False)
class UserReport(Base):
    __tablename__="reports"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    reporter_id: Mapped[int]=mapped_column(BigInteger)
    target_id: Mapped[int]=mapped_column(BigInteger)
    reason: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),default="open")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class BotSetting(Base):
    __tablename__="bot_settings"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    key: Mapped[str]=mapped_column(String(100),unique=True,index=True)
    value: Mapped[str]=mapped_column(Text,default="")
class Subscription(Base):
    __tablename__="subscriptions"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    plan: Mapped[str]=mapped_column(String(50),default="free")
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    actor_id: Mapped[int]=mapped_column(BigInteger,index=True)
    scope: Mapped[str]=mapped_column(String(100))
    action: Mapped[str]=mapped_column(String(100))
    detail: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
