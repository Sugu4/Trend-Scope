"""
PostgreSQL — Verbindung & ORM-Modelle
Speichert berechnete Trend-Scores, Rankings und Prognosen strukturiert.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, Text
from datetime import datetime
import logging
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


# ── ORM-Modelle ─────────────────────────────────────────────

class TrendResult(Base):
    """Berechnetes Trend-Ergebnis (aggregiert, pro Stunde)."""
    __tablename__ = "trend_results"

    id: Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str]   = mapped_column(String(200), index=True)
    platform: Mapped[str]  = mapped_column(String(50), index=True)
    category: Mapped[str]  = mapped_column(String(50))
    score: Mapped[float]   = mapped_column(Float)
    mention_count: Mapped[int] = mapped_column(Integer)
    growth_rate: Mapped[float] = mapped_column(Float)
    sentiment: Mapped[float]   = mapped_column(Float, default=0.0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ForecastResult(Base):
    """ML-Prognose für einen Trend."""
    __tablename__ = "forecast_results"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str]     = mapped_column(String(200), index=True)
    forecast_score: Mapped[float]  = mapped_column(Float)
    confidence_low: Mapped[float]  = mapped_column(Float)
    confidence_high: Mapped[float] = mapped_column(Float)
    forecast_days: Mapped[int]     = mapped_column(Integer)
    signal: Mapped[str]            = mapped_column(String(50))   # Emerging, Rising, Falling…
    created_at: Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)


# ── Verbindung ────────────────────────────────────────────────

async def connect_postgres():
    global _engine, _SessionLocal
    try:
        _engine = create_async_engine(settings.postgres_uri, echo=False)
        _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ PostgreSQL verbunden")
    except Exception as e:
        logger.warning("⚠️  PostgreSQL nicht erreichbar: %s — Mock-Modus aktiv", e)
        _engine = None


async def close_postgres():
    global _engine
    if _engine:
        await _engine.dispose()


async def get_session() -> AsyncSession:
    if _SessionLocal is None:
        raise RuntimeError("PostgreSQL nicht verbunden")
    async with _SessionLocal() as session:
        yield session


async def save_trend_results(results: list[dict]) -> int:
    """Speichert eine Liste von Trend-Ergebnissen."""
    if _SessionLocal is None:
        return len(results)
    async with _SessionLocal() as session:
        rows = [TrendResult(**r) for r in results]
        session.add_all(rows)
        await session.commit()
    return len(rows)


async def get_top_trends(limit: int = 10, category: str | None = None) -> list[dict]:
    """
    Holt die neuesten Top-Trends aus PostgreSQL.
    Gibt pro Keyword nur den neuesten Eintrag zurück (für das Dashboard).
    """
    if _SessionLocal is None:
        return []
    from sqlalchemy import select, desc, func
    async with _SessionLocal() as session:
        # Subquery: neueste calculated_at pro Keyword
        subq = (
            select(TrendResult.keyword, func.max(TrendResult.calculated_at).label("max_at"))
            .group_by(TrendResult.keyword)
            .subquery()
        )
        q = (
            select(TrendResult)
            .join(subq, (TrendResult.keyword == subq.c.keyword) &
                        (TrendResult.calculated_at == subq.c.max_at))
            .order_by(desc(TrendResult.score))
            .limit(limit)
        )
        if category:
            q = q.where(TrendResult.category == category)
        result = await session.execute(q)
        rows = result.scalars().all()
        return [
            {
                "keyword": r.keyword,
                "platform": r.platform,
                "category": r.category,
                "score": round(r.score, 1),
                "mention_count": r.mention_count,
                "growth_rate": round(r.growth_rate, 2),
                "sentiment": round(r.sentiment, 2),
                "calculated_at": r.calculated_at.isoformat() if r.calculated_at else "",
            }
            for r in rows
        ]
