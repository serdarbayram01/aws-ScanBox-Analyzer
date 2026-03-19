"""
FinOps Module — Flask Blueprint
All financial cost analysis routes live here.
Removing this file/blueprint does not affect any other module.
"""

import os
import re
import threading
import logging

from flask import Blueprint, jsonify, request, send_from_directory, render_template

import aws_client as awsc
import report_generator as rg

finops_bp = Blueprint('finops', __name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports'
)

# Audit logger
_logger = logging.getLogger('finops.routes')

# Input validation patterns
_PROFILE_RE = re.compile(r'^[\w\-\.@\+/: ]{1,128}$')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_FILENAME_RE = re.compile(r'^[\w\-\.]+$')

def _valid_profile(name):
    """Validate profile name against allowed characters."""
    return bool(name and _PROFILE_RE.match(name))

def _valid_date(d):
    """Validate date string format (YYYY-MM-DD)."""
    return bool(d and _DATE_RE.match(d))

def _valid_filename(name):
    """Validate report filename — no path traversal."""
    return bool(name and _FILENAME_RE.match(name) and '..' not in name)

def _get_report_mimetype(filename):
    """Return explicit MIME type for report files to prevent browser misinterpretation."""
    if filename.endswith('.csv'):
        return 'text/csv'
    elif filename.endswith('.pdf'):
        return 'application/pdf'
    elif filename.endswith('.html'):
        return 'text/html'
    return 'application/octet-stream'


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@finops_bp.route('/')
def root_redirect():
    from flask import redirect
    return redirect('/finops')


@finops_bp.route('/finops')
def index():
    return render_template('index.html')


@finops_bp.route('/finops/detail')
def detail():
    return render_template('detail.html')


@finops_bp.route('/finops/guide')
def guide():
    return render_template('guide.html')


# ---------------------------------------------------------------------------
# API — Profiles
# ---------------------------------------------------------------------------

@finops_bp.route('/finops/api/profiles')
def api_profiles():
    try:
        profiles = awsc.get_aws_profiles()
        return jsonify({'status': 'ok', 'profiles': profiles})
    except Exception as exc:
        _logger.error('Failed to list profiles: %s', exc)
        return jsonify({'status': 'error', 'error': 'Failed to list AWS profiles'}), 500


# ---------------------------------------------------------------------------
# API — Costs (Dashboard)
# ---------------------------------------------------------------------------

@finops_bp.route('/finops/api/costs', methods=['POST'])
def api_costs():
    data = request.get_json(silent=True) or {}
    profiles = data.get('profiles', [])
    try:
        months_back = min(max(int(data.get('months_back', 13)), 1), 13)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'error': 'Invalid months_back value'}), 400

    if not profiles:
        return jsonify({'status': 'error', 'error': 'No profiles selected'}), 400

    if len(profiles) > 50:
        return jsonify({'status': 'error', 'error': 'Too many profiles (max 50)'}), 400

    # Validate each profile name
    profiles = [p for p in profiles if isinstance(p, str) and _valid_profile(p)]
    if not profiles:
        return jsonify({'status': 'error', 'error': 'No valid profiles provided'}), 400

    _logger.info('Cost analysis requested for %d profiles', len(profiles))

    results = awsc.fetch_all_profiles_costs(profiles, months_back=months_back)

    successful = [r for r in results if r.get('status') == 'success']
    summary = {
        'total_current_spend': round(sum(r['current_spend'] for r in successful), 2),
        'total_projection':    round(sum(r['projection']     for r in successful), 2),
        'total_historical':    round(sum(r['total_usage']    for r in successful), 2),
        'total_credits':       round(sum(r['total_credits']  for r in successful), 2),
    }

    return jsonify({'status': 'ok', 'profiles': results, 'summary': summary})


# ---------------------------------------------------------------------------
# API — Detail (single profile)
# ---------------------------------------------------------------------------

