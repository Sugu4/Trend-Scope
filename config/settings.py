"""
Zentrales Konfigurationsmodul — liest Werte aus .env
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Datenbanken
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "trendscope"

    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "trends"

    postgres_uri: str = "postgresql+asyncpg://postgres:password@localhost:5432/trendscope"

    # Social Media APIs
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "TrendScope/1.0"

    youtube_api_key: str = ""

    twitter_bearer_token: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    collect_limit: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
