from fastapi import FastAPI, HTTPException
from app.collector.reddit_collector import fetch_reddit_posts
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Alles ready?
    print("TrendScope startet...")
    yield
    # Shutdown: Cleanup (optional)
    print("TrendScope stoppt.")

app = FastAPI(title="TrendScope", lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "TrendScope API läuft ✅"}

@app.get("/collect")
def collect_data():
    posts = fetch_reddit_posts()
    if not posts:
        raise HTTPException(status_code=500, detail="Keine Posts geholt (Reddit/Mongo-Fehler)")
    return {"stored_posts": posts, "count": len(posts)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
