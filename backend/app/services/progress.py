"""Live progress of a running analysis, kept in Redis instead of the database.

Progress only matters while a job runs, so it needs no database column. Redis problems
are logged and ignored: a missing progress bar must never fail an analysis or the API.
"""

import json
import logging
from functools import lru_cache

import redis

from app.core.config import get_settings

log = logging.getLogger(__name__)

TTL_S = 3600  # Redis deletes the entry by itself after 1 hour
TIMEOUT_S = 1.0  # give up quickly if Redis is down, so nothing waits for it


@lru_cache
def _client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=TIMEOUT_S, socket_timeout=TIMEOUT_S)


def _key(analysis_id: str) -> str:
    return f"progress:{analysis_id}"


def set_progress(analysis_id: str, percent: int, step: str) -> None:
    try:
        value = json.dumps({"percent": max(0, min(100, int(percent))), "step": step})
        _client().set(_key(analysis_id), value, ex=TTL_S)
    except Exception as e:
        log.warning("could not save progress for %s: %s", analysis_id, e)


def get_progress(analysis_id: str) -> dict | None:
    """Return {"percent": int, "step": str}, or None if there is nothing to show."""
    try:
        value = _client().get(_key(analysis_id))
        if not value:
            return None
        data = json.loads(value)
        return {"percent": int(data["percent"]), "step": str(data["step"])}
    except Exception as e:
        log.warning("could not read progress for %s: %s", analysis_id, e)
        return None


def clear_progress(analysis_id: str) -> None:
    try:
        _client().delete(_key(analysis_id))
    except Exception as e:
        log.warning("could not clear progress for %s: %s", analysis_id, e)
