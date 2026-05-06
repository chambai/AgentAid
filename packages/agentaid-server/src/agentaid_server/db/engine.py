from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel
from ..config import settings

engine = create_async_engine(settings.db_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    from . import models  # noqa: F401  -- triggers SQLModel metadata population
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def session() -> AsyncSession:
    async with SessionLocal() as s:
        yield s
