"""
TrendScope — FastAPI Backend Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api.routes import trends, forecast, health, collect
from db.mongo import connect_mongo, close_mongo
from db.postgres import connect_postgres, close_postgres

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle."""
    logger.info("🚀 TrendScope starting up...")
    await connect_mongo()
    await connect_postgres()
    yield
    logger.info("🛑 TrendScope shutting down...")
    await close_mongo()
    await close_postgres()


app = FastAPI(
    title="TrendScope API",
    description="Analyse und Vorhersage globaler Social-Media-Trends",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # In Produktion einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router registrieren ──────────────────────────────
app.include_router(health.router,  prefix="/api",          tags=["Health"])
app.include_router(trends.router,  prefix="/api/trends",   tags=["Trends"])
app.include_router(forecast.router,prefix="/api/forecast", tags=["Prognose"])
app.include_router(collect.router, prefix="/api/collect",  tags=["Datensammlung"])


@app.get("/", tags=["Root"])
async def root():
    return {"message": "TrendScope API läuft ✅", "docs": "/docs"}
