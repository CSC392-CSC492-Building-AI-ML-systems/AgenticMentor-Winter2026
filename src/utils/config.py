"""Configuration utilities for environment-driven settings."""

from __future__ import annotations

import os


def load_config() -> dict:
    """Load configuration values from environment variables."""
    return {
        "app_env": os.getenv("APP_ENV", "development"),
    }
