from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db import Base
def utc(): return datetime.now(timezone.utc)
class AppUser(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    telegram_id: Mapped[int]=mapped_column(BigInteger,unique=True,index=True)
    username: Mapped[str|None]=mapped_column(String(100),nullable=True)
    display_name: Mapped[str]=mapped_column(String(255),default="")
    first_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc)
    last_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc)
class GroupSetting(Base):
    __tablename__="group_settings"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,unique=True,index=True)
    rules_text: Mapped[str]=mapped_column(Text,default="Be respectful. No spam or scams.")
    goodbye_text: Mapped[str]=mapped_column(Text,default="Goodbye {name}.")
    captcha_enabled: Mapped[bool]=mapped_column(Boolean,default=False)
    media_lock: Mapped[bool]=mapped_column(Boolean,default=False)
    forward_lock: Mapped[bool]=mapped_column(Boolean,default=False)
    poll_lock: Mapped[bool]=mapped_column(Boolean,default=False)
    raid_mode: Mapped[bool]=mapped_column(Boolean,default=False)
class BlockedUser(Base):
    __tablename__="blocked_users"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    reason: Mapped[str]=mapped_column(Text,default="")
    __table_args__=(UniqueConstraint("chat_id","user_id"),)
