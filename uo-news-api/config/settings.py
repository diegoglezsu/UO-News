"""
Configuration settings for UO-News.

Loads from .env file if present. All values can be overridden via environment variables.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

def find_project_root() -> Path:
    env_root = os.environ.get("UO_NEWS_ROOT")
    if env_root:
        return Path(env_root).resolve()

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError(
        "Project root not found. "
        "Set UO_NEWS_ROOT or run from the project directory."
    )


ROOT = find_project_root()
JSON_PATH = ROOT / "data" / "json" / "noticias_uniovi.json"
DB_PATH = ROOT / "db"
LOG_DIR = ROOT / "logs"

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
