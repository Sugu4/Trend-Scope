"""
API Route: /api/forecast
"""

from fastapi import APIRouter, Query
from ml.scoring import forecast_trend, batch_forecast, _classify_signal

router = APIRouter()


@router.get("/", summary="Prognosen für Top-Trends")
async def get_forecasts(
    days: int = Query(30, ge=7, le=90, description="Prognosezeitraum in Tagen"),
    limit: int = Query(10, ge=1, le=30),
):
    """
    Erstellt ML-Prognosen für die wichtigsten aktuellen Trends.
    """
    # Historische Daten aus DB laden (oder Demo-Daten)
    history = _get_demo_history()
    results = batch_forecast(history, forecast_days=days)
    return {"days": days, "forecasts": results[:limit]}


@router.get("/keyword/{keyword}", summary="Prognose für einzelnes Keyword")
async def get_keyword_forecast(
    keyword: str,
    days: int = Query(30, ge=7, le=90),
):
    """Erstellt eine detaillierte Prognose für ein spezifisches Keyword."""
    history = _get_demo_history()
    hist = history.get(keyword)
    if hist is None:
        # Generische Prognose mit Standardwerten
        hist = [50.0, 52.0, 55.0, 54.0, 58.0, 61.0, 63.0]

    result = forecast_trend(keyword, hist, forecast_days=days)
    return result


@router.get("/emerging", summary="Aufsteigende Trends")
async def get_emerging(limit: int = Query(5, ge=1, le=20)):
    """Gibt Trends zurück die stark wachsen (Signal: Emerging / Rising)."""
    history = _get_demo_history()
    all_fc = batch_forecast(history, forecast_days=14)
    emerging = [f for f in all_fc if f["signal"] in ("Emerging", "Rising")]
    return emerging[:limit]


@router.get("/declining", summary="Absinkende Trends")
async def get_declining(limit: int = Query(5, ge=1, le=20)):
    """Gibt Trends zurück die an Bedeutung verlieren."""
    history = _get_demo_history()
    all_fc = batch_forecast(history, forecast_days=14)
    declining = [f for f in all_fc if f["signal"] in ("Falling", "Cooling")]
    return declining[:limit]


def _get_demo_history() -> dict[str, list[float]]:
    """Demo-Verlaufsdaten für Prognose-Entwicklung."""
    return {
        "AI & Machine Learning":  [72, 75, 78, 80, 84, 88, 91, 93, 96],
        "Klimawandel":             [65, 68, 70, 72, 74, 78, 82, 86, 89],
        "Kryptowährung":           [55, 60, 58, 65, 70, 72, 77, 80, 85],
        "Quantum Computing":       [20, 22, 25, 28, 33, 39, 46, 55, 64],
        "Metaverse XR":            [85, 82, 78, 75, 74, 76, 77, 78, 78],
        "NFT Marketplace":         [90, 82, 74, 65, 55, 48, 42, 38, 33],
        "Green Hydrogen":          [30, 33, 37, 42, 48, 54, 61, 68, 75],
        "Gaming 2025":             [60, 62, 65, 68, 70, 72, 75, 78, 82],
        "Veganer Lifestyle":       [50, 52, 54, 55, 57, 58, 59, 60, 59],
        "Web3 Gaming":             [70, 65, 60, 54, 48, 42, 38, 34, 30],
    }
