"""Configuration utilities for environment-driven settings."""
from __future__ import annotations
import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _gemini_key_default() -> str:
    """Use GEMINI_API_KEY first; fall back to GOOGLE_API_KEY (same key, legacy name)."""
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    
    # Model Configuration
    # Gemini LLM: set GEMINI_API_KEY (or GOOGLE_API_KEY – same key, legacy name).
    gemini_api_key: str = Field(default_factory=_gemini_key_default)
    model_name: str = "gemini-2.5-flash"
    model_temperature: float = 0.7
    model_max_tokens: int = 4096

    # Firebase Authentication configuration
    # Path to a Firebase service account JSON file on disk.
    # This file should NOT be committed to source control; point to it via environment variable.
    firebase_service_account_path: str | None = None

    # Web API key from your Firebase project settings (used for email/password auth via REST).
    firebase_api_key: str | None = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

def load_config() -> dict:
    """Load configuration values from environment variables."""
    return {
        "app_env": os.getenv("APP_ENV", "development"),
    }

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()