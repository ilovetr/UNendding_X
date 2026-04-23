"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://agenthub:agenthub_secret@localhost:5432/agenthub"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://agenthub:agenthub_secret@localhost:5432/agenthub"

    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 15  # Access token: 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh token: 7 days

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # A2A Protocol
    A2A_VERSION: str = "1.0.0"
    AGENT_ENDPOINT: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
