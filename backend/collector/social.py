"""
TrendScope — Social Media Data Collector
Sammelt Posts von Reddit, YouTube und X/Twitter über deren offizielle APIs.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── DATENMODELL ──────────────────────────────────────────────

def make_post(
    text: str,
    platform: str,
    external_id: str,
    likes: int = 0,
    shares: int = 0,
    url: str = "",
    author: str = "",
    keywords: list[str] | None = None,
) -> dict:
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
        "sentiment": 0.0,   # wird später durch NLP befüllt
    }


# ── REDDIT COLLECTOR ──────────────────────────────────────────

class RedditCollector:
    """
    Nutzt die Reddit API (OAuth2) um Posts aus Hot/New/Rising zu sammeln.
    Docs: https://www.reddit.com/dev/api
    """

    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    API_URL   = "https://oauth.reddit.com"

    def __init__(self):
        self.client_id     = settings.reddit_client_id
        self.client_secret = settings.reddit_client_secret
        self.user_agent    = settings.reddit_user_agent
        self._token: str | None = None

    async def _get_token(self, session: aiohttp.ClientSession) -> str:
        if self._token:
            return self._token
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        data = {"grant_type": "client_credentials"}
        headers = {"User-Agent": self.user_agent}
        async with session.post(self.TOKEN_URL, auth=auth, data=data, headers=headers) as r:
            r.raise_for_status()
            js = await r.json()
            self._token = js["access_token"]
            return self._token

    async def collect(
        self,
        subreddits: list[str] | None = None,
        limit: int = 25,
    ) -> list[dict]:
        """Sammelt Posts aus den angegebenen Subreddits (Standard: r/worldnews, r/technology …)."""
        if not self.client_id or not self.client_secret:
            logger.warning("Reddit API-Key fehlt — übersprungen")
            return []

        subreddits = subreddits or [
            "worldnews", "technology", "science", "politics",
            "gaming", "Music", "Fitness", "investing",
        ]
        posts = []
        async with aiohttp.ClientSession() as session:
            try:
                token = await self._get_token(session)
                headers = {
                    "Authorization": f"bearer {token}",
                    "User-Agent": self.user_agent,
                }
                for sub in subreddits:
                    url = f"{self.API_URL}/r/{sub}/hot.json?limit={limit}"
                    async with session.get(url, headers=headers) as r:
                        if r.status != 200:
                            logger.warning("Reddit r/%s: HTTP %s", sub, r.status)
                            continue
                        data = await r.json()
                        children = data.get("data", {}).get("children", [])
                        for child in children:
                            p = child.get("data", {})
                            text = f"{p.get('title', '')} {p.get('selftext', '')}".strip()
                            posts.append(make_post(
                                text=text,
                                platform="Reddit",
                                external_id=p.get("id", ""),
                                likes=p.get("ups", 0),
                                shares=p.get("num_comments", 0),
                                url=f"https://reddit.com{p.get('permalink', '')}",
                                author=p.get("author", ""),
                            ))
            except Exception as e:
                logger.error("Reddit Collector Fehler: %s", e)

        logger.info("Reddit: %d Posts gesammelt", len(posts))
        return posts


# ── YOUTUBE COLLECTOR ─────────────────────────────────────────

class YouTubeCollector:
    """
    Nutzt die YouTube Data API v3 um Trending-Videos zu sammeln.
    Docs: https://developers.google.com/youtube/v3
    """

    SEARCH_URL   = "https://www.googleapis.com/youtube/v3/search"
    VIDEOS_URL   = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self):
        self.api_key = settings.youtube_api_key

    async def collect(
        self,
        queries: list[str] | None = None,
        limit: int = 20,
        region: str = "DE",
    ) -> list[dict]:
        if not self.api_key:
            logger.warning("YouTube API-Key fehlt — übersprungen")
            return []

        queries = queries or ["trending", "viral", "news today", "tech 2025"]
        posts = []

        async with aiohttp.ClientSession() as session:
            for query in queries:
                params = {
                    "key": self.api_key,
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": limit,
                    "regionCode": region,
                    "relevanceLanguage": "de",
                    "order": "viewCount",
                }
                try:
                    async with session.get(self.SEARCH_URL, params=params) as r:
                        r.raise_for_status()
                        data = await r.json()
                        for item in data.get("items", []):
                            snippet = item.get("snippet", {})
                            vid_id  = item.get("id", {}).get("videoId", "")
                            text = f"{snippet.get('title', '')} {snippet.get('description', '')}".strip()
                            posts.append(make_post(
                                text=text,
                                platform="YouTube",
                                external_id=vid_id,
                                url=f"https://youtube.com/watch?v={vid_id}",
                                author=snippet.get("channelTitle", ""),
                            ))
                except Exception as e:
                    logger.error("YouTube Collector Fehler (query=%s): %s", query, e)

        logger.info("YouTube: %d Videos gesammelt", len(posts))
        return posts


# ── TWITTER/X COLLECTOR ───────────────────────────────────────

class TwitterCollector:
    """
    Nutzt die Twitter API v2 (Bearer Token) um aktuelle Tweets zu sammeln.
    Docs: https://developer.twitter.com/en/docs/twitter-api
    """

    SEARCH_URL  = "https://api.twitter.com/2/tweets/search/recent"
    TRENDS_URL  = "https://api.twitter.com/1.1/trends/place.json"

    def __init__(self):
        self.bearer = settings.twitter_bearer_token

    async def collect(
        self,
        queries: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        if not self.bearer:
            logger.warning("Twitter Bearer Token fehlt — übersprungen")
            return []

        queries = queries or [
            "trending -is:retweet lang:de",
            "AI -is:retweet lang:de",
            "Nachrichten -is:retweet lang:de",
            "viral -is:retweet lang:en",
        ]
        posts = []
        headers = {"Authorization": f"Bearer {self.bearer}"}

        async with aiohttp.ClientSession() as session:
            for query in queries:
                params = {
                    "query": query,
                    "max_results": min(limit, 100),
                    "tweet.fields": "public_metrics,author_id,created_at",
                }
                try:
                    async with session.get(self.SEARCH_URL, params=params, headers=headers) as r:
                        if r.status == 429:
                            logger.warning("Twitter Rate Limit erreicht")
                            break
                        r.raise_for_status()
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
                    logger.error("Twitter Collector Fehler: %s", e)

        logger.info("Twitter/X: %d Tweets gesammelt", len(posts))
        return posts


# ── ORCHESTRIERUNG ────────────────────────────────────────────

async def collect_all(limit: int | None = None) -> list[dict]:
    """
    Startet alle Collector parallel und gibt alle Posts als Liste zurück.
    """
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

    all_posts: list[dict] = []
    for r in results:
        if isinstance(r, list):
            all_posts.extend(r)
        else:
            logger.error("Collector Exception: %s", r)

    logger.info("Gesamt gesammelt: %d Posts", len(all_posts))
    return all_posts
