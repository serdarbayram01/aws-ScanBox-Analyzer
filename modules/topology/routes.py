"""
Topology Module — Flask Blueprint
Network topology visualization routes. Independent from FinOps, SecOps, MapInventory.
"""

import json
import os
import threading
import re

from flask import Blueprint, jsonify, request, render_template, send_from_directory

from . import cache
from . import collector

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

topology_bp = Blueprint('topology', __name__)

# Module-level scan progress tracker, keyed by profile name.
_scan_progress = {}
_scan_locks = {}  # profile → True when scan is running


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@topology_bp.route('/topology')
def index():
    return render_template('topology/index.html')


@topology_bp.route('/topology/guide')
def guide():
    return render_template('topology/guide.html')


# ---------------------------------------------------------------------------
# API — Profiles
# ---------------------------------------------------------------------------

@topology_bp.route('/topology/api/profiles')
def api_profiles():
    try:
        import aws_client as awsc
        profiles = awsc.get_aws_profiles()
        return jsonify({'status': 'ok', 'profiles': profiles})
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# API — Regions
# ---------------------------------------------------------------------------

@topology_bp.route('/topology/api/regions')
def api_regions():
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400
    try:
        import boto3
        session = boto3.Session(profile_name=profile)
        ec2 = session.client('ec2', region_name='us-east-1')
        regions = sorted([r['RegionName'] for r in ec2.describe_regions(
            Filters=[{'Name': 'opt-in-status', 'Values': ['opt-in-not-required', 'opted-in']}]
        )['Regions']])
        return jsonify({'status': 'ok', 'regions': regions})
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# API — Scan (background thread)
# ---------------------------------------------------------------------------

def _run_scan_thread(profile, regions, exclude_defaults=False):
    """Execute topology scan in a background thread and cache results."""
    import boto3
    _scan_locks[profile] = True
    try:
        session = boto3.Session(profile_name=profile)
        sts = session.client('sts', region_name='us-east-1')
        identity = sts.get_caller_identity()
        account_id = identity.get('Account', '')

        def progress_callback(service, status_msg, completed, total):
            _scan_progress[profile] = {
                'service': service,
                'completed': completed,
                'total': total,
            }

        results = collector.collect_all(
            session=session,
            account_id=account_id,
            regions=regions,
            progress_callback=progress_callback,
            exclude_defaults=exclude_defaults,
        )

        results['profile'] = profile
        results['account_id'] = account_id
        cache.save_scan(profile, results)

        resource_count = results.get('metadata', {}).get('resource_count', 0)
        _scan_progress[profile] = {
            'service': 'done',
            'completed': resource_count,
            'total': resource_count,
            'done': True,
        }

    except Exception as exc:
        _scan_progress[profile] = {
            'service': 'error',
            'completed': 0,
            'total': 0,
            'done': True,
            'error': str(exc),
        }
    finally:
        _scan_locks.pop(profile, None)


@topology_bp.route('/topology/api/scan', methods=['POST'])
def api_scan():
    data    = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    regions = data.get('regions') or None
    exclude_defaults = data.get('exclude_defaults', False)

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    if not regions or len(regions) == 0:
        return jsonify({'status': 'error', 'error': 'regions required'}), 400

    # Prevent concurrent scans for same profile
    if _scan_locks.get(profile):
        return jsonify({'status': 'error', 'error': 'Scan already in progress for this profile'}), 429

    _scan_progress[profile] = {
        'service': 'starting',
        'completed': 0,
        'total': 0,
    }
    t = threading.Thread(
        target=_run_scan_thread,
        args=(profile, regions, exclude_defaults),
        daemon=True,
    )
    t.start()

    return jsonify({'status': 'started', 'profile': profile})


# ---------------------------------------------------------------------------
# API — Scan Progress
# ---------------------------------------------------------------------------

@topology_bp.route('/topology/api/scan-progress')
def api_scan_progress():
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    progress = _scan_progress.get(profile)
    if progress is None:
        return jsonify({'status': 'not_found'})

    completed = progress.get('completed', 0)
    total = progress.get('total', 0)
    percent = round((completed / total * 100) if total > 0 else 0, 1)

    return jsonify({
        'status': 'ok',
        'service': progress.get('service', ''),
        'completed': completed,
        'total': total,
        'percent': percent,
        'done': progress.get('done', False),
        'error': progress.get('error'),
    })


# ---------------------------------------------------------------------------
# API — Last Scan (cached)
# ---------------------------------------------------------------------------

@topology_bp.route('/topology/api/last-scanned-profile')
def api_last_scanned_profile():
    scans = cache.list_scans()
    if not scans:
        return jsonify({'status': 'not_found'})
    scans.sort(key=lambda s: s['age_seconds'])
    return jsonify({'status': 'ok', 'profile': scans[0]['profile']})


@topology_bp.route('/topology/api/scan-history')
def api_scan_history():
    scans = cache.list_scans()
    history = []
    for s in scans:
        results, age = cache.load_scan(s['profile'])
        meta = results.get('metadata', {}) if results else {}
        history.append({
            'profile': s['profile'],
            'age_seconds': s['age_seconds'],
            'resource_count': meta.get('resource_count', 0),
            'regions_count': meta.get('regions_scanned', 0),
            'timestamp': meta.get('timestamp', ''),
            'account_id': results.get('account_id', '') if results else '',
            'type_counts': meta.get('type_counts', {}),
        })
    history.sort(key=lambda h: h['age_seconds'])
    return jsonify({'status': 'ok', 'scans': history})


