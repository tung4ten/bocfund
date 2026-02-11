from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # fund/

DB_PATH = os.environ.get(
    "BOC_DB_PATH",
    str(_PROJECT_ROOT / "data" / "boc_nav.sqlite3"),
)

PORTFOLIO_PATH = os.environ.get(
    "BOC_PORTFOLIO_PATH",
    str(_PROJECT_ROOT / "portfolio.json"),
)

FRONTEND_DIST_DIR = os.environ.get(
    "BOC_FRONTEND_DIST",
    str(_PROJECT_ROOT / "web" / "frontend" / "dist"),
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        abs_path = str(Path(DB_PATH).resolve())
        _engine = create_engine(
            f"sqlite:///{abs_path}",
            connect_args={"check_same_thread": False},
            future=True,
        )
    return _engine


def get_session_factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db():
    """FastAPI dependency – yields a DB session per request."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Portfolio config (re-read on every call so edits take effect immediately)
# ---------------------------------------------------------------------------
def load_portfolio_codes() -> List[str]:
    try:
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("products", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []
