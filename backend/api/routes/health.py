"""
API Route: /api/health  — System-Status
"""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health", summary="System-Status")
async def health_check():
    """Gibt den Verbindungsstatus aller Systemkomponenten zurück."""
    from db.mongo import get_db as get_mongo
    from db.elastic import _es

    mongo_ok = get_mongo() is not None
    es_ok    = _es is not None

    # PostgreSQL prüfen
    pg_ok = False
    try:
        from db.postgres import _engine
        pg_ok = _engine is not None
    except Exception:
        pass

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "services": {
            "mongodb":       "connected" if mongo_ok else "mock-mode",
            "elasticsearch": "connected" if es_ok    else "mock-mode",
            "postgresql":    "connected" if pg_ok    else "mock-mode",
        },
    }
