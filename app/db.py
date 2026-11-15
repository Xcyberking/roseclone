from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import DATABASE_URL
if DATABASE_URL.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)
engine=create_async_engine(DATABASE_URL, echo=False)
Session=async_sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
async def init_db():
    from app import models, models_extra, models_security
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
