"""
TrendScope — Trend Scoring & ML-Prognose
  1. Trend-Score Berechnung (gewichtete Formel)
  2. Kategorie-Klassifikation
  3. Zeitreihen-Prognose mit scikit-learn (Linear Regression + RandomForest)
"""

import logging
import math
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


# ── KATEGORIEN ────────────────────────────────────────────────

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "tech":          ["ai", "ki", "chatgpt", "robot", "software", "code", "python", "api", "cloud",
                      "crypto", "bitcoin", "blockchain", "nft", "metaverse", "xr", "ar", "vr",
                      "openai", "gpu", "chip", "quantum"],
    "politik":       ["wahl", "election", "regierung", "government", "politik", "bundestag",
                      "trump", "biden", "eu", "nato", "ukraine", "krieg", "war", "minister"],
    "wirtschaft":    ["aktie", "stock", "markt", "market", "börse", "inflation", "zinsen",
                      "euro", "dollar", "wirtschaft", "economy", "invest", "startup", "bank"],
    "sport":         ["fußball", "football", "soccer", "fifa", "nba", "nfl", "tennis",
                      "olympia", "sport", "tor", "goal", "bundesliga", "champions"],
    "entertainment": ["film", "movie", "serie", "netflix", "music", "song", "album",
                      "spotify", "youtube", "tiktok", "instagram", "viral", "meme", "game"],
    "health":        ["gesundheit", "health", "fitness", "workout", "diet", "mental",
                      "yoga", "schlaf", "sleep", "ernährung", "nutrition", "medizin"],
}


def classify_category(keywords: list[str]) -> str:
    """Klassifiziert einen Trend anhand seiner Keywords."""
    scores: dict[str, int] = defaultdict(int)
    for kw in keywords:
        kw_lower = kw.lower()
        for category, cat_keywords in CATEGORY_KEYWORDS.items():
            if any(ck in kw_lower for ck in cat_keywords):
                scores[category] += 1
    if not scores:
        return "general"
    return max(scores, key=scores.get)


# ── TREND SCORING ─────────────────────────────────────────────

def calculate_trend_score(
    mention_count: int,
    growth_rate: float,
    avg_sentiment: float,
    recency_weight: float = 1.0,
    engagement: float = 0.0,
) -> float:
    """
    Gewichtete Trend-Score Formel:
      - Erwähnungen (logarithmisch skaliert): 40%
      - Wachstumsrate: 35%
      - Sentiment (neutral gilt als gut): 10%
      - Recency: 10%
      - Engagement (Likes+Shares): 5%

    Rückgabe: Score 0–100
    """
    mention_score  = min(100, math.log1p(mention_count) * 10) * 0.40
    growth_score   = min(100, max(0, growth_rate * 100))      * 0.35
    sentiment_score = ((avg_sentiment + 1) / 2) * 100          * 0.10
    recency_score  = recency_weight * 100                       * 0.10
    engagement_score = min(100, math.log1p(engagement) * 8)    * 0.05

    raw = mention_score + growth_score + sentiment_score + recency_score + engagement_score
    return round(min(100.0, raw), 1)


def compute_growth_rate(current_count: int, previous_count: int) -> float:
    """Berechnet die prozentuale Wachstumsrate."""
    if previous_count == 0:
        return 1.0 if current_count > 0 else 0.0
    return round((current_count - previous_count) / previous_count, 4)


def build_trend_results(
    aggregated: list[dict],
    previous_counts: dict[str, int] | None = None,
    platform: str = "mixed",
) -> list[dict]:
    """
    Nimmt aggregierte Keyword-Daten (aus NLP-Pipeline) und berechnet
    vollständige Trend-Ergebnisse inkl. Score, Kategorie, Wachstumsrate.
    """
    previous_counts = previous_counts or {}
    results = []

    for item in aggregated:
        keyword  = item["keyword"]
        count    = item["count"]
        sentiment = item.get("avg_sentiment", 0.0)
        prev     = previous_counts.get(keyword, max(1, count - 5))
        growth   = compute_growth_rate(count, prev)
        category = classify_category([keyword])
        score    = calculate_trend_score(
            mention_count=count,
            growth_rate=growth,
            avg_sentiment=sentiment,
        )

        results.append({
            "keyword": keyword,
            "platform": platform,
            "category": category,
            "score": score,
            "mention_count": count,
            "growth_rate": growth,
            "sentiment": sentiment,
            "calculated_at": datetime.utcnow(),
        })

    # Sortiert nach Score
    return sorted(results, key=lambda x: x["score"], reverse=True)