@finops_bp.route('/finops/api/detail')
def api_detail():
    profile     = request.args.get('profile', '')
    try:
        months_back = min(max(int(request.args.get('months', 6)), 1), 12)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'error': 'Invalid months parameter'}), 400
    start_date  = request.args.get('start', None)
    end_date    = request.args.get('end',   None)

    if not profile or not _valid_profile(profile):
        return jsonify({'status': 'error', 'error': 'Valid profile name required'}), 400

    # Validate date parameters if provided
    if start_date and not _valid_date(start_date):
        return jsonify({'status': 'error', 'error': 'Invalid start date format (YYYY-MM-DD)'}), 400
    if end_date and not _valid_date(end_date):
        return jsonify({'status': 'error', 'error': 'Invalid end date format (YYYY-MM-DD)'}), 400

    _logger.info('Detail requested for profile=%s', profile)

    results = {}
    errors  = {}

    def run(key, fn, *args, **kwargs):
        try:
            results[key] = fn(*args, **kwargs)
        except Exception as exc:
            errors[key] = str(exc)

    kw = dict(start_date=start_date, end_date=end_date) if (start_date and end_date) else {}

    threads = [
        threading.Thread(target=run, args=('costs',   awsc.fetch_profile_costs,       profile, months_back), kwargs=kw),
        threading.Thread(target=run, args=('regions', awsc.fetch_region_distribution, profile, months_back), kwargs=kw),
        threading.Thread(target=run, args=('budgets', awsc.fetch_budgets,             profile)),
        threading.Thread(target=run, args=('ec2',     awsc.fetch_ec2_inventory,       profile)),
        threading.Thread(target=run, args=('credits', awsc.fetch_credits,             profile)),
    ]
    for t in threads: t.start()
    for t in threads: t.join(timeout=30)

    # Check for timed-out threads
    for t in threads:
        if t.is_alive():
            _logger.warning('Thread %s timed out after 30s', t.name)

    return jsonify({
        'status':  'ok',
        'profile': profile,
        'costs':   results.get('costs',   {'status': 'error', 'error': errors.get('costs',   'unknown')}),
        'regions': results.get('regions', {'status': 'error', 'error': errors.get('regions', 'unknown')}),
        'budgets': results.get('budgets', {'status': 'error', 'error': errors.get('budgets', 'unknown')}),
        'ec2':     results.get('ec2',     {'status': 'error', 'error': errors.get('ec2',     'unknown')}),
        'credits': results.get('credits', {'status': 'error', 'error': errors.get('credits', 'unknown')}),
    })


@finops_bp.route('/finops/api/cost-report')
def api_cost_report():
    profile     = request.args.get('profile', '')
    granularity = request.args.get('granularity', 'DAILY').upper()
    start_date  = request.args.get('start', None)
    end_date    = request.args.get('end',   None)

    if not profile or not _valid_profile(profile):
        return jsonify({'status': 'error', 'error': 'Valid profile name required'}), 400
    if granularity not in ('DAILY', 'WEEKLY', 'MONTHLY'):
        granularity = 'DAILY'
    if start_date and not _valid_date(start_date):
        return jsonify({'status': 'error', 'error': 'Invalid start date format'}), 400
    if end_date and not _valid_date(end_date):
        return jsonify({'status': 'error', 'error': 'Invalid end date format'}), 400

    result = awsc.fetch_cost_report(profile, granularity, start_date, end_date)
    return jsonify(result)


@finops_bp.route('/finops/api/service-detail')
def api_service_detail():
    profile = request.args.get('profile', '')
    service = request.args.get('service', '')
    try:
        months = min(max(int(request.args.get('months', 6)), 1), 12)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'error': 'Invalid months parameter'}), 400

    if not profile or not _valid_profile(profile):
        return jsonify({'status': 'error', 'error': 'Valid profile name required'}), 400
    if not service or len(service) > 256:
        return jsonify({'status': 'error', 'error': 'Valid service name required'}), 400

    result = awsc.fetch_service_detail(profile, service, months_back=months)
    return jsonify(result)


# ---------------------------------------------------------------------------
# API — Reports
# ---------------------------------------------------------------------------

@finops_bp.route('/finops/api/reports/list')
def api_reports_list():
    return jsonify({'status': 'ok', 'reports': rg.list_reports()})


@finops_bp.route('/finops/api/reports/generate', methods=['POST'])
def api_reports_generate():
    data        = request.get_json(silent=True) or {}
    profiles    = data.get('profiles', [])
    fmt         = data.get('format', 'html').lower()
    try:
        months_back = min(max(int(data.get('months_back', 13)), 1), 13)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'error': 'Invalid months_back value'}), 400

    if not profiles:
        return jsonify({'status': 'error', 'error': 'No profiles selected'}), 400

    if fmt not in ('html', 'csv', 'pdf'):
        return jsonify({'status': 'error', 'error': f'Unknown format: {fmt}'}), 400

    # Validate profile names
    profiles = [p for p in profiles if isinstance(p, str) and _valid_profile(p)]
    if not profiles:
        return jsonify({'status': 'error', 'error': 'No valid profiles provided'}), 400

    results = awsc.fetch_all_profiles_costs(profiles, months_back=months_back)

    try:
        if fmt == 'html':
            path = rg.generate_html(results)
        elif fmt == 'csv':
            path = rg.generate_csv(results)
        elif fmt == 'pdf':
            path = rg.generate_pdf(results)
            if path is None:
                return jsonify({'status': 'error', 'error': 'reportlab not installed — run: pip install reportlab'}), 500

        filename = os.path.basename(path)
        _logger.info('Report generated: %s', filename)
        return jsonify({'status': 'ok', 'filename': filename, 'path': path})

    except Exception as exc:
        _logger.error('Report generation failed: %s', exc)
        return jsonify({'status': 'error', 'error': 'Report generation failed'}), 500


