from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional
import uuid


def _filter_none(mapping: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    if not mapping:
        return {}
    return {key: value for key, value in mapping.items() if value is not None}


def build_task_record(
    endpoint: str,
    *,
    method: str,
    payload: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Return a normalized task record ready to be stored/enqueued."""
    return {
        "task_id": str(uuid.uuid4()),
        "request": {
            "method": method.upper(),
            "endpoint": endpoint,
            "payload": _filter_none(payload),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "response": None,
    }


__all__ = ["build_task_record"]
