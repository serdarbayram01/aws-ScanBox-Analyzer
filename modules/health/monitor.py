"""
Health Module — Background Monitor
Runs latency checks, DNS health, and AWS/Cloudflare status polling in background threads.
Lazy-start: begins monitoring on first page visit, runs until app stops.
"""

import socket
import ssl
import time
import threading
import json
import struct
import logging
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from xml.etree import ElementTree

_ssl_context = ssl.create_default_context()

_logger = logging.getLogger('health.monitor')

# ---------------------------------------------------------------------------
# AWS Region endpoints for latency measurement (EC2 endpoints)
# ---------------------------------------------------------------------------
AWS_REGIONS = {
    'us-east-1':      {'name': 'US East (N. Virginia)',      'endpoint': 'ec2.us-east-1.amazonaws.com'},
    'us-east-2':      {'name': 'US East (Ohio)',             'endpoint': 'ec2.us-east-2.amazonaws.com'},
    'us-west-1':      {'name': 'US West (N. California)',    'endpoint': 'ec2.us-west-1.amazonaws.com'},
    'us-west-2':      {'name': 'US West (Oregon)',           'endpoint': 'ec2.us-west-2.amazonaws.com'},
    'eu-west-1':      {'name': 'Europe (Ireland)',           'endpoint': 'ec2.eu-west-1.amazonaws.com'},
    'eu-west-2':      {'name': 'Europe (London)',            'endpoint': 'ec2.eu-west-2.amazonaws.com'},
    'eu-west-3':      {'name': 'Europe (Paris)',             'endpoint': 'ec2.eu-west-3.amazonaws.com'},
    'eu-central-1':   {'name': 'Europe (Frankfurt)',         'endpoint': 'ec2.eu-central-1.amazonaws.com'},
    'eu-central-2':   {'name': 'Europe (Zurich)',            'endpoint': 'ec2.eu-central-2.amazonaws.com'},
    'eu-north-1':     {'name': 'Europe (Stockholm)',         'endpoint': 'ec2.eu-north-1.amazonaws.com'},
    'eu-south-1':     {'name': 'Europe (Milan)',             'endpoint': 'ec2.eu-south-1.amazonaws.com'},
    'eu-south-2':     {'name': 'Europe (Spain)',             'endpoint': 'ec2.eu-south-2.amazonaws.com'},
    'ap-northeast-1': {'name': 'Asia Pacific (Tokyo)',       'endpoint': 'ec2.ap-northeast-1.amazonaws.com'},
    'ap-northeast-2': {'name': 'Asia Pacific (Seoul)',       'endpoint': 'ec2.ap-northeast-2.amazonaws.com'},
    'ap-northeast-3': {'name': 'Asia Pacific (Osaka)',       'endpoint': 'ec2.ap-northeast-3.amazonaws.com'},
    'ap-southeast-1': {'name': 'Asia Pacific (Singapore)',   'endpoint': 'ec2.ap-southeast-1.amazonaws.com'},
    'ap-southeast-2': {'name': 'Asia Pacific (Sydney)',      'endpoint': 'ec2.ap-southeast-2.amazonaws.com'},
    'ap-southeast-3': {'name': 'Asia Pacific (Jakarta)',     'endpoint': 'ec2.ap-southeast-3.amazonaws.com'},
    'ap-south-1':     {'name': 'Asia Pacific (Mumbai)',      'endpoint': 'ec2.ap-south-1.amazonaws.com'},
    'ap-south-2':     {'name': 'Asia Pacific (Hyderabad)',   'endpoint': 'ec2.ap-south-2.amazonaws.com'},
    'ap-east-1':      {'name': 'Asia Pacific (Hong Kong)',   'endpoint': 'ec2.ap-east-1.amazonaws.com'},
    'sa-east-1':      {'name': 'South America (Sao Paulo)',  'endpoint': 'ec2.sa-east-1.amazonaws.com'},
    'ca-central-1':   {'name': 'Canada (Central)',           'endpoint': 'ec2.ca-central-1.amazonaws.com'},
    'me-south-1':     {'name': 'Middle East (Bahrain)',      'endpoint': 'ec2.me-south-1.amazonaws.com'},
    'me-central-1':   {'name': 'Middle East (UAE)',          'endpoint': 'ec2.me-central-1.amazonaws.com'},
    'af-south-1':     {'name': 'Africa (Cape Town)',         'endpoint': 'ec2.af-south-1.amazonaws.com'},
    'il-central-1':   {'name': 'Israel (Tel Aviv)',          'endpoint': 'ec2.il-central-1.amazonaws.com'},
}

