from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://app:changeme@localhost:5432/reel_processor"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    WHISPER_MODEL: str = "base"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
