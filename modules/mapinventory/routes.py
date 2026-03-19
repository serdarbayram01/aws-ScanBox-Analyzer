"""
Map Inventory Module — Flask Blueprint
All resource inventory / mapping routes. Removing this file/blueprint does not affect FinOps or SecOps.
"""

import json
import os
import threading

from flask import Blueprint, jsonify, request, render_template, send_from_directory

from . import cache
from . import collector

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

mapinventory_bp = Blueprint('mapinventory', __name__)

# Module-level scan progress tracker, keyed by profile name.
# Each entry: {service: str, completed: int, total: int}
_scan_progress = {}

# Limit concurrent profile scans to prevent thread explosion
# (e.g. 100 profiles × 40 workers = 4000 threads without this)
_scan_semaphore = threading.Semaphore(5)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@mapinventory_bp.route('/mapinventory')
def index():
    return render_template('mapinventory/index.html')


@mapinventory_bp.route('/mapinventory/guide')
def guide():
    return render_template('mapinventory/guide.html')


# ---------------------------------------------------------------------------
# API — Profiles
# ---------------------------------------------------------------------------

@mapinventory_bp.route('/mapinventory/api/profiles')
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

@mapinventory_bp.route('/mapinventory/api/services')
def api_services():
    return jsonify({'status': 'ok', 'services': collector.SERVICES_ORDER})


@mapinventory_bp.route('/mapinventory/api/regions')
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

def _run_scan_thread(profile, exclude_defaults, regions, services=None):
    """Execute inventory scan in a background thread and cache results."""
    import boto3
    _scan_semaphore.acquire()
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
            exclude_defaults=exclude_defaults,
            regions=regions,
            services=services,
            progress_callback=progress_callback,
        )

        results['profile'] = profile
        results['account_id'] = account_id
        cache.save_scan(profile, results)

        resource_count = results.get('metadata', {}).get('resource_count', 0)
        # Mark progress as done
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
        _scan_semaphore.release()


@mapinventory_bp.route('/mapinventory/api/scan', methods=['POST'])
def api_scan():
    data             = request.get_json(silent=True) or {}
    profiles         = data.get('profiles', [])
    exclude_defaults = bool(data.get('exclude_defaults', False))
    regions          = data.get('regions') or None  # list or None → scan all
    services         = data.get('services') or None  # list or None → scan all

    if not profiles:
        return jsonify({'status': 'error', 'error': 'profiles required'}), 400

    for profile in profiles:
        # Reset progress for this profile
        _scan_progress[profile] = {
            'service': 'starting',
            'completed': 0,
            'total': 0,
        }
        t = threading.Thread(
            target=_run_scan_thread,
            args=(profile, exclude_defaults, regions, services),
            daemon=True,
        )
        t.start()

    return jsonify({'status': 'started', 'profiles': profiles})


# ---------------------------------------------------------------------------
# API — Scan Progress
# ---------------------------------------------------------------------------

@mapinventory_bp.route('/mapinventory/api/scan-progress')
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

@mapinventory_bp.route('/mapinventory/api/last-scanned-profile')
def api_last_scanned_profile():
    """Return the most recently scanned profile name."""
    scans = cache.list_scans()
    if not scans:
        return jsonify({'status': 'not_found'})
    scans.sort(key=lambda s: s['age_seconds'])
    return jsonify({'status': 'ok', 'profile': scans[0]['profile']})


@mapinventory_bp.route('/mapinventory/api/scan-history')
def api_scan_history():
    """Return list of all cached scans with summary info."""
    scans = cache.list_scans()
    history = []
    for s in scans:
        results, age = cache.load_scan(s['profile'])
        meta = results.get('metadata', {}) if results else {}
        history.append({
            'profile': s['profile'],
            'age_seconds': s['age_seconds'],
            'resource_count': meta.get('resource_count', 0),
            'services_count': len(meta.get('service_counts', {})),
            'regions_count': meta.get('regions_scanned', 0),
            'timestamp': meta.get('timestamp', ''),
            'account_id': results.get('account_id', '') if results else '',
            'duration_seconds': meta.get('scan_duration_seconds', 0),
        })
    history.sort(key=lambda h: h['age_seconds'])
    return jsonify({'status': 'ok', 'scans': history})


