"""
SecOps — 24-hour Cache Manager
External API data (NVD, Prowler Hub) is fetched at most once per 24 hours.
Scan results are cached per profile and returned until user triggers a new scan.
"""

import json
import os
import time
from datetime import datetime

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SCAN_DIR  = os.path.join(CACHE_DIR, 'scan_results')
MAX_AGE   = 86400  # 24 hours

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(SCAN_DIR,  exist_ok=True)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _cache_path(key: str) -> str:
    return os.path.join(CACHE_DIR, f'{key}.json')


def _age(path: str) -> float:
    """Return age in seconds; inf if file missing/invalid."""
    try:
        with open(path) as f:
            ts = json.load(f).get('_ts', 0)
        return time.time() - ts
    except Exception:
        return float('inf')


# ---------------------------------------------------------------------------
# External data cache
# ---------------------------------------------------------------------------

def is_stale(key: str) -> bool:
    return _age(_cache_path(key)) > MAX_AGE


def read_cache(key: str):
    """Return (data, age_seconds). data=None if not found."""
    path = _cache_path(key)
    try:
        with open(path) as f:
            blob = json.load(f)
        return blob.get('data'), time.time() - blob.get('_ts', 0)
    except Exception:
        return None, float('inf')


def write_cache(key: str, data) -> None:
    with open(_cache_path(key), 'w') as f:
        json.dump({'_ts': time.time(), 'data': data}, f)


# ---------------------------------------------------------------------------
# Scan result cache (per profile)
# ---------------------------------------------------------------------------

def save_scan(profile: str, results: dict) -> None:
    path = os.path.join(SCAN_DIR, f'{_safe(profile)}.json')
    with open(path, 'w') as f:
        json.dump({'_ts': time.time(), 'results': results}, f)


def load_scan(profile: str):
    """Return (results, age_seconds) for the last scan of profile."""
    path = os.path.join(SCAN_DIR, f'{_safe(profile)}.json')
    try:
        with open(path) as f:
            blob = json.load(f)
        return blob.get('results'), time.time() - blob.get('_ts', 0)
    except Exception:
        return None, float('inf')


def _safe(name: str) -> str:
    """Sanitize profile name for filesystem use. Matches aws_client.validate_profile() charset."""
    return ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)


def list_scans() -> list:
    """Return list of dicts with profile names and ages for all cached scans."""
    scans = []
    try:
        for fname in os.listdir(SCAN_DIR):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(SCAN_DIR, fname)
            try:
                with open(path) as f:
                    blob = json.load(f)
                ts = blob.get('_ts', 0)
                age = time.time() - ts
                profile = fname[:-5]  # strip .json
                scans.append({
                    'profile': profile,
                    'age_seconds': round(age, 1),
                })
            except Exception:
                continue
    except FileNotFoundError:
        pass
    return scans


# ---------------------------------------------------------------------------
# API config (keys stored locally)
# ---------------------------------------------------------------------------

API_CONFIG_PATH = os.path.join(CACHE_DIR, 'api_config.json')

_DEFAULT_CONFIG = {
    'nvd_api_key':        '',
    'prowler_hub_api_key': '',
}


def get_api_config() -> dict:
    try:
        with open(API_CONFIG_PATH) as f:
            return {**_DEFAULT_CONFIG, **json.load(f)}
    except Exception:
        return dict(_DEFAULT_CONFIG)


def save_api_config(config: dict) -> None:
    merged = {**_DEFAULT_CONFIG, **config}
    with open(API_CONFIG_PATH, 'w') as f:
        json.dump(merged, f, indent=2)


# ---------------------------------------------------------------------------
# Status summary (for UI)
# ---------------------------------------------------------------------------

def get_cache_status() -> dict:
    status = {}
    for key in ['nvd', 'prowler_hub']:
        path = _cache_path(key)
        age  = _age(path)
        status[key] = {
            'exists':       age < float('inf'),
            'stale':        age > MAX_AGE,
            'age_hours':    round(age / 3600, 1) if age < float('inf') else None,
            'last_update':  datetime.fromtimestamp(time.time() - age).strftime('%Y-%m-%d %H:%M')
                            if age < float('inf') else None,
        }
    return status
