"""
Advice Module — Flask Blueprint Routes
"""

import os
import re
import threading

import boto3
from botocore.exceptions import ProfileNotFound, NoCredentialsError, ClientError
from flask import Blueprint, render_template, request, jsonify, send_from_directory

from . import advisor_engine, cache
from . import report_generator

advice_bp = Blueprint('advice', __name__, url_prefix='/advice')

_REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@advice_bp.route('/')
def index():
    return render_template('advice/index.html')


@advice_bp.route('/guide')
def guide():
    return render_template('advice/guide.html')


# ---------------------------------------------------------------------------
# API — Profiles & Regions
# ---------------------------------------------------------------------------

@advice_bp.route('/api/profiles')
def api_profiles():
    """Return list of AWS profiles (with SSO flag) from ~/.aws/config."""
    try:
        import aws_client as awsc
        profiles = awsc.get_aws_profiles()
        return jsonify({'status': 'ok', 'profiles': profiles})
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500


@advice_bp.route('/api/regions')
def api_regions():
    """Return opted-in regions for a profile."""
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'error': 'profile required'}), 400
    try:
        session = boto3.Session(profile_name=profile)
        ec2 = session.client('ec2', region_name='us-east-1')
        resp = ec2.describe_regions(
            Filters=[{'Name': 'opt-in-status', 'Values': ['opt-in-not-required', 'opted-in']}]
        )
        regions = sorted([r['RegionName'] for r in resp.get('Regions', [])])
        return jsonify(regions)
    except Exception as exc:
        err_str = str(exc)
        if 'UnauthorizedSSOTokenError' in err_str or 'Token has expired' in err_str:
            return jsonify({'error': 'sso_expired', 'profile': profile}), 401
        return jsonify({'error': err_str}), 500


# ---------------------------------------------------------------------------
# API — Prerequisites check
# ---------------------------------------------------------------------------

@advice_bp.route('/api/prerequisites')
def api_prerequisites():
    """Check if SecOps, MapInventory scans exist for the profile."""
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'error': 'profile required'}), 400
    result = advisor_engine.check_prerequisites(profile)
    return jsonify(result)


# ---------------------------------------------------------------------------
# API — Assessment
# ---------------------------------------------------------------------------

@advice_bp.route('/api/assess', methods=['POST'])
def api_assess():
    """Start assessment in background thread."""
    data = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    regions = data.get('regions', [])

    if not profile:
        return jsonify({'error': 'profile required'}), 400
    if not regions:
        return jsonify({'error': 'regions required'}), 400

    # Check prerequisites first
    prereqs = advisor_engine.check_prerequisites(profile)
    if not prereqs['ready']:
        return jsonify({
            'error': 'prerequisites_missing',
            'missing': prereqs['missing'],
        }), 400

    advisor_engine.init_progress(profile)

    def _run():
        advisor_engine.run_assessment(profile, regions)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return jsonify({'status': 'started', 'profile': profile})


@advice_bp.route('/api/assess-progress')
def api_assess_progress():
    """Poll assessment progress."""
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'error': 'profile required'}), 400

    progress = advisor_engine.get_progress(profile)
    if progress is None:
        # Check if assessment is done (cached)
        results, _ = cache.load_assessment(profile)
        if results:
            return jsonify({'done': True, 'completed': 1, 'total': 1, 'step': 'done', 'percent': 100})
        return jsonify({'done': False, 'completed': 0, 'total': 0, 'step': '', 'percent': 0})

    total = progress.get('total', 1)
    completed = progress.get('completed', 0)
    pct = round(completed / total * 100) if total > 0 else 0

    return jsonify({
        'done': False,
        'step': progress.get('step', ''),
        'completed': completed,
        'total': total,
        'percent': pct,
    })


@advice_bp.route('/api/last-assessment')
def api_last_assessment():
    """Return cached assessment results."""
    profile = request.args.get('profile', '')
    if not profile:
        return jsonify({'error': 'profile required'}), 400

    results, age = cache.load_assessment(profile)
    if not results:
        return jsonify({'status': 'no_data'})

    results['cache_age_seconds'] = age
    return jsonify(results)


