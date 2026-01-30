"""
Configuration settings for BiZhen backend.

Uses pydantic-settings for environment variable management.
All sensitive values are loaded from environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Database ---
    db_url: str = "postgresql://bizhen_user:bizhen_pass@localhost:5432/bizhen"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- ChromaDB ---
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # --- DeepSeek API ---
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-chat"
    deepseek_reasoner_model: str = "deepseek-reasoner"

    # --- Security ---
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_hours: int = 24

    # --- Application ---
    debug: bool = False
    api_prefix: str = "/api"


# Global settings instance
settings = Settings()
