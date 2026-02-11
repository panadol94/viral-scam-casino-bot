"""Database models and CRUD operations for the scam casino bot."""

import json
import os
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL", "")


class Base(DeclarativeBase):
    pass


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    casino_name = Column(String(500), nullable=False, index=True)
    casino_link = Column(String(1000), nullable=True)
    amount_lost = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    screenshots = Column(Text, default="[]")  # JSON array of file_ids
    grid_image_id = Column(String(500), nullable=True)  # Telegram file_id of grid
    channel_message_id = Column(BigInteger, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def get_screenshots(self) -> list[str]:
        try:
            return json.loads(self.screenshots or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_screenshots(self, file_ids: list[str]) -> None:
        self.screenshots = json.dumps(file_ids)


class BannedUser(Base):
    __tablename__ = "banned_users"

    user_id = Column(BigInteger, primary_key=True)
    reason = Column(Text, nullable=True)
    banned_by = Column(BigInteger, nullable=False)
    banned_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


# ── Engine & Session ──────────────────────────────────────────────

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Report CRUD ───────────────────────────────────────────────────


async def create_report(
    user_id: int,
    username: str | None,
    first_name: str | None,
    casino_name: str,
    casino_link: str | None,
    amount_lost: str | None,
    description: str,
    screenshot_ids: list[str],
) -> Report:
    async with async_session() as session:
        report = Report(
            user_id=user_id,
            username=username,
            first_name=first_name,
            casino_name=casino_name,
            casino_link=casino_link,
            amount_lost=amount_lost,
            description=description,
        )
        report.set_screenshots(screenshot_ids)
        session.add(report)
        await session.commit()
        await session.refresh(report)
        return report


async def update_report_channel_msg(report_id: int, message_id: int, grid_image_id: str | None = None) -> None:
    async with async_session() as session:
        report = await session.get(Report, report_id)
        if report:
            report.channel_message_id = message_id
            if grid_image_id:
                report.grid_image_id = grid_image_id
            await session.commit()


async def search_reports(query: str) -> list[Report]:
    async with async_session() as session:
        stmt = (
            select(Report)
            .where(Report.casino_name.ilike(f"%{query}%"))
            .order_by(Report.created_at.desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def check_link(link: str) -> list[Report]:
    async with async_session() as session:
        stmt = (
            select(Report)
            .where(Report.casino_link.ilike(f"%{link}%"))
            .order_by(Report.created_at.desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_stats() -> dict:
    async with async_session() as session:
        total = await session.scalar(select(func.count(Report.id)))

        # Top 5 most reported casinos
        stmt = (
            select(Report.casino_name, func.count(Report.id).label("count"))
            .group_by(Report.casino_name)
            .order_by(func.count(Report.id).desc())
            .limit(5)
        )
        result = await session.execute(stmt)
        top_casinos = [(row[0], row[1]) for row in result.all()]

        return {"total": total or 0, "top_casinos": top_casinos}


async def get_report_by_id(report_id: int) -> Report | None:
    async with async_session() as session:
        return await session.get(Report, report_id)


async def delete_report(report_id: int) -> bool:
    async with async_session() as session:
        report = await session.get(Report, report_id)
        if report:
            await session.delete(report)
            await session.commit()
            return True
        return False


# ── Ban CRUD ──────────────────────────────────────────────────────


async def ban_user(user_id: int, banned_by: int, reason: str | None = None) -> BannedUser:
    async with async_session() as session:
        banned = BannedUser(user_id=user_id, banned_by=banned_by, reason=reason)
        await session.merge(banned)
        await session.commit()
        return banned


async def unban_user(user_id: int) -> bool:
    async with async_session() as session:
        user = await session.get(BannedUser, user_id)
        if user:
            await session.delete(user)
            await session.commit()
            return True
        return False


async def is_banned(user_id: int) -> bool:
    async with async_session() as session:
        user = await session.get(BannedUser, user_id)
        return user is not None


async def get_banned_list() -> list[BannedUser]:
    async with async_session() as session:
        result = await session.execute(
            select(BannedUser).order_by(BannedUser.banned_at.desc())
        )
        return list(result.scalars().all())
