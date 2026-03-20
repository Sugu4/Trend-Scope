"""
API Route: /api/trends
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from db.elastic import get_top_keywords
from db.postgres import get_top_trends
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
    limit: int = Query(10, ge=1, le=50, description="Anzahl der Trends"),
    category: str | None = Query(None, description="Filter nach Kategorie"),
    platform: str | None = Query(None, description="Filter nach Plattform"),
    time_window: str = Query("now-24h/h", description="Elasticsearch Zeitfenster"),
):
    """
    Gibt die aktuellen Top-Trends zurück.
    Datenquelle: PostgreSQL (falls befüllt) → Elasticsearch-Aggregation → Mock-Daten.
    """
    # 1. Versuche PostgreSQL (bereits berechnete Ergebnisse)
    pg_results = await get_top_trends(limit=limit, category=category)
    if pg_results:
        return pg_results

    # 2. Fallback: Live-Aggregation aus Elasticsearch
    keywords = await get_top_keywords(platform=platform, time_window=time_window, top_n=limit)
    if keywords:
        trends = build_trend_results(keywords, platform=platform or "mixed")
        return trends[:limit]

    # 3. Mock-Daten (wenn keine DB läuft)
    return _mock_trends(limit, category)


@router.get("/search", summary="Trends durchsuchen")
async def search_trends(
    q: str = Query(..., min_length=2, description="Suchbegriff"),
    limit: int = Query(10, ge=1, le=50),
):
    """Volltextsuche über Trends und Keywords."""
    from db.elastic import search_trends as es_search
    results = await es_search(q=q, size=limit)
    if not results:
        return {"query": q, "results": [], "message": "Keine Ergebnisse gefunden"}
    return {"query": q, "results": results}


def _mock_trends(limit: int, category: str | None) -> list[dict]:
    """Demo-Daten wenn keine Datenbank erreichbar."""
    from datetime import datetime, timezone
    data = [
        {"keyword": "AI & Machine Learning", "platform": "X",         "category": "tech",          "score": 96.0, "mention_count": 48200, "growth_rate": 0.24, "sentiment": 0.3},
        {"keyword": "Klimawandel 2025",       "platform": "Reddit",    "category": "politik",        "score": 89.0, "mention_count": 37500, "growth_rate": 0.18, "sentiment": -0.2},
        {"keyword": "Kryptowährung",          "platform": "X",         "category": "wirtschaft",     "score": 85.0, "mention_count": 33100, "growth_rate": 0.31, "sentiment": 0.1},
        {"keyword": "FIFA 2025",              "platform": "TikTok",    "category": "sport",          "score": 82.0, "mention_count": 29600, "growth_rate": 0.12, "sentiment": 0.5},
        {"keyword": "Metaverse XR",           "platform": "YouTube",   "category": "tech",          "score": 78.0, "mention_count": 24100, "growth_rate": 0.09, "sentiment": 0.15},
        {"keyword": "MindfulMorning",         "platform": "Instagram", "category": "health",         "score": 74.0, "mention_count": 21800, "growth_rate": 0.22, "sentiment": 0.7},
        {"keyword": "Bundestagswahl",         "platform": "X",         "category": "politik",        "score": 71.0, "mention_count": 19300, "growth_rate": 0.07, "sentiment": -0.1},
        {"keyword": "Taylor Swift Tour",      "platform": "TikTok",    "category": "entertainment",  "score": 68.0, "mention_count": 17900, "growth_rate": 0.15, "sentiment": 0.8},
        {"keyword": "Open Source AI",         "platform": "Reddit",    "category": "tech",          "score": 64.0, "mention_count": 15400, "growth_rate": 0.19, "sentiment": 0.4},
        {"keyword": "Veganer Lifestyle",      "platform": "Instagram", "category": "health",         "score": 59.0, "mention_count": 13100, "growth_rate": 0.08, "sentiment": 0.6},
        {"keyword": "Gaming 2025",            "platform": "YouTube",   "category": "entertainment",  "score": 55.0, "mention_count": 11800, "growth_rate": 0.06, "sentiment": 0.3},
        {"keyword": "Erneuerbare Energie",    "platform": "Reddit",    "category": "wirtschaft",     "score": 51.0, "mention_count": 10200, "growth_rate": 0.14, "sentiment": 0.2},
    ]
    ts = datetime.now(timezone.utc).isoformat()
    for d in data:
        d["calculated_at"] = ts
    if category:
        data = [d for d in data if d["category"] == category]
    return data[:limit]
