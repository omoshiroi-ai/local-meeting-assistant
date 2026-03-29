"""Persisted LLM overrides in ``app_state`` (JSON). Environment remains the fallback."""

from __future__ import annotations

import json
import logging
import sqlite3

from src.config import LLM_MAX_NEW_TOKENS, LLM_MODEL
from src.db.repository import AppStateRepo

logger = logging.getLogger(__name__)

LLM_SETTINGS_KEY = "llm_settings"


def _load_doc(conn: sqlite3.Connection) -> dict:
    raw = AppStateRepo(conn).get(LLM_SETTINGS_KEY)
    if not raw:
        return {}
    try:
        doc = json.loads(raw)
        return doc if isinstance(doc, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Invalid %s JSON; ignoring", LLM_SETTINGS_KEY)
        return {}


def _save_doc(conn: sqlite3.Connection, doc: dict) -> None:
    repo = AppStateRepo(conn)
    if not doc:
        repo.delete(LLM_SETTINGS_KEY)
    else:
        repo.set(LLM_SETTINGS_KEY, json.dumps(doc))


def get_stored_model_id(conn: sqlite3.Connection | None) -> str | None:
    if conn is None:
        return None
    mid = _load_doc(conn).get("model_id")
    if mid is None:
        return None
    if not isinstance(mid, str):
        return None
    s = mid.strip()
    return s or None


def get_stored_max_new_tokens(conn: sqlite3.Connection | None) -> int | None:
    if conn is None:
        return None
    v = _load_doc(conn).get("max_new_tokens")
    if v is None:
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n


def get_effective_model_id(conn: sqlite3.Connection | None) -> str:
    stored = get_stored_model_id(conn)
    return stored if stored else LLM_MODEL


def get_effective_max_new_tokens(conn: sqlite3.Connection | None) -> int:
    stored = get_stored_max_new_tokens(conn)
    return stored if stored is not None else LLM_MAX_NEW_TOKENS


def get_llm_settings_view(conn: sqlite3.Connection) -> dict:
    """Structured view for API responses."""
    return {
        "effective_model_id": get_effective_model_id(conn),
        "effective_max_new_tokens": get_effective_max_new_tokens(conn),
        "stored_model_id": get_stored_model_id(conn),
        "stored_max_new_tokens": get_stored_max_new_tokens(conn),
        "environment_model_id": LLM_MODEL,
        "environment_max_new_tokens": LLM_MAX_NEW_TOKENS,
    }


def patch_llm_settings(conn: sqlite3.Connection, updates: dict) -> dict:
    """Merge partial updates (only keys present in ``updates``). Values ``None`` clear override."""
    doc = _load_doc(conn)
    if "model_id" in updates:
        v = updates["model_id"]
        if v is None or (isinstance(v, str) and not str(v).strip()):
            doc.pop("model_id", None)
        else:
            doc["model_id"] = str(v).strip()
    if "max_new_tokens" in updates:
        v = updates["max_new_tokens"]
        if v is None:
            doc.pop("max_new_tokens", None)
        else:
            doc["max_new_tokens"] = int(v)
    _save_doc(conn, doc)
    return get_llm_settings_view(conn)
