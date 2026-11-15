from datetime import datetime, timezone
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Text, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
def utcnow(): return datetime.now(timezone.utc)
class URLPolicy(Base):
    __tablename__="url_policies"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    domain: Mapped[str]=mapped_column(String(255))
    mode: Mapped[str]=mapped_column(String(20),default="allow")
    added_by: Mapped[int]=mapped_column(BigInteger)
    __table_args__=(UniqueConstraint("chat_id","domain"),)
class ScheduledMessage(Base):
    __tablename__="scheduled_messages"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    text: Mapped[str]=mapped_column(Text)
    run_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    created_by: Mapped[int]=mapped_column(BigInteger)
    enabled: Mapped[bool]=mapped_column(Boolean,default=True)
    sent_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class TrustProfile(Base):
    __tablename__="trust_profiles"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    score: Mapped[float]=mapped_column(Float,default=50)
    messages_seen: Mapped[int]=mapped_column(Integer,default=0)
    flags: Mapped[int]=mapped_column(Integer,default=0)
    review_status: Mapped[str]=mapped_column(String(20),default="clear")
    notes: Mapped[str]=mapped_column(Text,default="")
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__=(UniqueConstraint("chat_id","user_id"),)
class ReviewCase(Base):
    __tablename__="review_cases"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    reason: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),default="open")
    reviewer_id: Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class VerificationChallenge(Base):
    __tablename__="verification_challenges"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    answer_hash: Mapped[str]=mapped_column(String(128))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    attempts: Mapped[int]=mapped_column(Integer,default=0)
    completed: Mapped[bool]=mapped_column(Boolean,default=False)