@mapinventory_bp.route('/mapinventory/api/last-scan')
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

@mapinventory_bp.route('/mapinventory/api/resources')
def api_resources():
    profile = request.args.get('profile', '')
    service = request.args.get('service', '')
    region  = request.args.get('region', '')
    rtype   = request.args.get('type', '')

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, _ = cache.load_scan(profile)
    if not results:
        return jsonify({'status': 'not_found', 'resources': []})

    resources = results.get('resources', [])

    if service:
        resources = [r for r in resources if r.get('service', '').lower() == service.lower()]
    if region:
        resources = [r for r in resources if r.get('region') == region]
    if rtype:
        resources = [r for r in resources if r.get('type', '').lower() == rtype.lower()]

    return jsonify({'status': 'ok', 'count': len(resources), 'resources': resources})


# ---------------------------------------------------------------------------
# API — Single Resource Detail
# ---------------------------------------------------------------------------

@mapinventory_bp.route('/mapinventory/api/resource-detail')
def api_resource_detail():
    profile    = request.args.get('profile', '')
    service    = request.args.get('service', '')
    resource_id = request.args.get('id', '')

    if not profile or not resource_id:
        return jsonify({'status': 'error', 'error': 'profile and id required'}), 400

    results, _ = cache.load_scan(profile)
    if not results:
        return jsonify({'status': 'not_found'})

    resources = results.get('resources', [])
    for r in resources:
        if r.get('id') == resource_id:
            if service and r.get('service', '').lower() != service.lower():
                continue
            return jsonify({'status': 'ok', 'resource': r})

    return jsonify({'status': 'not_found'})


# ---------------------------------------------------------------------------
# API — Cache Management
# ---------------------------------------------------------------------------

@mapinventory_bp.route('/mapinventory/api/cache/clear', methods=['POST'])
def api_cache_clear():
    data    = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    deleted = cache.clear_scan(profile)
    # Also remove progress tracking
    _scan_progress.pop(profile, None)
    return jsonify({'status': 'ok', 'deleted': deleted})


# ---------------------------------------------------------------------------
# API — Reports
# ---------------------------------------------------------------------------

@mapinventory_bp.route('/mapinventory/api/reports/list')
def api_reports_list():
    try:
        files = []
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if not fname.startswith('mapinventory_'):
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


def _get_report_mimetype(filename):
    """Return explicit MIME type for report files."""
    if filename.endswith('.csv'):
        return 'text/csv'
    elif filename.endswith('.pdf'):
        return 'application/pdf'
    elif filename.endswith('.html'):
        return 'text/html'
    return 'application/octet-stream'

@mapinventory_bp.route('/mapinventory/reports/download/<path:filename>')
def download_report(filename):
    basename = os.path.basename(filename)
    if not basename or '..' in filename:
        return jsonify({'status': 'error', 'error': 'Invalid filename'}), 400
    mimetype = _get_report_mimetype(basename)
    return send_from_directory(os.path.abspath(REPORTS_DIR), basename, as_attachment=True, mimetype=mimetype)


@mapinventory_bp.route('/mapinventory/api/reports/delete', methods=['POST'])
def api_reports_delete():
    import re as _re
    data = request.get_json(silent=True) or {}
    bases = data.get('bases', [])
    if not bases:
        return jsonify({'status': 'error', 'error': 'No bases provided'}), 400
    deleted = 0
    for base in bases:
        if not _re.match(r'^mapinventory_[\w\-]+_\d{8}_\d{6}$', base):
            continue
        for ext in ('html', 'csv', 'pdf'):
            fpath = os.path.join(REPORTS_DIR, f'{base}.{ext}')
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
                    deleted += 1
            except OSError:
                pass
    return jsonify({'status': 'ok', 'deleted': deleted})


@mapinventory_bp.route('/mapinventory/api/reports/generate', methods=['POST'])
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


@mapinventory_bp.route('/mapinventory/api/reports/generate_all', methods=['POST'])
def api_reports_generate_all():
    """Generate HTML + CSV + PDF for a profile using the same timestamp."""
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
