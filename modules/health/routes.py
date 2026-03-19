"""
Health Module — Flask Blueprint
Connection health, AWS outage status, DNS health monitoring.
"""

from flask import Blueprint, jsonify, render_template
from . import monitor

health_bp = Blueprint('health', __name__)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@health_bp.route('/health')
def index():
    """Render the Health dashboard. Also triggers lazy monitoring start."""
    monitor.start_monitoring()
    return render_template('health/index.html')


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@health_bp.route('/health/api/status')
def api_status():
    """Return all monitoring data in a single payload."""
    return jsonify(monitor.get_full_status())


@health_bp.route('/health/api/latency')
def api_latency():
    """Return region latency data sorted by speed."""
    return jsonify({
        'regions': monitor.get_region_latency(),
        'best_region': monitor.get_best_region(),
    })


@health_bp.route('/health/api/latency-history')
def api_latency_history():
    """Return latency trend data for charts."""
    return jsonify({
        'regions': monitor.get_region_history(),
        'dns': monitor.get_dns_history(),
    })


@health_bp.route('/health/api/aws-outages')
def api_aws_outages():
    """Return AWS outage/incident data."""
    return jsonify({
        'outages': monitor.get_aws_outages(),
    })


@health_bp.route('/health/api/dns')
def api_dns():
    """Return DNS resolver status."""
    return jsonify({
        'dns': monitor.get_dns_status(),
    })


@health_bp.route('/health/api/cloudflare')
def api_cloudflare():
    """Return Cloudflare status data."""
    return jsonify({
        'cloudflare': monitor.get_cloudflare_status(),
    })


@health_bp.route('/health/api/start', methods=['POST'])
def api_start():
    """Explicitly start monitoring (if not already running)."""
    monitor.start_monitoring()
    return jsonify({'status': 'ok', 'monitoring': monitor.is_monitoring()})
