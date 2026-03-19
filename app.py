"""
AWS ScanBox Analyzer — Flask Application Entry Point
Registers all module blueprints and starts the server.

Adding a new module:
  1. Create modules/<name>/routes.py with a Blueprint named <name>_bp
  2. Import and register it below — nothing else changes.

Removing a module:
  1. Comment out or delete the import + register lines below.
  2. Delete the modules/<name>/ folder.
"""

import os
import threading
import webbrowser

import logging
import time as _time

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ---------------------------------------------------------------------------
# Version — single source of truth: VERSION file in project root
# ---------------------------------------------------------------------------
_VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')
try:
    with open(_VERSION_FILE) as _vf:
        APP_VERSION = _vf.read().strip()
except FileNotFoundError:
    APP_VERSION = '0.0.0'

app.config['APP_VERSION'] = APP_VERSION

# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------
_req_logger = logging.getLogger('scanbox.requests')
if not _req_logger.handlers:
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'), exist_ok=True)
    _rh = logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'requests.log'))
    _rh.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
    _req_logger.addHandler(_rh)
    _req_logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Simple API Rate Limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------
_rate_limit_store = {}  # ip -> [timestamps]
_RATE_LIMIT = 60       # max requests per window
_RATE_WINDOW = 60      # window in seconds


@app.before_request
def _rate_limit_check():
    if not request.path.startswith(('/finops/api/', '/secops/api/', '/mapinventory/api/',
                                     '/topology/api/', '/advice/api/', '/health/api/')):
        return  # only limit API endpoints
    ip = request.remote_addr or '127.0.0.1'
    now = _time.time()
    if ip not in _rate_limit_store:
        _rate_limit_store[ip] = []
    # Clean old entries
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < _RATE_WINDOW]
    if len(_rate_limit_store[ip]) >= _RATE_LIMIT:
        return jsonify({'status': 'error', 'error': 'Rate limit exceeded. Try again later.'}), 429
    _rate_limit_store[ip].append(now)


@app.before_request
def _log_request_start():
    request._start_time = _time.time()


@app.after_request
def _log_request_end(response):
    duration = round((_time.time() - getattr(request, '_start_time', _time.time())) * 1000, 1)
    if request.path.startswith('/static/'):
        return response  # skip static file logging
    _req_logger.info('%s %s %s %sms', request.method, request.path, response.status_code, duration)
    # CORS headers for local development
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5100'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response


# ---------------------------------------------------------------------------
# Global Error Handlers — JSON for API requests, HTML for page requests
# ---------------------------------------------------------------------------

def _wants_json():
    """Check if the client prefers JSON (API calls) over HTML."""
    return (
        request.path.startswith('/finops/api/') or
        request.path.startswith('/secops/api/') or
        request.path.startswith('/mapinventory/api/') or
        request.path.startswith('/topology/api/') or
        request.path.startswith('/advice/api/') or
        request.path.startswith('/health/api/') or
        request.accept_mimetypes.best == 'application/json'
    )


@app.errorhandler(404)
def not_found(e):
    if _wants_json():
        return jsonify({'status': 'error', 'error': 'Not found'}), 404
    return render_template('error.html', code=404, message='Page not found'), 404


@app.errorhandler(500)
def internal_error(e):
    if _wants_json():
        return jsonify({'status': 'error', 'error': 'Internal server error'}), 500
    return render_template('error.html', code=500, message='Internal server error'), 500


# ---------------------------------------------------------------------------
# Context processor — injects active_module into every template
# ---------------------------------------------------------------------------

@app.context_processor
def inject_active_module():
    """Determines the active sidebar module from the current blueprint name."""
    module = 'finops'
    if request.blueprints:
        bp_name = request.blueprints[-1]
        if bp_name in ('finops', 'secops', 'mapinventory', 'topology', 'advice', 'health', 'enjoy', 'about'):
            module = bp_name
    return {'active_module': module, 'app_version': APP_VERSION}


# ---------------------------------------------------------------------------
# Register module blueprints
# ---------------------------------------------------------------------------

from modules.finops.routes import finops_bp           # noqa: E402
from modules.secops.routes import secops_bp           # noqa: E402
from modules.mapinventory.routes import mapinventory_bp  # noqa: E402
from modules.topology.routes import topology_bp            # noqa: E402
from modules.advice.routes import advice_bp                # noqa: E402
from modules.health.routes import health_bp                # noqa: E402
from modules.enjoy.routes import enjoy_bp                  # noqa: E402
from modules.about.routes import about_bp                  # noqa: E402

app.register_blueprint(finops_bp)
app.register_blueprint(secops_bp)
app.register_blueprint(mapinventory_bp)
app.register_blueprint(topology_bp)
app.register_blueprint(advice_bp)
app.register_blueprint(health_bp)
app.register_blueprint(enjoy_bp)
app.register_blueprint(about_bp)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def open_browser(port):
    import time
    time.sleep(1.2)
    webbrowser.open(f'http://localhost:{port}')


if __name__ == '__main__':
    port = 5100
    print(f'\n  AWS ScanBox Analyzer v{APP_VERSION}')
    print(f'  Running at: http://localhost:{port}')
    print(f'  Press Ctrl+C to stop.\n')

    # Start health monitoring immediately on app boot (no lazy wait)
    from modules.health import monitor as _health_monitor
    _health_monitor.start_monitoring()

    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    app.run(host='0.0.0.0', port=port, debug=False)