# ── ML PROGNOSE ───────────────────────────────────────────────

def forecast_trend(
    keyword: str,
    history: list[float],
    forecast_days: int = 30,
) -> dict:
    """
    Erstellt eine Trend-Prognose mit scikit-learn.
    Nutzt lineare Regression + einfache Wachstumsmodellierung.

    history: Liste historischer Score-Werte (zeitlich aufsteigend)
    Gibt zurück: {keyword, forecast, confidence_low, confidence_high, signal}
    """
    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import PolynomialFeatures

        if len(history) < 3:
            return _simple_forecast(keyword, history, forecast_days)

        X = np.array(range(len(history))).reshape(-1, 1)
        y = np.array(history)

        # Polynomial Regression (Grad 2) für bessere Kurvenanpassung
        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_poly = poly.fit_transform(X)

        model = LinearRegression()
        model.fit(X_poly, y)

        # Prognose
        future_X = np.array(range(len(history), len(history) + forecast_days)).reshape(-1, 1)
        future_poly = poly.transform(future_X)
        predictions = model.predict(future_poly)
        predictions = np.clip(predictions, 0, 150).tolist()

        # Konfidenzintervall (±8%)
        conf_low  = [round(max(0, v * 0.92), 1) for v in predictions]
        conf_high = [round(min(150, v * 1.08), 1) for v in predictions]
        pred_round = [round(v, 1) for v in predictions]

        # Signal bestimmen
        recent_avg = float(np.mean(history[-3:]))
        future_avg = float(np.mean(predictions[-7:]))
        growth = (future_avg - recent_avg) / max(recent_avg, 1)

        signal = _classify_signal(growth)

        return {
            "keyword": keyword,
            "forecast": pred_round,
            "confidence_low": conf_low,
            "confidence_high": conf_high,
            "forecast_days": forecast_days,
            "signal": signal,
            "growth_rate_forecast": round(growth * 100, 1),
        }

    except ImportError:
        logger.warning("scikit-learn oder numpy nicht installiert — einfache Prognose")
        return _simple_forecast(keyword, history, forecast_days)
    except Exception as e:
        logger.error("Forecast-Fehler für '%s': %s", keyword, e)
        return _simple_forecast(keyword, history, forecast_days)


def _simple_forecast(keyword: str, history: list[float], days: int) -> dict:
    """Einfache lineare Extrapolation als Fallback."""
    if len(history) < 2:
        last = history[-1] if history else 50.0
        forecast = [round(last, 1)] * days
    else:
        delta = (history[-1] - history[0]) / len(history)
        last  = history[-1]
        forecast = [round(min(150, max(0, last + delta * i)), 1) for i in range(1, days + 1)]

    signal = "Stable"
    if len(forecast) >= 7:
        g = (sum(forecast[-7:]) / 7 - sum(forecast[:7]) / 7) / max(sum(forecast[:7]) / 7, 1)
        signal = _classify_signal(g)

    return {
        "keyword": keyword,
        "forecast": forecast,
        "confidence_low": [round(v * 0.9, 1) for v in forecast],
        "confidence_high": [round(v * 1.1, 1) for v in forecast],
        "forecast_days": days,
        "signal": signal,
        "growth_rate_forecast": 0.0,
    }


def _classify_signal(growth: float) -> str:
    if growth > 0.5:   return "Emerging"
    if growth > 0.15:  return "Rising"
    if growth > -0.10: return "Stable"
    if growth > -0.30: return "Cooling"
    return "Falling"


def batch_forecast(
    trend_history: dict[str, list[float]],
    forecast_days: int = 30,
) -> list[dict]:
    """
    Erstellt Prognosen für mehrere Keywords gleichzeitig.
    trend_history: {keyword: [score_day1, score_day2, ...]}
    """
    results = []
    for keyword, history in trend_history.items():
        fc = forecast_trend(keyword, history, forecast_days)
        results.append(fc)

    # Sortiert nach prognostizierter Wachstumsrate
    return sorted(results, key=lambda x: x.get("growth_rate_forecast", 0), reverse=True)
