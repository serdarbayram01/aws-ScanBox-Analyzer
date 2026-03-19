"""
SecOps Module — Flask Blueprint
All security analysis routes. Removing this file/blueprint does not affect FinOps.
"""

import json
import os
import re
import logging

from flask import Blueprint, jsonify, request, render_template, send_from_directory

from . import scanner, cache

_logger = logging.getLogger('secops.routes')
_PROFILE_RE = re.compile(r'^[\w\-\.@\+/: ]{1,128}$')
_FILENAME_RE = re.compile(r'^[\w\-\.]+$')

def _valid_profile(name):
    return bool(name and _PROFILE_RE.match(name))

def _valid_filename(name):
    return bool(name and _FILENAME_RE.match(name) and '..' not in name)

def _get_report_mimetype(filename):
    """Return explicit MIME type for report files."""
    if filename.endswith('.csv'):
        return 'text/csv'
    elif filename.endswith('.pdf'):
        return 'application/pdf'
    elif filename.endswith('.html'):
        return 'text/html'
    return 'application/octet-stream'

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

secops_bp = Blueprint('secops', __name__)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@secops_bp.route('/secops')
def index():
    return render_template('secops/index.html')


@secops_bp.route('/secops/detail')
def detail():
    return render_template('secops/detail.html')


@secops_bp.route('/secops/guide')
def guide():
    return render_template('secops/guide.html')


# ---------------------------------------------------------------------------
# API — Profiles (SecOps-own, independent from FinOps)
# ---------------------------------------------------------------------------

@secops_bp.route('/secops/api/profiles')
def api_profiles():
    try:
        import aws_client as awsc
        profiles = awsc.get_aws_profiles()
        return jsonify({'status': 'ok', 'profiles': profiles})
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# API — Scan
# ---------------------------------------------------------------------------

@secops_bp.route('/secops/api/regions')
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


@secops_bp.route('/secops/api/scan', methods=['POST'])
def api_scan():
    data             = request.get_json(silent=True) or {}
    profile          = data.get('profile', '')
    exclude_defaults = bool(data.get('exclude_defaults', False))
    regions          = data.get('regions') or None  # list or None → scan all

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results = scanner.run_scan(profile, exclude_defaults=exclude_defaults, regions=regions)
    return jsonify(results)


@secops_bp.route('/secops/api/scan-progress')
def api_scan_progress():
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    progress = scanner.get_progress(profile)
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
    })


@secops_bp.route('/secops/api/scan-history')
def api_scan_history():
    """Return list of all cached scans with summary info."""
    scans = cache.list_scans()
    history = []
    for s in scans:
        results, age = cache.load_scan(s['profile'])
        if not results:
            continue
        summary = results.get('summary', {})
        svc = results.get('services', {})
        history.append({
            'profile':       s['profile'],
            'age_seconds':   s['age_seconds'],
            'account_id':    results.get('account_id', ''),
            'scan_time':     results.get('scan_time', ''),
            'score':         summary.get('score', 0),
            'total':         summary.get('total', 0),
            'passed':        summary.get('passed', 0),
            'failed':        summary.get('failed', 0),
            'services_count': len(svc),
        })
    history.sort(key=lambda h: h['age_seconds'])
    return jsonify({'status': 'ok', 'scans': history})


@secops_bp.route('/secops/api/last-scan')
def api_last_scan():
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, age = scanner.get_last_scan(profile)
    if results is None:
        return jsonify({'status': 'not_found'})

    results['_cache_age_seconds'] = round(age)
    return jsonify(results)


# ---------------------------------------------------------------------------
# API — Findings (filtered)
# ---------------------------------------------------------------------------

@secops_bp.route('/secops/api/findings')
def api_findings():
    profile   = request.args.get('profile', '')
    framework = request.args.get('framework', '')
    severity  = request.args.get('severity', '')
    service   = request.args.get('service', '')
    status    = request.args.get('status', '')

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, _ = scanner.get_last_scan(profile)
    if not results:
        return jsonify({'status': 'not_found', 'findings': []})

    findings = results.get('findings', [])

    if framework:
        findings = [f for f in findings if framework in f.get('frameworks', {})]
    if severity:
        findings = [f for f in findings if f.get('severity') == severity.upper()]
    if service:
        findings = [f for f in findings if f.get('service') == service]
    if status:
        findings = [f for f in findings if f.get('status') == status.upper()]

    return jsonify({'status': 'ok', 'count': len(findings), 'findings': findings})


# ---------------------------------------------------------------------------
# API — Cache / Settings
# ---------------------------------------------------------------------------