@topology_bp.route('/topology/api/last-scan')
def api_last_scan():
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, age = cache.load_scan(profile)
    if results is None:
        return jsonify({'status': 'not_found'})

    results['_cache_age_seconds'] = round(age)
    return jsonify(results)


# ---------------------------------------------------------------------------
# API — Filtered Resources
# ---------------------------------------------------------------------------

@topology_bp.route('/topology/api/resources')
def api_resources():
    profile = request.args.get('profile', '')
    rtype   = request.args.get('type', '')
    region  = request.args.get('region', '')
    vpc_id  = request.args.get('vpc_id', '')

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, _ = cache.load_scan(profile)
    if not results:
        return jsonify({'status': 'not_found', 'resources': []})

    resources = results.get('resources', [])

    if rtype:
        resources = [r for r in resources if r.get('type') == rtype]
    if region:
        resources = [r for r in resources if r.get('region') == region]
    if vpc_id:
        resources = [r for r in resources if r.get('vpc_id') == vpc_id]

    return jsonify({'status': 'ok', 'count': len(resources), 'resources': resources})


# ---------------------------------------------------------------------------
# API — Cache Management
# ---------------------------------------------------------------------------

@topology_bp.route('/topology/api/cache/clear', methods=['POST'])
def api_cache_clear():
    data    = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    deleted = cache.clear_scan(profile)
    _scan_progress.pop(profile, None)
    return jsonify({'status': 'ok', 'deleted': deleted})


# ---------------------------------------------------------------------------
# API — Reports
# ---------------------------------------------------------------------------

@topology_bp.route('/topology/api/reports/list')
def api_reports_list():
    try:
        files = []
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if not fname.startswith('topology_'):
                continue
            fpath = os.path.join(REPORTS_DIR, fname)
            files.append({
                'filename': fname,
                'size':     os.path.getsize(fpath),
                'mtime':    os.path.getmtime(fpath),
            })
        return jsonify({'status': 'ok', 'reports': files[:100]})
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500


@topology_bp.route('/topology/reports/download/<path:filename>')
def download_report(filename):
    # Prevent path traversal
    basename = os.path.basename(filename)
    if not basename or '..' in filename or not re.match(r'^topology_[\w\-]+_\d{8}_\d{6}\.(html|csv|pdf)$', basename):
        return jsonify({'status': 'error', 'error': 'Invalid filename'}), 400
    return send_from_directory(os.path.abspath(REPORTS_DIR), basename, as_attachment=True)


@topology_bp.route('/topology/api/reports/delete', methods=['POST'])
def api_reports_delete():
    data = request.get_json(silent=True) or {}
    bases = data.get('bases', [])
    if not bases:
        return jsonify({'status': 'error', 'error': 'bases required'}), 400
    deleted = []
    for base in bases:
        # Validate base key format
        if not re.match(r'^topology_[\w\-]+_\d{8}_\d{6}$', base):
            continue
        for ext in ('html', 'csv', 'pdf'):
            fpath = os.path.join(REPORTS_DIR, f'{base}.{ext}')
            try:
                os.remove(fpath)
                deleted.append(f'{base}.{ext}')
            except FileNotFoundError:
                pass
    return jsonify({'status': 'ok', 'deleted': deleted})


@topology_bp.route('/topology/api/reports/generate', methods=['POST'])
def api_reports_generate():
    data    = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    fmt     = data.get('format', 'html').lower()

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, _ = cache.load_scan(profile)
    if not results:
        return jsonify({'status': 'error', 'error': 'No scan results found — run a scan first'}), 400

    try:
        from .report_generator import generate_html, generate_csv, generate_pdf
        if fmt == 'html':
            path = generate_html(results)
        elif fmt == 'csv':
            path = generate_csv(results)
        elif fmt == 'pdf':
            path = generate_pdf(results)
            if path is None:
                return jsonify({'status': 'error', 'error': 'reportlab not installed'}), 500
        else:
            return jsonify({'status': 'error', 'error': f'Unknown format: {fmt}'}), 400

        return jsonify({'status': 'ok', 'filename': os.path.basename(path)})
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500


@topology_bp.route('/topology/api/reports/generate_all', methods=['POST'])
def api_reports_generate_all():
    from datetime import datetime
    data    = request.get_json(silent=True) or {}
    profile = data.get('profile', '')

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, _ = cache.load_scan(profile)
    if not results:
        return jsonify({'status': 'error', 'error': 'No scan results found — run a scan first'}), 400

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    from .report_generator import generate_html, generate_csv, generate_pdf
    filenames = {}

    try:
        filenames['html'] = os.path.basename(generate_html(results, ts=ts))
    except Exception:
        filenames['html'] = None

    try:
        filenames['csv'] = os.path.basename(generate_csv(results, ts=ts))
    except Exception:
        filenames['csv'] = None

    try:
        path = generate_pdf(results, ts=ts)
        filenames['pdf'] = os.path.basename(path) if path else None
    except Exception:
        filenames['pdf'] = None

    return jsonify({'status': 'ok', 'filenames': filenames, 'ts': ts})
