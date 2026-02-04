"""Centralized paths for the ProRef project."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
QUESTIONS_DIR = DATA_DIR / "questions"
TESTCASES_DIR = DATA_DIR / "test_cases"
DOCS_DIR = DATA_DIR / "docs"
DB_PATH = DATA_DIR / "proref.db"


def ensure_dirs():
    """Create all required directories if they don't exist."""
    QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)
    TESTCASES_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
