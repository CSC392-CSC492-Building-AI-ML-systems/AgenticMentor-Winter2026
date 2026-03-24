"""Configuration utilities for environment-driven settings."""
from __future__ import annotations
import json
import os
from functools import lru_cache
from typing import Any, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always offer these for "app default key" mode in the UI and resolver (env cannot shrink below this).
# Note: Google AI Studio uses gemini-3-flash-preview for the Gemini 3 Flash API id (not gemini-3-flash).
_MIN_APP_DEFAULT_MODELS: tuple[str, ...] = ("gemini-2.5-flash", "gemini-3-flash-preview")


def _parse_model_list_env(value: Any) -> Any:
    """Parse list fields from env: JSON array, or comma-separated string."""
    if value is None or isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return [p.strip() for p in s.split(",") if p.strip()]
    return value


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
    # Broad text-model catalog shown in UI for custom-key mode.
    # Note: availability depends on the user's Google AI Studio account/tier.
    supported_custom_models: list[str] = Field(
        default_factory=lambda: [
            "gemini-2.5-flash",
            "gemini-3-flash-preview",
            "gemini-2.0-flash",
            "gemini-2.5-pro",
            "gemini-2-flash-exp",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-3.1-pro-preview",
            "gemini-3.1-flash-lite-preview",
        ]
    )
    allowed_default_models: list[str] = Field(
        default_factory=lambda: list(_MIN_APP_DEFAULT_MODELS)
    )

    @field_validator("allowed_default_models", "supported_custom_models", mode="before")
    @classmethod
    def _coerce_model_lists_from_env(cls, value: Any) -> Any:
        return _parse_model_list_env(value)

    @model_validator(mode="after")
    def _merge_min_default_models(self) -> Settings:
        seen: set[str] = set()
        merged: list[str] = []
        for m in (*_MIN_APP_DEFAULT_MODELS, *self.allowed_default_models):
            if m and m not in seen:
                seen.add(m)
                merged.append(m)
        self.allowed_default_models = merged
        return self

    # Firebase Authentication configuration
    # Path to a Firebase service account JSON file on disk.
    # This file should NOT be committed to source control; point to it via environment variable.
    firebase_service_account_path: Optional[str] = None

    # Web API key from your Firebase project settings (used for email/password auth via REST).
    firebase_api_key: Optional[str] = None
    
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