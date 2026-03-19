import requests
from typing import List, Dict
from app.models.db.mongodb import posts_collection

URL = "https://www.reddit.com/r/all/top.json?limit=10"
HEADERS = {
    "User-Agent": "TrendScope/0.1 by /u/yourusername"}

def fetch_reddit_posts() -> List[Dict]:
    """Holt 10 Top-Posts von /r/all und speichert sie (ohne Duplikate)."""
    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"Reddit API Error: {response.status_code}")
            return []

        data = response.json()
        posts_data: List[Dict] = []

        
        for post in data["data"]["children"]:
            post_data = {
                "title": post["data"]["title"],
                "score": post["data"]["score"],
                "url": post["data"]["url"],  # Extra: Post-URL hinzugefügt
                "subreddit": post["data"]["subreddit"],
                "created_utc": post["data"]["created_utc"]
            }
            posts_data.append(post_data)

        # Bulk-Insert (schnell + effizient)
        if posts_data:
            posts_collection.insert_many(posts_data)

        return posts_data

    except Exception as e:
        print(f"Fehler beim Fetchen: {e}")
        return []