# ---------------------------------------------------------------------------
# DNS Providers
# ---------------------------------------------------------------------------
DNS_PROVIDERS = {
    'cloudflare_primary':   {'name': 'Cloudflare 1.1.1.1',   'ip': '1.1.1.1',   'provider': 'cloudflare'},
    'cloudflare_secondary': {'name': 'Cloudflare 1.0.0.1',   'ip': '1.0.0.1',   'provider': 'cloudflare'},
    'google_primary':       {'name': 'Google 8.8.8.8',       'ip': '8.8.8.8',   'provider': 'google'},
    'google_secondary':     {'name': 'Google 8.8.4.4',       'ip': '8.8.4.4',   'provider': 'google'},
}

# ---------------------------------------------------------------------------
# Status page URLs
# ---------------------------------------------------------------------------
AWS_STATUS_URL = 'https://status.aws.amazon.com/data.json'
AWS_STATUS_RSS = 'https://status.aws.amazon.com/rss/all.rss'
CLOUDFLARE_STATUS_URL = 'https://www.cloudflarestatus.com/api/v2/summary.json'

# ---------------------------------------------------------------------------
# History settings
# ---------------------------------------------------------------------------
MAX_HISTORY = 120  # 120 data points = 1 hour at 30s intervals

# ---------------------------------------------------------------------------
# Shared state (in-memory, thread-safe via lock)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_started = False
_last_error = None  # last monitoring error for UI

# Current values
_region_latency = {}
_dns_status = {}
_aws_outages = []
_cloudflare_status = {}

# History for trend charts
_region_history = {}
_dns_history = {}

# Best region recommendation
_best_region = None


# ---------------------------------------------------------------------------
# Measurement functions
# ---------------------------------------------------------------------------

def _tcp_latency(host, port=443, timeout=3):
    """Measure TCP handshake latency to host:port in milliseconds.
    Timeout reduced to 3s (from 5s) to avoid stalling the pool."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.perf_counter()
        sock.connect((host, port))
        elapsed = (time.perf_counter() - start) * 1000
        sock.close()
        return round(elapsed, 1)
    except Exception:
        return None


def _dns_query_latency(dns_ip, domain='aws.amazon.com', timeout=3):
    """Send a raw DNS query to the given resolver and measure response time."""
    try:
        tx_id = struct.pack('!H', 0x1234)
        flags = struct.pack('!H', 0x0100)
        counts = struct.pack('!4H', 1, 0, 0, 0)

        qname = b''
        for part in domain.split('.'):
            qname += struct.pack('B', len(part)) + part.encode()
        qname += b'\x00'
        qtype = struct.pack('!H', 1)
        qclass = struct.pack('!H', 1)

        query = tx_id + flags + counts + qname + qtype + qclass

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        start = time.perf_counter()
        sock.sendto(query, (dns_ip, 53))
        sock.recvfrom(512)
        elapsed = (time.perf_counter() - start) * 1000
        sock.close()
        return round(elapsed, 1)
    except Exception:
        return None


def _fetch_json(url, timeout=10):
    """Fetch JSON from a URL with a timeout and SSL verification."""
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=timeout, context=_ssl_context) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


def _fetch_text(url, timeout=10):
    """Fetch text content from URL with SSL verification."""
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=timeout, context=_ssl_context) as resp:
            return resp.read().decode('utf-8')
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Background polling loops — all wrapped in try/except to prevent thread death
# ---------------------------------------------------------------------------

def _poll_region_latency():
    """Check TCP latency to all AWS regions every 30 seconds.
    Uses ThreadPoolExecutor instead of raw threads to avoid join-timeout stalls."""
    global _best_region
    _fail_count = 0

    while True:
        try:
            now = time.time()
            latencies = {}

            def check_region(code):
                return code, _tcp_latency(AWS_REGIONS[code]['endpoint'])

            # ThreadPoolExecutor with bounded timeout prevents 270s stall
            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = {executor.submit(check_region, code): code for code in AWS_REGIONS}
                for future in as_completed(futures, timeout=15):
                    try:
                        code, lat = future.result()
                        latencies[code] = lat
                    except Exception:
                        pass

            with _lock:
                for code, info in AWS_REGIONS.items():
                    lat = latencies.get(code)
                    _region_latency[code] = {
                        'latency_ms': lat,
                        'status': 'ok' if lat is not None else 'timeout',
                        'name': info['name'],
                        'endpoint': info['endpoint'],
                        'last_check': now,
                    }
                    if code not in _region_history:
                        _region_history[code] = deque(maxlen=MAX_HISTORY)
                    _region_history[code].append((now, lat))

                valid = [(c, _region_latency[c]['latency_ms'])
                         for c in _region_latency if _region_latency[c]['latency_ms'] is not None]
                if valid:
                    best_code, best_lat = min(valid, key=lambda x: x[1])
                    _best_region = {
                        'region': best_code,
                        'name': AWS_REGIONS[best_code]['name'],
                        'latency_ms': best_lat,
                    }

            _fail_count = 0
        except Exception as exc:
            _fail_count += 1
            _logger.error('Region latency poll failed (attempt %d): %s', _fail_count, exc)

        # Exponential backoff on failure: 30s, 60s, 120s, max 300s
        sleep_time = min(30 * (2 ** min(_fail_count, 3)), 300) if _fail_count else 30
        time.sleep(sleep_time)


def _poll_dns_health():
    """Check DNS resolver latency every 30 seconds."""
    _fail_count = 0

    while True:
        try:
            now = time.time()
            latencies = {}

            def check_dns(key):
                return key, _dns_query_latency(DNS_PROVIDERS[key]['ip'])

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(check_dns, key): key for key in DNS_PROVIDERS}
                for future in as_completed(futures, timeout=10):
                    try:
                        key, lat = future.result()
                        latencies[key] = lat
                    except Exception:
                        pass

            with _lock:
                for key, info in DNS_PROVIDERS.items():
                    lat = latencies.get(key)
                    _dns_status[key] = {
                        'latency_ms': lat,
                        'status': 'ok' if lat is not None else 'timeout',
                        'name': info['name'],
                        'ip': info['ip'],
                        'provider': info['provider'],
                        'last_check': now,
                    }
                    if key not in _dns_history:
                        _dns_history[key] = deque(maxlen=MAX_HISTORY)
                    _dns_history[key].append((now, lat))

            _fail_count = 0
        except Exception as exc:
            _fail_count += 1
            _logger.error('DNS health poll failed (attempt %d): %s', _fail_count, exc)

        sleep_time = min(30 * (2 ** min(_fail_count, 3)), 300) if _fail_count else 30
        time.sleep(sleep_time)


def _poll_aws_status():
    """Fetch AWS Service Health Dashboard every 5 minutes with fallback to RSS."""
    _fail_count = 0

    while True:
        try:
            data = _fetch_json(AWS_STATUS_URL)
            events = []

            if data:
                current = data.get('current', [])
                archive = data.get('archive', [])

                for item in current:
                    events.append({
                        'service': item.get('service_name', item.get('service', '')),
                        'summary': item.get('summary', item.get('description', '')),
                        'date': item.get('date', ''),
                        'status': 'ongoing',
                        'region': _extract_region(item),
                        'url': 'https://health.aws',
                    })

                for item in archive[:10]:
                    events.append({
                        'service': item.get('service_name', item.get('service', '')),
                        'summary': item.get('summary', item.get('description', '')),
                        'date': item.get('date', ''),
                        'status': 'resolved',
                        'region': _extract_region(item),
                        'url': 'https://health.aws',
                    })

                with _lock:
                    _aws_outages.clear()
                    _aws_outages.extend(events)
                _fail_count = 0
            else:
                # Fallback: try RSS
                rss_events = _parse_aws_rss()
                if rss_events:
                    with _lock:
                        _aws_outages.clear()
                        _aws_outages.extend(rss_events)
                    _fail_count = 0
                else:
                    _fail_count += 1

        except Exception as exc:
            _fail_count += 1
            _logger.error('AWS status poll failed (attempt %d): %s', _fail_count, exc)

        sleep_time = min(300 * (2 ** min(_fail_count, 2)), 900) if _fail_count else 300
        time.sleep(sleep_time)


def _parse_aws_rss():
    """Parse AWS status RSS feed and return events list."""
    text = _fetch_text(AWS_STATUS_RSS)
    if not text:
        return None
    try:
        root = ElementTree.fromstring(text)
        items = root.findall('.//item')
        events = []
        for item in items[:20]:
            title = item.findtext('title', '')
            desc = item.findtext('description', '')
            pub_date = item.findtext('pubDate', '')
            link = item.findtext('link', '')
            guid = item.findtext('guid', '')

            region = ''
            for r in AWS_REGIONS:
                if r in (title + guid).lower():
                    region = r
                    break

            events.append({
                'service': title.split(':')[0].strip() if ':' in title else title[:60],
                'summary': desc[:300] if desc else title,
                'date': pub_date,
                'status': 'resolved' if any(w in desc.lower() for w in ('resolved', 'recovered')) else 'ongoing',
                'region': region,
                'url': link or 'https://health.aws',
            })
        return events
    except Exception:
        return None


def _extract_region(item):
    """Try to extract region from AWS status item."""
    text = json.dumps(item).lower()
    for r in AWS_REGIONS:
        if r in text:
            return r
    return ''


def _poll_cloudflare_status():
    """Fetch Cloudflare status page every 5 minutes."""
    _fail_count = 0

    while True:
        try:
            data = _fetch_json(CLOUDFLARE_STATUS_URL)
            if data:
                status_info = data.get('status', {})
                incidents = data.get('incidents', [])
                components = data.get('components', [])

                parsed_incidents = []
                for inc in incidents[:10]:
                    parsed_incidents.append({
                        'name': inc.get('name', ''),
                        'status': inc.get('status', ''),
                        'impact': inc.get('impact', ''),
                        'created_at': inc.get('created_at', ''),
                        'updated_at': inc.get('updated_at', ''),
                        'url': inc.get('shortlink', ''),
                    })

                parsed_components = []
                for comp in components[:30]:
                    if comp.get('group', False) or not comp.get('name'):
                        continue
                    parsed_components.append({
                        'name': comp.get('name', ''),
                        'status': comp.get('status', ''),
                        'description': comp.get('description', ''),
                    })

                with _lock:
                    _cloudflare_status.clear()
                    _cloudflare_status.update({
                        'indicator': status_info.get('indicator', 'unknown'),
                        'description': status_info.get('description', ''),
                        'incidents': parsed_incidents,
                        'components': parsed_components,
                        'last_check': time.time(),
                    })
                _fail_count = 0
            else:
                _fail_count += 1

        except Exception as exc:
            _fail_count += 1
            _logger.error('Cloudflare status poll failed (attempt %d): %s', _fail_count, exc)

        sleep_time = min(300 * (2 ** min(_fail_count, 2)), 900) if _fail_count else 300
        time.sleep(sleep_time)


# ---------------------------------------------------------------------------
# Public API (called by routes.py)
# ---------------------------------------------------------------------------

def start_monitoring():
    """Start background monitoring threads (lazy, called on first page visit)."""
    global _started
    with _lock:
        if _started:
            return
        _started = True

    threads = [
        threading.Thread(target=_poll_region_latency, daemon=True, name='health-region'),
        threading.Thread(target=_poll_dns_health, daemon=True, name='health-dns'),
        threading.Thread(target=_poll_aws_status, daemon=True, name='health-aws-status'),
        threading.Thread(target=_poll_cloudflare_status, daemon=True, name='health-cf-status'),
    ]
    for t in threads:
        t.start()


def is_monitoring():
    return _started


def get_region_latency():
    with _lock:
        data = dict(_region_latency)
    sorted_items = sorted(
        data.items(),
        key=lambda x: (x[1]['latency_ms'] is None, x[1]['latency_ms'] or 99999)
    )
    return [{'region': code, **info} for code, info in sorted_items]


def get_region_history():
    with _lock:
        return {code: list(dq) for code, dq in _region_history.items()}


def get_dns_status():
    with _lock:
        return dict(_dns_status)


def get_dns_history():
    with _lock:
        return {key: list(dq) for key, dq in _dns_history.items()}


def get_aws_outages():
    with _lock:
        return list(_aws_outages)


def get_cloudflare_status():
    with _lock:
        return dict(_cloudflare_status)


def get_best_region():
    with _lock:
        return dict(_best_region) if _best_region else None


def get_full_status():
    """Return all monitoring data in one call — single lock acquisition."""
    with _lock:
        regions_data = dict(_region_latency)
        best = dict(_best_region) if _best_region else None
        dns = dict(_dns_status)
        outages = list(_aws_outages)
        cf = dict(_cloudflare_status)

    # Sort regions outside lock
    sorted_regions = sorted(
        regions_data.items(),
        key=lambda x: (x[1]['latency_ms'] is None, x[1]['latency_ms'] or 99999)
    )

    return {
        'monitoring': _started,
        'regions': [{'region': code, **info} for code, info in sorted_regions],
        'best_region': best,
        'dns': dns,
        'aws_outages': outages,
        'cloudflare': cf,
        'timestamp': time.time(),
    }
