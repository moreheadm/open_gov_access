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
        "postgresql://postgres:postgres@localhost:5432/supervisor_votes"
    )
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Scraper
    state_dir: str = "data/state"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

