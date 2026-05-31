"""Simple in-memory TTL cache for the AWS Reference module.

No AWS / boto3 dependencies. Mirrors the pattern from aws_client._ce_cache
but kept module-local so the AWS Reference module can run on a host with no
AWS credentials at all (the wider `aws_client.py` imports boto3 eagerly)."""

import threading
import time

_PROBE_TTL         = 300     # 5 min — TCP latency probe results
_REGIONAL_JSON_TTL = 86400   # 24 h — AWS regional services JSON (very stable)
_IP_RANGES_TTL     = 43200   # 12 h — AWS IP-ranges JSON (updated daily-ish)

_store = {}
_lock = threading.Lock()


def get(key: str, ttl: float):
    """Return cached value if not expired, else None."""
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        if now - entry['ts'] > ttl:
            _store.pop(key, None)
            return None
        return entry['value']


def set_(key: str, value):
    """Store a value with the current timestamp."""
    with _lock:
        _store[key] = {'value': value, 'ts': time.time()}


def age(key: str):
    """Return seconds since the entry was stored, or None if not cached."""
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        return time.time() - entry['ts']


def invalidate(key: str = None):
    """Drop a specific key, or all keys if key is None."""
    with _lock:
        if key is None:
            _store.clear()
        else:
            _store.pop(key, None)
