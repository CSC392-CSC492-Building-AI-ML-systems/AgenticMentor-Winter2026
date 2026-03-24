"""In-process store for user Gemini API keys (never written to the database).

Keys are keyed by (owner_uid, project_id). They are lost on process restart and
are not shared across multiple API worker processes.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

_lock = threading.Lock()
# (owner_uid, project_id) -> (api_key, expiry_monotonic)
_store: dict[tuple[str, str], tuple[str, float]] = {}

# Default: keep key in RAM for 7 days after last set/verify (refreshed on each set).
_DEFAULT_TTL_SEC = 7 * 24 * 3600


def set_custom_key(owner_uid: str, project_id: str, api_key: str, ttl_seconds: int | None = None) -> None:
    ttl = _DEFAULT_TTL_SEC if ttl_seconds is None else ttl_seconds
    exp = time.monotonic() + ttl
    with _lock:
        _store[(owner_uid, project_id)] = (api_key.strip(), exp)


def get_custom_key(owner_uid: str, project_id: str) -> Optional[str]:
    now = time.monotonic()
    with _lock:
        entry = _store.get((owner_uid, project_id))
        if not entry:
            return None
        key, exp = entry
        if exp < now:
            del _store[(owner_uid, project_id)]
            return None
        return key


def delete_custom_key(owner_uid: str, project_id: str) -> None:
    with _lock:
        _store.pop((owner_uid, project_id), None)


def custom_key_is_set(owner_uid: str, project_id: str) -> bool:
    return get_custom_key(owner_uid, project_id) is not None


def delete_all_for_user(owner_uid: str) -> None:
    with _lock:
        dead = [k for k in _store if k[0] == owner_uid]
        for k in dead:
            del _store[k]
