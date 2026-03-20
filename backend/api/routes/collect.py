"""
API Route: /api/collect
"""

from fastapi import APIRouter, BackgroundTasks, Query
from datetime import datetime, timezone

router = APIRouter()

@router.post("/run", summary="Datensammlung starten")
async def trigger_collection(
    background_tasks: BackgroundTasks,
    limit: int = Query(50, ge=10, le=500),
):
    background_tasks.add_task(_run_pipeline, limit)
    return {
        "status": "started",
        "message": f"Pipeline läuft im Hintergrund (limit={limit})",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/status", summary="Status")
async def collection_status():
    return {"last_run": _last_run, "total_posts": _total_posts, "platforms": _platform_counts}

_last_run: str | None = None
_total_posts: int = 0
_platform_counts: dict = {}

def _clean_post(post: dict) -> dict:
    cleaned = {}
    for k, v in post.items():
        if k == "_id":
            continue
        try:
            import json
            json.dumps(v)
            cleaned[k] = v
        except (TypeError, ValueError):
            cleaned[k] = str(v)
    return cleaned

async def _run_pipeline(limit: int):
    global _last_run, _total_posts, _platform_counts
    import logging
    logger = logging.getLogger(__name__)
    try:
        # 1. Sammeln
        from collector.social import collect_all
        posts = await collect_all(limit=limit)
        posts = [_clean_post(p) for p in posts]

        # 2. NLP
        from nlp.pipeline import process_posts, aggregate_keywords
        processed = process_posts(posts)
        processed = [_clean_post(p) for p in processed]

        # 3. MongoDB
        from db.mongo import insert_posts
        await insert_posts(processed)

        # 4. Elasticsearch
        from db.elastic import index_posts
        await index_posts([{k: v for k, v in p.items() if k != "_id"} for p in processed])

        # 5. Aggregation & Deduplication
        aggregated = aggregate_keywords(processed, top_n=20)

        # 6. Scoring
        from ml.scoring import build_trend_results
        results = build_trend_results(aggregated)

        # 7. Alte Daten löschen dann neue speichern
        from db.postgres import _SessionLocal
        if _SessionLocal:
            from db.postgres import TrendResult
            from sqlalchemy import delete
            async with _SessionLocal() as session:
                await session.execute(delete(TrendResult))
                await session.commit()

        from db.postgres import save_trend_results
        await save_trend_results(results)

        _last_run = datetime.now(timezone.utc).isoformat()
        _total_posts = len(posts)
        _platform_counts = {}
        for p in posts:
            pl = p.get("platform", "unknown")
            _platform_counts[pl] = _platform_counts.get(pl, 0) + 1

        logger.info("✅ Pipeline: %d Posts, %d Trends", len(posts), len(results))

    except Exception as e:
        logger.error("❌ Pipeline-Fehler: %s", e)
