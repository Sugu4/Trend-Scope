"""
TrendScope — Social Media & News Data Collector
Quellen: Reddit (RSS), YouTube, NewsAPI, GitHub Trending
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
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


# ── REDDIT RSS (kein API-Key) ─────────────────────────────────

class RedditCollector:
    SUBREDDITS = [
        "worldnews", "technology", "science", "politics",
        "business", "environment", "Futurology", "Economics",
        "geopolitics", "space", "cybersecurity", "MachineLearning",
        "Bitcoin", "climate", "energy", "artificial",
    ]

    async def collect(self, limit: int = 25) -> list[dict]:
        posts = []
        async with aiohttp.ClientSession() as session:
            for sub in self.SUBREDDITS:
                try:
                    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=8"
                    headers = {"User-Agent": "TrendScope/1.0"}
                    async with session.get(url, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status == 200:
                            data = await r.json()
                            for child in data.get("data", {}).get("children", [])[:5]:
                                p = child.get("data", {})
                                text = f"{p.get('title', '')} {p.get('selftext', '')[:150]}".strip()
                                if text:
                                    posts.append(make_post(
                                        text=text, platform="Reddit",
                                        external_id=p.get("id", ""),
                                        likes=p.get("ups", 0),
                                        shares=p.get("num_comments", 0),
                                        url=f"https://reddit.com{p.get('permalink', '')}",
                                        author=p.get("author", ""),
                                    ))
                        elif r.status == 429:
                            await asyncio.sleep(3)
                except Exception as e:
                    logger.warning("Reddit r/%s: %s", sub, e)
                await asyncio.sleep(0.4)

        logger.info("Reddit: %d Posts", len(posts))
        return posts


# ── YOUTUBE ───────────────────────────────────────────────────

class YouTubeCollector:
    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

    QUERIES = [
        "AI artificial intelligence 2026",
        "climate change global warming",
        "cryptocurrency bitcoin ethereum",
        "politics election world news",
        "technology innovation breakthrough",
        "space NASA discovery",
        "economy inflation recession",
        "cybersecurity hacking",
        "renewable energy solar wind",
        "geopolitics world conflict",
    ]

    def __init__(self):
        self.api_key = settings.youtube_api_key

    async def collect(self, limit: int = 20) -> list[dict]:
        if not self.api_key:
            logger.warning("YouTube API-Key fehlt")
            return []

        posts = []
        async with aiohttp.ClientSession() as session:
            for query in self.QUERIES:
                try:
                    params = {
                        "key": self.api_key, "part": "snippet",
                        "q": query, "type": "video",
                        "maxResults": 8, "order": "viewCount",
                    }
                    async with session.get(self.SEARCH_URL, params=params,
                                           timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                        for item in data.get("items", []):
                            snippet = item.get("snippet", {})
                            vid_id = item.get("id", {}).get("videoId", "")
                            text = f"{snippet.get('title', '')} {snippet.get('description', '')[:150]}".strip()
                            posts.append(make_post(
                                text=text, platform="YouTube",
                                external_id=vid_id,
                                url=f"https://youtube.com/watch?v={vid_id}",
                                author=snippet.get("channelTitle", ""),
                            ))
                except Exception as e:
                    logger.error("YouTube (query=%s): %s", query, e)

        logger.info("YouTube: %d Videos", len(posts))
        return posts


# ── NEWSAPI (kostenlos, 100 Anfragen/Tag) ─────────────────────

class NewsAPICollector:
    """
    NewsAPI.org — kostenlos bis 100 Anfragen/Tag.
    API-Key beantragen: https://newsapi.org/register
    """
    URL = "https://newsapi.org/v2/top-headlines"
    EVERYTHING_URL = "https://newsapi.org/v2/everything"

    def __init__(self):
        self.api_key = getattr(settings, 'newsapi_key', '')

    async def collect(self, limit: int = 30) -> list[dict]:
        if not self.api_key:
            logger.info("NewsAPI Key fehlt — übersprungen (https://newsapi.org/register)")
            return []

        posts = []
        categories = ["technology", "science", "business", "health", "general"]

        async with aiohttp.ClientSession() as session:
            for category in categories:
                try:
                    params = {
                        "apiKey": self.api_key,
                        "category": category,
                        "language": "en",
                        "pageSize": 10,
                    }
                    async with session.get(self.URL, params=params,
                                           timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                        for article in data.get("articles", []):
                            title = article.get("title", "")
                            desc  = article.get("description", "") or ""
                            text  = f"{title} {desc[:200]}".strip()
                            if text and text != "[Removed]":
                                posts.append(make_post(
                                    text=text,
                                    platform="NewsAPI",
                                    external_id=article.get("url", "")[-50:],
                                    likes=0,
                                    shares=0,
                                    url=article.get("url", ""),
                                    author=article.get("source", {}).get("name", ""),
                                ))
                except Exception as e:
                    logger.error("NewsAPI (category=%s): %s", category, e)

        logger.info("NewsAPI: %d Artikel", len(posts))
        return posts


# ── GITHUB TRENDING (kein API-Key) ────────────────────────────

class GitHubTrendingCollector:
    """
    GitHub Trending — komplett kostenlos, kein API-Key nötig.
    Scrapt die öffentliche GitHub API für trending Repos.
    """
    API_URL = "https://api.github.com/search/repositories"

    TOPICS = [
        "artificial-intelligence", "machine-learning", "blockchain",
        "climate-tech", "cybersecurity", "web3", "quantum-computing",
        "large-language-models", "autonomous-vehicles", "renewable-energy",
    ]

    async def collect(self, limit: int = 30) -> list[dict]:
        posts = []
        async with aiohttp.ClientSession() as session:
            for topic in self.TOPICS:
                try:
                    params = {
                        "q": f"topic:{topic}",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 5,
                    }
                    headers = {
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "TrendScope/1.0",
                    }
                    async with session.get(self.API_URL, params=params, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                        for repo in data.get("items", [])[:3]:
                            name = repo.get("full_name", "")
                            desc = repo.get("description", "") or ""
                            lang = repo.get("language", "") or ""
                            stars = repo.get("stargazers_count", 0)
                            text = f"{name} {desc} {lang} {topic.replace('-', ' ')}".strip()
                            posts.append(make_post(
                                text=text,
                                platform="GitHub",
                                external_id=str(repo.get("id", "")),
                                likes=stars,
                                shares=repo.get("forks_count", 0),
                                url=repo.get("html_url", ""),
                                author=repo.get("owner", {}).get("login", ""),
                            ))
                except Exception as e:
                    logger.warning("GitHub Trending (topic=%s): %s", topic, e)
                await asyncio.sleep(0.3)

        logger.info("GitHub Trending: %d Repos", len(posts))
        return posts


# ── ORCHESTRIERUNG ────────────────────────────────────────────

async def collect_all(limit=None) -> list[dict]:
    n = limit or settings.collect_limit

    collectors = [
        RedditCollector().collect(limit=n),
        YouTubeCollector().collect(limit=n // 2),
        NewsAPICollector().collect(limit=n),
        GitHubTrendingCollector().collect(limit=n),
    ]

    results = await asyncio.gather(*collectors, return_exceptions=True)

    all_posts = []
    platform_counts = {}
    for r in results:
        if isinstance(r, list):
            all_posts.extend(r)
            for p in r:
                pl = p.get("platform", "unknown")
                platform_counts[pl] = platform_counts.get(pl, 0) + 1
        else:
            logger.error("Collector Fehler: %s", r)

    logger.info("Gesamt: %d Posts — %s", len(all_posts), platform_counts)
    return all_posts
