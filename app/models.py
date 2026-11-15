from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db import Base
def now(): return datetime.now(timezone.utc)
class Group(Base):
    __tablename__="groups"
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str]=mapped_column(String(255), default="Telegram group")
    welcome_enabled: Mapped[bool]=mapped_column(Boolean, default=True)
    welcome_text: Mapped[str]=mapped_column(Text, default="Welcome {name}!")
    antiflood_enabled: Mapped[bool]=mapped_column(Boolean, default=True)
    antilink_enabled: Mapped[bool]=mapped_column(Boolean, default=False)
    max_messages: Mapped[int]=mapped_column(Integer, default=6)
    window_seconds: Mapped[int]=mapped_column(Integer, default=8)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
class Member(Base):
    __tablename__="members"
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger, index=True)
    user_id: Mapped[int]=mapped_column(BigInteger, index=True)
    username: Mapped[str|None]=mapped_column(String(100), nullable=True)
    full_name: Mapped[str]=mapped_column(String(255), default="")
    status: Mapped[str]=mapped_column(String(30), default="seen")
    first_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint("chat_id","user_id"),)
class ModerationLog(Base):
    __tablename__="moderation_logs"
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger, index=True)
    user_id: Mapped[int]=mapped_column(BigInteger)
    action: Mapped[str]=mapped_column(String(40))
    reason: Mapped[str]=mapped_column(Text, default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
class Warning(Base):
    __tablename__="warnings"
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger, index=True)
    user_id: Mapped[int]=mapped_column(BigInteger, index=True)
    reason: Mapped[str]=mapped_column(Text, default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
