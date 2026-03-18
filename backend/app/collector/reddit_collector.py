import requests

URL = "https://www.reddit.com/r/all/top.json?limit=10"

HEADERS = {
    "User-Agent": "TrendScope/0.1"
}

def fetch_reddit_posts():
    response = requests.get(URL, headers=HEADERS)

    if response.status_code != 200:
        return []

    data = response.json()

    posts = []

    for post in data["data"]["children"]:
        posts.append({
            "title": post["data"]["title"],
            "score": post["data"]["score"]
        })

    return posts