@finops_bp.route('/finops/api/reports/generate_all', methods=['POST'])
def api_reports_generate_all():
    """Generate HTML + CSV + PDF with the same timestamp."""
    from datetime import datetime as dt
    data        = request.get_json(silent=True) or {}
    profiles    = data.get('profiles', [])
    try:
        months_back = min(max(int(data.get('months_back', 13)), 1), 13)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'error': 'Invalid months_back value'}), 400

    if not profiles:
        return jsonify({'status': 'error', 'error': 'No profiles selected'}), 400

    profiles = [p for p in profiles if isinstance(p, str) and _valid_profile(p)]
    if not profiles:
        return jsonify({'status': 'error', 'error': 'No valid profiles provided'}), 400

    results = awsc.fetch_all_profiles_costs(profiles, months_back=months_back)
    ts = dt.now().strftime('%Y%m%d_%H%M%S')
    filenames = {}

    try:
        filenames['html'] = os.path.basename(rg.generate_html(results, title='AWS FinOps Report'))
    except Exception:
        filenames['html'] = None
    try:
        filenames['csv'] = os.path.basename(rg.generate_csv(results))
    except Exception:
        filenames['csv'] = None
    try:
        path = rg.generate_pdf(results)
        filenames['pdf'] = os.path.basename(path) if path else None
    except Exception:
        filenames['pdf'] = None

    return jsonify({'status': 'ok', 'filenames': filenames, 'ts': ts})


@finops_bp.route('/finops/api/reports/generate_per_profile', methods=['POST'])
def api_reports_generate_per_profile():
    """Generate separate reports for each profile."""
    from datetime import datetime as dt
    data        = request.get_json(silent=True) or {}
    profiles    = data.get('profiles', [])
    try:
        months_back = min(max(int(data.get('months_back', 13)), 1), 13)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'error': 'Invalid months_back value'}), 400

    if not profiles:
        return jsonify({'status': 'error', 'error': 'No profiles selected'}), 400

    profiles = [p for p in profiles if isinstance(p, str) and _valid_profile(p)]
    if not profiles:
        return jsonify({'status': 'error', 'error': 'No valid profiles provided'}), 400

    results = awsc.fetch_all_profiles_costs(profiles, months_back=months_back)
    ts = dt.now().strftime('%Y%m%d_%H%M%S')
    generated = []

    for profile_data in results:
        if profile_data.get('status') != 'success':
            continue
        fnames = rg.generate_profile_report(profile_data, ts=ts)
        generated.append({
            'profile': profile_data['profile'],
            'filenames': fnames,
        })

    return jsonify({'status': 'ok', 'generated': generated, 'count': len(generated)})


@finops_bp.route('/finops/api/reports/delete', methods=['POST'])
def api_reports_delete():
    """Delete report files by base key."""
    data = request.get_json(silent=True) or {}
    bases = data.get('bases', [])
    if not bases:
        return jsonify({'status': 'error', 'error': 'No bases provided'}), 400

    deleted = 0
    for base in bases:
        if not re.match(r'^aws_finops_[\w\-]*_?\d{8}_\d{6}$', base):
            continue
        for ext in ('html', 'csv', 'pdf'):
            fpath = os.path.join(REPORTS_DIR, f'{base}.{ext}')
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
                    deleted += 1
            except OSError:
                pass
        # Also delete _services.csv companion
        svc_path = os.path.join(REPORTS_DIR, f'{base}_services.csv')
        try:
            if os.path.exists(svc_path):
                os.remove(svc_path)
                deleted += 1
        except OSError:
            pass

    return jsonify({'status': 'ok', 'deleted': deleted})


@finops_bp.route('/finops/reports/<path:filename>')
def serve_report(filename):
    if not _valid_filename(filename):
        return jsonify({'status': 'error', 'error': 'Invalid filename'}), 400
    return send_from_directory(os.path.abspath(REPORTS_DIR), filename)


@finops_bp.route('/finops/reports/download/<path:filename>')
def download_report(filename):
    if not _valid_filename(filename):
        return jsonify({'status': 'error', 'error': 'Invalid filename'}), 400
    mimetype = _get_report_mimetype(filename)
    return send_from_directory(os.path.abspath(REPORTS_DIR), filename, as_attachment=True, mimetype=mimetype)