@secops_bp.route('/secops/api/cache/status')
def api_cache_status():
    return jsonify({'status': 'ok', 'cache': cache.get_cache_status()})


@secops_bp.route('/secops/api/scan-history/delete', methods=['POST'])
def api_scan_history_delete():
    """Delete a cached scan result for a profile."""
    data = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    if not profile or not _valid_profile(profile):
        return jsonify({'status': 'error', 'error': 'Valid profile required'}), 400

    scan_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'scan_results')
    safe_name = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in profile)
    fpath = os.path.join(scan_dir, f'{safe_name}.json')
    try:
        if os.path.exists(fpath):
            os.remove(fpath)
            return jsonify({'status': 'ok', 'deleted': True})
        return jsonify({'status': 'ok', 'deleted': False})
    except OSError as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500


@secops_bp.route('/secops/api/settings', methods=['GET'])
def api_settings_get():
    cfg = cache.get_api_config()
    # Mask keys in response
    masked = {k: ('***' if v else '') for k, v in cfg.items()}
    return jsonify({'status': 'ok', 'config': masked})


@secops_bp.route('/secops/api/settings', methods=['POST'])
def api_settings_save():
    data = request.get_json(silent=True) or {}
    existing = cache.get_api_config()
    # Only update provided non-masked values
    for k in existing:
        v = data.get(k, '')
        if v and v != '***':
            existing[k] = v
    cache.save_api_config(existing)
    return jsonify({'status': 'ok'})


# ---------------------------------------------------------------------------
# API — Reports
# ---------------------------------------------------------------------------

@secops_bp.route('/secops/api/reports/list')
def api_reports_list():
    try:
        files = []
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if not fname.startswith('secops_'):
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


@secops_bp.route('/secops/reports/<path:filename>')
def serve_report(filename):
    if not _valid_filename(filename):
        return jsonify({'status': 'error', 'error': 'Invalid filename'}), 400
    return send_from_directory(os.path.abspath(REPORTS_DIR), filename)


@secops_bp.route('/secops/reports/download/<path:filename>')
def download_report(filename):
    if not _valid_filename(filename):
        return jsonify({'status': 'error', 'error': 'Invalid filename'}), 400
    mimetype = _get_report_mimetype(filename)
    return send_from_directory(os.path.abspath(REPORTS_DIR), filename, as_attachment=True, mimetype=mimetype)


@secops_bp.route('/secops/api/reports/generate', methods=['POST'])
def api_reports_generate():
    data    = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    fmt     = data.get('format', 'html').lower()

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, _ = scanner.get_last_scan(profile)
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


@secops_bp.route('/secops/api/reports/generate_all', methods=['POST'])
def api_reports_generate_all():
    """Generate HTML + CSV + PDF for a profile using the same timestamp."""
    from datetime import datetime
    data    = request.get_json(silent=True) or {}
    profile = data.get('profile', '')

    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400

    results, _ = scanner.get_last_scan(profile)
    if not results:
        return jsonify({'status': 'error', 'error': 'No scan results found — run a scan first'}), 400

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    from .report_generator import generate_html, generate_csv, generate_pdf
    filenames = {}

    try:
        filenames['html'] = os.path.basename(generate_html(results, ts=ts))
    except Exception as exc:
        filenames['html'] = None

    try:
        filenames['csv'] = os.path.basename(generate_csv(results, ts=ts))
    except Exception as exc:
        filenames['csv'] = None

    try:
        path = generate_pdf(results, ts=ts)
        filenames['pdf'] = os.path.basename(path) if path else None
    except Exception:
        filenames['pdf'] = None

    return jsonify({'status': 'ok', 'filenames': filenames, 'ts': ts})


@secops_bp.route('/secops/api/reports/delete', methods=['POST'])
def api_reports_delete():
    """Delete report groups by base key (e.g. secops_profile_20260314_120000)."""
    import re
    data = request.get_json(silent=True) or {}
    bases = data.get('bases', [])
    if not bases:
        return jsonify({'status': 'error', 'error': 'No bases provided'}), 400

    deleted = 0
    for base in bases:
        # Validate base key format
        if not re.match(r'^secops_[\w\-\.]+_\d{8}_\d{6}$', base):
            continue
        # Delete all matching files: base.html, base.csv, base.pdf
        for ext in ('html', 'csv', 'pdf'):
            fpath = os.path.join(REPORTS_DIR, f'{base}.{ext}')
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
                    deleted += 1
            except OSError:
                pass

    return jsonify({'status': 'ok', 'deleted': deleted})
