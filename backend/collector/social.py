"""
TrendScope — Social Media Data Collector
Reddit (RSS - kein API-Key nötig), YouTube, Twitter
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator
import xml.etree.ElementTree as ET

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def make_post(text, platform, external_id, likes=0, shares=0, url="", author="", keywords=None):
    return {
        "text": text,
        "platform": platform,
        "external_id": external_id,
        "likes": likes,
        "shares": shares,
        "url": url,
        "author": author,
        "keywords": keywords or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sentiment": 0.0,
    }


# ── REDDIT RSS (kein API-Key nötig) ──────────────────────────

class RedditRSSCollector:
    """
    Nutzt Reddit's öffentlichen RSS-Feed — komplett kostenlos, kein Account nötig.
    Sammelt Posts aus den wichtigsten Subreddits.
    """

    SUBREDDITS = [
        "worldnews", "technology", "science", "politics",
        "business", "environment", "artificial", "Futurology",
        "Economics", "geopolitics", "space", "cybersecurity",
        "climate", "energy", "MachineLearning", "Bitcoin",
    ]

    async def collect(self, limit: int = 25) -> list[dict]:
        posts = []
        async with aiohttp.ClientSession() as session:
            for sub in self.SUBREDDITS:
                try:
                    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
                    headers = {"User-Agent": "TrendScope/1.0"}
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status == 200:
                            data = await r.json()
                            children = data.get("data", {}).get("children", [])
                            for child in children[:5]:
                                p = child.get("data", {})
                                title = p.get("title", "")
                                selftext = p.get("selftext", "")[:200]
                                text = f"{title} {selftext}".strip()
                                if text:
                                    posts.append(make_post(
                                        text=text,
                                        platform="Reddit",
                                        external_id=p.get("id", ""),
                                        likes=p.get("ups", 0),
                                        shares=p.get("num_comments", 0),
                                        url=f"https://reddit.com{p.get('permalink', '')}",
                                        author=p.get("author", ""),
                                    ))
                        elif r.status == 429:
                            logger.warning("Reddit Rate Limit für r/%s", sub)
                            await asyncio.sleep(2)
                except Exception as e:
                    logger.warning("Reddit r/%s Fehler: %s", sub, e)
                await asyncio.sleep(0.5)  # Höfliche Pause zwischen Requests

        logger.info("Reddit RSS: %d Posts gesammelt", len(posts))
        return posts


# ── REDDIT OAuth (optional, mit API-Key) ─────────────────────

class RedditCollector:
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    API_URL   = "https://oauth.reddit.com"

    def __init__(self):
        self.client_id     = settings.reddit_client_id
        self.client_secret = settings.reddit_client_secret
        self.user_agent    = settings.reddit_user_agent
        self._token        = None

    async def _get_token(self, session):
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        async with session.post(self.TOKEN_URL, auth=auth,
                                data={"grant_type": "client_credentials"},
                                headers={"User-Agent": self.user_agent}) as r:
            r.raise_for_status()
            js = await r.json()
            self._token = js["access_token"]
            return self._token

    async def collect(self, subreddits=None, limit=25) -> list[dict]:
        if not self.client_id or not self.client_secret:
            # Fallback auf RSS
            return await RedditRSSCollector().collect(limit=limit)

        subreddits = subreddits or RedditRSSCollector.SUBREDDITS
        posts = []
        async with aiohttp.ClientSession() as session:
            try:
                token = await self._get_token(session)
                headers = {"Authorization": f"bearer {token}", "User-Agent": self.user_agent}
                for sub in subreddits:
                    url = f"{self.API_URL}/r/{sub}/hot.json?limit={limit}"
                    async with session.get(url, headers=headers) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                        for child in data.get("data", {}).get("children", []):
                            p = child.get("data", {})
                            text = f"{p.get('title', '')} {p.get('selftext', '')}".strip()
                            posts.append(make_post(
                                text=text, platform="Reddit",
                                external_id=p.get("id", ""),
                                likes=p.get("ups", 0),
                                shares=p.get("num_comments", 0),
                                url=f"https://reddit.com{p.get('permalink', '')}",
                                author=p.get("author", ""),
                            ))
            except Exception as e:
                logger.error("Reddit OAuth Fehler: %s — versuche RSS", e)
                return await RedditRSSCollector().collect(limit=limit)

        logger.info("Reddit OAuth: %d Posts", len(posts))
        return posts


# ── YOUTUBE ───────────────────────────────────────────────────

class YouTubeCollector:
    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self):
        self.api_key = settings.youtube_api_key

    async def collect(self, queries=None, limit=20, region="DE") -> list[dict]:
        if not self.api_key:
            logger.warning("YouTube API-Key fehlt")
            return []

        queries = queries or [
            "AI artificial intelligence 2026",
            "climate change global warming",
            "cryptocurrency bitcoin ethereum",
            "politics election news",
            "technology innovation science",
            "space NASA discovery",
            "economy inflation recession",
            "cybersecurity hacking data breach",
            "renewable energy solar",
            "geopolitics world news",
        ]
        posts = []
        async with aiohttp.ClientSession() as session:
            for query in queries:
                try:
                    params = {
                        "key": self.api_key, "part": "snippet",
                        "q": query, "type": "video",
                        "maxResults": min(limit, 10),
                        "order": "viewCount",
                    }
                    async with session.get(self.SEARCH_URL, params=params,
                                           timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                        for item in data.get("items", []):
                            snippet = item.get("snippet", {})
                            vid_id  = item.get("id", {}).get("videoId", "")
                            text = f"{snippet.get('title', '')} {snippet.get('description', '')}".strip()
                            posts.append(make_post(
                                text=text, platform="YouTube",
                                external_id=vid_id,
                                url=f"https://youtube.com/watch?v={vid_id}",
                                author=snippet.get("channelTitle", ""),
                            ))
                except Exception as e:
                    logger.error("YouTube Fehler (query=%s): %s", query, e)

        logger.info("YouTube: %d Videos", len(posts))
        return posts


# ── TWITTER ───────────────────────────────────────────────────

class TwitterCollector:
    SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

    def __init__(self):
        self.bearer = settings.twitter_bearer_token

    async def collect(self, queries=None, limit=50) -> list[dict]:
        if not self.bearer:
            return []

        queries = queries or [
            "AI -is:retweet lang:en",
            "climate -is:retweet lang:en",
            "crypto -is:retweet lang:en",
        ]
        posts = []
        headers = {"Authorization": f"Bearer {self.bearer}"}
        async with aiohttp.ClientSession() as session:
            for query in queries:
                try:
                    params = {"query": query, "max_results": min(limit, 100),
                              "tweet.fields": "public_metrics"}
                    async with session.get(self.SEARCH_URL, params=params,
                                           headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status == 429:
                            break
                        if r.status != 200:
                            continue
                        data = await r.json()
                        for tweet in data.get("data", []):
                            metrics = tweet.get("public_metrics", {})
                            posts.append(make_post(
                                text=tweet.get("text", ""),
                                platform="X",
                                external_id=tweet.get("id", ""),
                                likes=metrics.get("like_count", 0),
                                shares=metrics.get("retweet_count", 0),
                            ))
                except Exception as e:
                    logger.error("Twitter Fehler: %s", e)

        logger.info("Twitter: %d Tweets", len(posts))
        return posts


# ── ORCHESTRIERUNG ────────────────────────────────────────────

async def collect_all(limit=None) -> list[dict]:
    n = limit or settings.collect_limit

    reddit  = RedditCollector()
    youtube = YouTubeCollector()
    twitter = TwitterCollector()

    results = await asyncio.gather(
        reddit.collect(limit=n),
        youtube.collect(limit=n // 2),
        twitter.collect(limit=n),
        return_exceptions=True,
    )

    all_posts = []
    for r in results:
        if isinstance(r, list):
            all_posts.extend(r)
        else:
            logger.error("Collector Fehler: %s", r)

    logger.info("Gesamt: %d Posts", len(all_posts))
    return all_posts
