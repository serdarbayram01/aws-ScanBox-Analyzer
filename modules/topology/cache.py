"""
Topology Module — Scan Cache Manager
Scan results are cached per profile and returned until user triggers a new scan.
"""

import json
import os
import time

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SCAN_DIR  = os.path.join(CACHE_DIR, 'scan_results')

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(SCAN_DIR,  exist_ok=True)


def _safe(name: str) -> str:
    """Sanitize profile name for safe use as a filename."""
    safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)
    # Prevent empty names and path traversal
    safe = safe.strip('._')
    return safe or 'default'


def save_scan(profile: str, results: dict) -> None:
    """Persist scan results for a profile."""
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
                profile = fname[:-5]
                scans.append({
                    'profile': profile,
                    'age_seconds': round(age, 1),
                })
            except Exception:
                continue
    except FileNotFoundError:
        pass
    return scans
