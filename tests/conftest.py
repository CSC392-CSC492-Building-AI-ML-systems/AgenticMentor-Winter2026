"""Pytest configuration: project root on path (so 'src' imports work), load .env for integration tests."""
from pathlib import Path
import sys

# Add project root to sys.path so tests can "from src. ..." when run via pytest from project root or terminal
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def pytest_configure(config):
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parents[1]
        env = root / ".env"
        if env.exists():
            load_dotenv(env)
    except ImportError:
        pass
