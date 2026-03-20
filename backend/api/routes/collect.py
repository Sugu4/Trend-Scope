"""
API Route: /api/collect — Datensammlung manuell auslösen
"""

from fastapi import APIRouter, BackgroundTasks, Query
from datetime import datetime, timezone

router = APIRouter()


@router.post("/run", summary="Datensammlung starten")
async def trigger_collection(
    background_tasks: BackgroundTasks,
    limit: int = Query(50, ge=10, le=500, description="Posts pro Plattform"),
):
    """
    Startet einen Datensammlungs-Durchlauf im Hintergrund.
    Reihenfolge: Collect → NLP → Score → Speichern
    """
    background_tasks.add_task(_run_pipeline, limit)
    return {
        "status": "started",
        "message": f"Pipeline läuft im Hintergrund (limit={limit})",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status", summary="Status der letzten Collection")
async def collection_status():
    """Gibt Statistiken der letzten Datensammlungs-Runde zurück."""
    return {
        "last_run": _last_run,
        "total_posts": _total_posts,
        "platforms": _platform_counts,
    }


# ── Pipeline ─────────────────────────────────────────────────

_last_run: str | None = None
_total_posts: int = 0
_platform_counts: dict = {}


async def _run_pipeline(limit: int):
    global _last_run, _total_posts, _platform_counts
    import logging
    logger = logging.getLogger(__name__)

    try:
        # 1. Sammeln
        from collector.social import collect_all
        posts = await collect_all(limit=limit)

        # 2. NLP verarbeiten
        from nlp.pipeline import process_posts, aggregate_keywords
        processed = process_posts(posts)

        # 3. In MongoDB speichern
        from db.mongo import insert_posts
        await insert_posts(processed)

        # 4. In Elasticsearch indizieren
        from db.elastic import index_posts
        await index_posts(processed)

        # 5. Keyword-Aggregation
        aggregated = aggregate_keywords(processed, top_n=20)

        # 6. Trend-Score berechnen
        from ml.scoring import build_trend_results
        results = build_trend_results(aggregated)

        # 7. In PostgreSQL speichern
        from db.postgres import save_trend_results
        await save_trend_results(results)

        # Status aktualisieren
        _last_run = datetime.now(timezone.utc).isoformat()
        _total_posts = len(posts)
        _platform_counts = {}
        for p in posts:
            pl = p.get("platform", "unknown")
            _platform_counts[pl] = _platform_counts.get(pl, 0) + 1

        logger.info("✅ Pipeline abgeschlossen: %d Posts, %d Trends berechnet",
                    len(posts), len(results))

    except Exception as e:
        logger.error("❌ Pipeline-Fehler: %s", e)
