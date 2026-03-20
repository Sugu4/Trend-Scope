"""
API Route: /api/trends — nur echte Daten, kein Fallback auf Mock
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from db.postgres import get_top_trends
from db.elastic import get_top_keywords
from ml.scoring import build_trend_results

router = APIRouter()


class TrendItem(BaseModel):
    keyword: str
    platform: str
    category: str
    score: float
    mention_count: int
    growth_rate: float
    sentiment: float
    calculated_at: str


@router.get("/", response_model=list[TrendItem], summary="Top-Trends abrufen")
async def get_trends(
    limit: int = Query(20, ge=1, le=50),
    category: str | None = Query(None),
    platform: str | None = Query(None),
    time_window: str = Query("now-24h/h"),
):
    # 1. PostgreSQL — berechnete Ergebnisse
    pg_results = await get_top_trends(limit=limit, category=category)
    if pg_results:
        return pg_results

    # 2. Elasticsearch — Live-Aggregation
    keywords = await get_top_keywords(platform=platform, time_window=time_window, top_n=limit)
    if keywords:
        trends = build_trend_results(keywords, platform=platform or "mixed")
        return trends[:limit]

    # 3. Leer — kein Mock mehr
    return []


@router.get("/search", summary="Trends durchsuchen")
async def search_trends(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
):
    from db.elastic import search_trends as es_search
    results = await es_search(q=q, size=limit)
    return {"query": q, "results": results or []}


@router.get("/stats", summary="Trend-Statistiken")
async def get_stats():
    """Gibt echte Statistiken zurück — Posts, Trends, Plattformen."""
    from db.postgres import _SessionLocal, TrendResult
    from db.mongo import get_db
    from sqlalchemy import select, func, distinct

    stats = {"total_trends": 0, "platforms": [], "top_categories": [], "total_posts": 0}

    try:
        if _SessionLocal:
            async with _SessionLocal() as session:
                # Anzahl Trends
                count = await session.execute(select(func.count()).select_from(TrendResult))
                stats["total_trends"] = count.scalar() or 0

                # Plattformen
                plats = await session.execute(
                    select(distinct(TrendResult.platform))
                )
                stats["platforms"] = [r[0] for r in plats.fetchall()]

                # Top Kategorien
                cats = await session.execute(
                    select(TrendResult.category, func.count().label("n"))
                    .group_by(TrendResult.category)
                    .order_by(func.count().desc())
                    .limit(5)
                )
                stats["top_categories"] = [{"category": r[0], "count": r[1]} for r in cats.fetchall()]
    except Exception:
        pass

    try:
        db = get_db()
        if db is not None:
            stats["total_posts"] = await db.posts.count_documents({})
    except Exception:
        pass

    return stats
