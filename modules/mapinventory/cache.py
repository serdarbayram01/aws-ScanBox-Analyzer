"""
Map Inventory — Scan Cache Manager
Scan results are cached per profile and returned until user triggers a new scan.
"""

import json
import os
import time

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SCAN_DIR  = os.path.join(CACHE_DIR, 'scan_results')
MAX_CACHED_SCANS = 20

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(SCAN_DIR,  exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(name: str) -> str:
    """Sanitize profile name for safe use as a filename."""
    return ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)


# ---------------------------------------------------------------------------
# Scan result cache (per profile)
# ---------------------------------------------------------------------------

def save_scan(profile: str, results: dict) -> None:
    """Persist scan results for a profile. Enforces MAX_CACHED_SCANS limit."""
    path = os.path.join(SCAN_DIR, f'{_safe(profile)}.json')
    with open(path, 'w') as f:
        json.dump({'_ts': time.time(), 'results': results}, f)
    _enforce_max_scans()


def _enforce_max_scans():
    """Delete oldest cached scans if count exceeds MAX_CACHED_SCANS."""
    try:
        files = []
        for fname in os.listdir(SCAN_DIR):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(SCAN_DIR, fname)
            files.append((fpath, os.path.getmtime(fpath)))
        if len(files) <= MAX_CACHED_SCANS:
            return
        # Sort by mtime ascending (oldest first), delete excess
        files.sort(key=lambda x: x[1])
        for fpath, _ in files[:len(files) - MAX_CACHED_SCANS]:
            try:
                os.remove(fpath)
            except OSError:
                pass
    except Exception:
        pass


def load_scan(profile: str):
    """Return (results, age_seconds) for the last scan of profile."""
    path = os.path.join(SCAN_DIR, f'{_safe(profile)}.json')
    try:
        with open(path) as f:
            blob = json.load(f)
        return blob.get('results'), time.time() - blob.get('_ts', 0)
    except Exception:
        return None, float('inf')


def clear_scan(profile: str) -> bool:
    """Delete cached scan for a profile. Returns True if file existed."""
    path = os.path.join(SCAN_DIR, f'{_safe(profile)}.json')
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False


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
