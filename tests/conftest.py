"""Pytest configuration: load .env from project root for integration tests."""
from pathlib import Path

def pytest_configure(config):
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parents[1]
        env = root / ".env"
        if env.exists():
            load_dotenv(env)
    except ImportError:
        pass
