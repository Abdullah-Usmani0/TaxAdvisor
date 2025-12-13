"""Configuration management using Pydantic settings"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    google_api_key: str
    tavily_api_key: str
    
    # Server Configuration
    frontend_url: str = "http://localhost:3000"
    port: int = 8000
    
    # Checkpoint Storage
    checkpoint_storage: Literal["memory", "postgres"] = "memory"
    
    # Optional: Database URL for production
    database_url: str | None = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

