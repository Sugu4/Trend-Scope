"""
MongoDB — Verbindung & Helfer
Speichert rohe Social-Media-Posts (unstrukturiert, flexibel).
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_mongo():
    global _client, _db
    try:
        _client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
        await _client.admin.command("ping")
        _db = _client[settings.mongo_db]
        # Indizes anlegen
        await _db.posts.create_index([("platform", 1), ("created_at", -1)])
        await _db.posts.create_index([("keywords", 1)])
        logger.info("✅ MongoDB verbunden: %s", settings.mongo_uri)
    except Exception as e:
        logger.warning("⚠️  MongoDB nicht erreichbar: %s — Mock-Modus aktiv", e)
        _db = None


async def close_mongo():
    global _client
    if _client:
        _client.close()


def get_db() -> AsyncIOMotorDatabase | None:
    return _db


async def insert_posts(posts: list[dict]) -> int:
    """Fügt eine Liste von Posts ein. Gibt die Anzahl eingefügter Dokumente zurück."""
    if _db is None:
        logger.debug("Mock-Modus: insert_posts übersprungen")
        return len(posts)
    if not posts:
        return 0
    result = await _db.posts.insert_many(posts, ordered=False)
    return len(result.inserted_ids)


async def get_recent_posts(platform: str | None = None, limit: int = 500) -> list[dict]:
    """Liefert die neuesten Posts, optional gefiltert nach Plattform."""
    if _db is None:
        return []
    query = {"platform": platform} if platform else {}
    cursor = _db.posts.find(query).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