@advice_bp.route('/api/assessment-history')
def api_assessment_history():
    """List all cached assessments."""
    assessments = cache.list_assessments()
    # Enrich with summary info
    enriched = []
    for a in assessments:
        results, _ = cache.load_assessment(a['profile'])
        if results:
            summary = results.get('summary', {})
            enriched.append({
                'profile': a['profile'],
                'timestamp': a.get('timestamp', ''),
                'age_seconds': a['age_seconds'],
                'total_findings': summary.get('total_findings', 0),
                'total_positive': summary.get('total_positive', 0),
                'risk_high': summary.get('risk_counts', {}).get('HIGH', 0),
                'risk_medium': summary.get('risk_counts', {}).get('MEDIUM', 0),
                'risk_low': summary.get('risk_counts', {}).get('LOW', 0),
                'account_id': results.get('account_id', ''),
            })
    return jsonify(enriched)


@advice_bp.route('/api/assessment-history/delete', methods=['POST'])
def api_assessment_delete():
    """Delete cached assessment for a profile."""
    data = request.get_json(silent=True) or {}
    profile = data.get('profile', '')
    if not profile:
        return jsonify({'status': 'error', 'error': 'profile required'}), 400
    cache.clear_assessment(profile)
    return jsonify({'status': 'ok'})


# ---------------------------------------------------------------------------
# API — Reports
# ---------------------------------------------------------------------------

@advice_bp.route('/api/reports/generate', methods=['POST'])
def api_generate_report():
    """Generate HTML (bilingual) + PDF-TR + PDF-EN."""
    data = request.get_json(silent=True) or {}
    profile = data.get('profile', '')

    if not profile:
        return jsonify({'error': 'profile required'}), 400

    results, _ = cache.load_assessment(profile)
    if not results:
        return jsonify({'error': 'No assessment data. Run assessment first.'}), 400

    os.makedirs(_REPORT_DIR, exist_ok=True)

    try:
        files = report_generator.generate_all(results)
        return jsonify({'status': 'ok', 'files': files})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@advice_bp.route('/api/reports/generate_all', methods=['POST'])
def api_generate_all():
    """Generate HTML (bilingual) + PDF-TR + PDF-EN with shared timestamp."""
    data = request.get_json(silent=True) or {}
    profile = data.get('profile', '')

    if not profile:
        return jsonify({'error': 'profile required'}), 400

    results, _ = cache.load_assessment(profile)
    if not results:
        return jsonify({'error': 'No assessment data. Run assessment first.'}), 400

    os.makedirs(_REPORT_DIR, exist_ok=True)

    try:
        files = report_generator.generate_all(results)
        return jsonify({'status': 'ok', 'files': files})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@advice_bp.route('/api/reports/list')
def api_reports_list():
    """List saved advice reports."""
    os.makedirs(_REPORT_DIR, exist_ok=True)
    files = []
    for fname in sorted(os.listdir(_REPORT_DIR), reverse=True):
        if fname.startswith('advice_'):
            fpath = os.path.join(_REPORT_DIR, fname)
            files.append({
                'filename': fname,
                'size': os.path.getsize(fpath),
                'modified': os.path.getmtime(fpath),
            })
    return jsonify(files[:100])


@advice_bp.route('/api/reports/delete', methods=['POST'])
def api_delete_reports():
    """Delete report files by base key (all formats sharing the same timestamp)."""
    data = request.get_json(silent=True) or {}
    bases = data.get('bases', [])
    if not bases:
        return jsonify({'error': 'bases required'}), 400

    deleted = 0
    for base in bases:
        if not re.match(r'^advice_[\w\-]+_\d{8}_\d{6}$', base):
            continue
        for suffix in ('.html', '_tr.pdf', '_en.pdf', '.csv', '.pdf'):
            fpath = os.path.join(_REPORT_DIR, f'{base}{suffix}')
            if os.path.isfile(fpath):
                os.remove(fpath)
                deleted += 1
    return jsonify({'status': 'ok', 'deleted': deleted})


@advice_bp.route('/reports/download/<filename>')
def download_report(filename):
    """Download a report file."""
    basename = os.path.basename(filename)
    if not basename or '..' in filename:
        return jsonify({'status': 'error', 'error': 'Invalid filename'}), 400
    mimetype = 'application/pdf' if basename.endswith('.pdf') else 'text/html' if basename.endswith('.html') else 'text/csv' if basename.endswith('.csv') else 'application/octet-stream'
    return send_from_directory(_REPORT_DIR, basename, as_attachment=True, mimetype=mimetype)
