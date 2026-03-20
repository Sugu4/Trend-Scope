"""
API Route: /api/forecast — Echte ML-Prognosen aus PostgreSQL-Daten
"""

from fastapi import APIRouter, Query
from ml.scoring import forecast_trend, batch_forecast

router = APIRouter()


async def _get_real_history() -> dict[str, list[float]]:
    """
    Lädt echte Trend-Scores aus PostgreSQL.
    Gruppiert nach Keyword und sortiert nach Zeit.
    """
    from db.postgres import _SessionLocal, TrendResult
    from sqlalchemy import select

    history = {}

    try:
        if _SessionLocal:
            async with _SessionLocal() as session:
                result = await session.execute(
                    select(TrendResult.keyword, TrendResult.score, TrendResult.calculated_at)
                    .order_by(TrendResult.keyword, TrendResult.calculated_at)
                )
                rows = result.fetchall()

                for keyword, score, _ in rows:
                    if keyword not in history:
                        history[keyword] = []
                    history[keyword].append(float(score))
    except Exception:
        pass

    return history


@router.get("/", summary="Prognosen für alle Trends")
async def get_forecasts(
    days: int = Query(30, ge=7, le=90),
    limit: int = Query(10, ge=1, le=30),
):
    history = await _get_real_history()
    if not history:
        return {"days": days, "forecasts": [], "message": "Noch keine Daten — bitte erst /api/collect/run ausführen"}

    results = batch_forecast(history, forecast_days=days)
    return {"days": days, "forecasts": results[:limit]}


@router.get("/emerging", summary="Aufsteigende Trends")
async def get_emerging(limit: int = Query(5, ge=1, le=20)):
    history = await _get_real_history()
    if not history:
        return []

    all_fc = batch_forecast(history, forecast_days=14)
    emerging = [f for f in all_fc if f["signal"] in ("Emerging", "Rising", "Stable")]
    return emerging[:limit]


@router.get("/declining", summary="Absinkende Trends")
async def get_declining(limit: int = Query(5, ge=1, le=20)):
    history = await _get_real_history()
    if not history:
        return []

    all_fc = batch_forecast(history, forecast_days=14)
    declining = [f for f in all_fc if f["signal"] in ("Falling", "Cooling", "Slowing")]
    return declining[:limit]


@router.get("/keyword/{keyword}", summary="Prognose für einzelnes Keyword")
async def get_keyword_forecast(
    keyword: str,
    days: int = Query(30, ge=7, le=90),
):
    history = await _get_real_history()
    hist = history.get(keyword)

    if not hist:
        # Keyword nicht in DB — versuche ähnliches zu finden
        similar = [k for k in history if keyword.lower() in k.lower()]
        if similar:
            hist = history[similar[0]]
        else:
            return {"error": f"Keyword '{keyword}' nicht gefunden", "available": list(history.keys())[:10]}

    return forecast_trend(keyword, hist, forecast_days=days)
