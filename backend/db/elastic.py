"""
Elasticsearch — Volltextsuche & Keyword-Aggregation
Analysiert gesammelte Texte, erkennt Trends in Echtzeit.
"""

from elasticsearch import AsyncElasticsearch, NotFoundError
import logging
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_es: AsyncElasticsearch | None = None

INDEX = settings.elasticsearch_index

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "text":       {"type": "text",    "analyzer": "standard"},
            "platform":   {"type": "keyword"},
            "keywords":   {"type": "keyword"},
            "created_at": {"type": "date"},
            "likes":      {"type": "integer"},
            "shares":     {"type": "integer"},
            "sentiment":  {"type": "float"},
        }
    }
}


async def connect_elasticsearch():
    global _es
    try:
        _es = AsyncElasticsearch(settings.elasticsearch_url, request_timeout=5)
        if not await _es.indices.exists(index=INDEX):
            await _es.indices.create(index=INDEX, body=INDEX_MAPPING)
            logger.info("Index '%s' angelegt", INDEX)
        logger.info("✅ Elasticsearch verbunden: %s", settings.elasticsearch_url)
    except Exception as e:
        logger.warning("⚠️  Elasticsearch nicht erreichbar: %s — Mock-Modus aktiv", e)
        _es = None


async def close_elasticsearch():
    if _es:
        await _es.close()


async def index_posts(posts: list[dict]) -> int:
    """Indiziert Posts in Elasticsearch."""
    if _es is None:
        return len(posts)
    from elasticsearch.helpers import async_bulk
    actions = [{"_index": INDEX, "_source": p} for p in posts]
    success, _ = await async_bulk(_es, actions)
    return success


async def get_top_keywords(
    platform: str | None = None,
    time_window: str = "now-24h/h",
    top_n: int = 20,
) -> list[dict]:
    """
    Aggregiert die häufigsten Keywords der letzten `time_window`.
    Gibt eine sortierte Liste mit keyword + count zurück.
    """
    if _es is None:
        # Mock-Daten wenn Elasticsearch nicht läuft
        return _mock_keywords()

    query = {
        "query": {
            "bool": {
                "must": [{"range": {"created_at": {"gte": time_window}}}],
                **({"filter": [{"term": {"platform": platform}}]} if platform else {}),
            }
        },
        "aggs": {
            "top_keywords": {
                "terms": {"field": "keywords", "size": top_n}
            }
        },
        "size": 0,
    }
    try:
        resp = await _es.search(index=INDEX, body=query)
        buckets = resp["aggregations"]["top_keywords"]["buckets"]
        return [{"keyword": b["key"], "count": b["doc_count"]} for b in buckets]
    except Exception as e:
        logger.error("Elasticsearch Abfrage fehlgeschlagen: %s", e)
        return _mock_keywords()


async def search_trends(q: str, size: int = 10) -> list[dict]:
    """Volltext-Suche über alle indizierten Posts."""
    if _es is None:
        return []
    body = {
        "query": {"multi_match": {"query": q, "fields": ["text", "keywords"]}},
        "size": size,
    }
    resp = await _es.search(index=INDEX, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def _mock_keywords() -> list[dict]:
    """Fallback-Daten wenn Elasticsearch offline."""
    return [
        {"keyword": "AI",              "count": 48200},
        {"keyword": "ChatGPT",         "count": 41000},
        {"keyword": "Klimawandel",     "count": 37500},
        {"keyword": "Bitcoin",         "count": 33100},
        {"keyword": "Bundestagswahl",  "count": 29800},
        {"keyword": "TikTok",          "count": 27400},
        {"keyword": "Metaverse",       "count": 24100},
        {"keyword": "Streaming",       "count": 22700},
        {"keyword": "GreenEnergy",     "count": 20300},
        {"keyword": "Gaming",          "count": 18900},
    ]
