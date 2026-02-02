from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Additional agents can be placed in this file.
    """
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    
    # Model Configuration
    gemini_api_key: str
    model_name: str = "gemini-1.5-flash"
    model_temperature: float = 0.7
    model_max_tokens: int = 4096
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings for model"""
    return Settings()

# Global settings instance
settings = get_settings()