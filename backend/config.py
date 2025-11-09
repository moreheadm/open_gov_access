"""
Configuration settings for the application.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://opengov:opengov@localhost:5432/open_gov_access"
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = os.getenv("PORT", 8000)

    # LLM
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

