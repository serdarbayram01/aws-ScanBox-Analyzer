"""
Advice module — Per-profile assessment result cache.
Stores assessment JSON in modules/advice/data/scan_results/<profile>.json
"""

import json
import os
import re
import time

_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'scan_results')


def _safe(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._-]', '_', name)


def _ensure_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)


def save_assessment(profile: str, results: dict):
    _ensure_dir()
    path = os.path.join(_DATA_DIR, f'{_safe(profile)}.json')
    payload = {'_ts': time.time(), 'results': results}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_assessment(profile: str) -> tuple:
    """Return (results_dict or None, age_seconds)."""
    path = os.path.join(_DATA_DIR, f'{_safe(profile)}.json')
    if not os.path.isfile(path):
        return None, 0
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = time.time() - data.get('_ts', 0)
        return data.get('results'), age
    except Exception:
        return None, 0


def clear_assessment(profile: str):
    """Delete cached assessment for a profile."""
    path = os.path.join(_DATA_DIR, f'{_safe(profile)}.json')
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def list_assessments() -> list:
    """Return list of {'profile': name, 'age_seconds': age} for cached assessments."""
    _ensure_dir()
    result = []
    for fname in os.listdir(_DATA_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(_DATA_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            ts = data.get('_ts', 0)
            profile = data.get('results', {}).get('profile', fname.replace('.json', ''))
            result.append({
                'profile': profile,
                'age_seconds': time.time() - ts,
                'timestamp': data.get('results', {}).get('assessment_time', ''),
            })
        except Exception:
            continue
    return result
