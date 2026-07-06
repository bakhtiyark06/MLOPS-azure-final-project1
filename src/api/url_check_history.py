# Author: Member D — URL check history persistence
# Purpose: Store successful public URL probe results for dashboard history

"""Server-side history for POST /check-url-metrics results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.api.schemas import UrlMetricsResponse
from src.utils.config import get_project_root

MAX_HISTORY_ENTRIES = 50

_history_path: Path | None = None


def get_history_path() -> Path:
    """Return path to url_check_history.json (override in tests via set_history_path)."""
    global _history_path
    if _history_path is not None:
        return _history_path
    return get_project_root() / "data" / "processed" / "url_check_history.json"


def set_history_path(path: Path | None) -> None:
    """Override history file location (tests). Pass None to reset to default."""
    global _history_path
    _history_path = path


def _read_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        return items if isinstance(items, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_store(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"items": items}, indent=2)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def append_entry(url: str, metrics: UrlMetricsResponse) -> None:
    """Prepend a successful check; dedupe by URL; cap at MAX_HISTORY_ENTRIES."""
    path = get_history_path()
    items = _read_store(path)
    items = [item for item in items if item.get("url") != url]

    entry = {
        "url": url,
        "checked_at": datetime.now(UTC).isoformat(),
        **metrics.model_dump(),
    }
    items.insert(0, entry)
    items = items[:MAX_HISTORY_ENTRIES]
    _write_store(path, items)


def list_history() -> list[dict]:
    """Return history entries newest first."""
    return _read_store(get_history_path())


def clear_history() -> None:
    """Remove all stored URL check history."""
    path = get_history_path()
    if path.exists():
        path.unlink()
