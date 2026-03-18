from fastapi import FastAPI
from app.collector.reddit_collector import fetch_reddit_posts

app = FastAPI()

@app.get("/")
def root():
    return {"message": "TrendScope API läuft"}

@app.get("/reddit")
def get_reddit_data():
    posts = fetch_reddit_posts()
    return {"posts": posts}