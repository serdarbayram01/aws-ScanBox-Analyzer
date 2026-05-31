"""AWS Reference module — Flask blueprint.

Endpoints:
    GET  /awsref/                       — page render
    GET  /awsref/api/regions            — full region + LZ list (static)
    GET  /awsref/api/services?region=X  — services available in a region
    GET  /awsref/api/region-matrix      — TCP-probe every region + LZ from this host
    GET  /awsref/api/endpoints?region=X — TCP-probe each AWS service endpoint in a region

NO `boto3`. NO AWS credentials. Only:
    - Static catalog (modules.awsref.aws_catalog)
    - TCP socket probes (modules.awsref.probe)
    - Optional public AWS JSON fetches (modules.awsref.public_sources)
"""

import re
from flask import Blueprint, jsonify, render_template, request

from . import aws_catalog, cache, probe, public_sources

awsref_bp = Blueprint('awsref', __name__)

# Loose region-code validator: lower-case letters / digits / dashes only.
_REGION_RE = re.compile(r'^[a-z0-9-]{1,40}$')


def _valid_region(code: str) -> bool:
    return bool(code and _REGION_RE.match(code))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

@awsref_bp.route('/awsref')
@awsref_bp.route('/awsref/')
def index():
    return render_template('awsref/index.html')


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@awsref_bp.route('/awsref/api/regions')
def api_regions():
    """Return the full region + LZ catalog. Static — no probe."""
    cache_key = 'regions_catalog_v1'
    cached = cache.get(cache_key, cache._REGIONAL_JSON_TTL)
    if cached is not None:
        return jsonify(cached)
    payload = {
        'status':  'ok',
        'regions': aws_catalog.AWS_REGIONS,
        'lzs_by_region': aws_catalog.LZ_BY_REGION,
        'lz_city_names': aws_catalog.LZ_CITY_NAMES,
        'totals': {
            'regions': len(aws_catalog.AWS_REGIONS),
            'lzs':     sum(len(r['lzs']) for r in aws_catalog.AWS_REGIONS),
        },
        'source': 'static catalog (modules.awsref.aws_catalog)',
    }
    cache.set_(cache_key, payload)
    return jsonify(payload)


@awsref_bp.route('/awsref/api/services')
def api_services():
    """Return service catalog with region-rendered endpoint hosts.

    Query params:
        region — region or LZ code (default: eu-central-1)
        probe  — '1' to also TCP-probe each endpoint and return p50/p95 ms
                 (slower; ~3-5 seconds for ~30 services in parallel)
    """
    raw_region = request.args.get('region', 'eu-central-1')
    if not _valid_region(raw_region):
        return jsonify({'status': 'error', 'error': 'invalid region'}), 400
    parent = aws_catalog.parent_region(raw_region)
    do_probe = request.args.get('probe') == '1'

    services = aws_catalog.services_for_region(raw_region)

    if do_probe:
        cache_key = f'services_probe::{parent}'
        cached = cache.get(cache_key, cache._PROBE_TTL)
        if cached is not None:
            probes_by_id = cached
        else:
            targets = [{'id': s['id'], 'host': s['endpoint'], 'port': s['port']}
                       for s in services
                       if s['endpoint'] and not s['endpoint'].startswith('169.254.')]
            results = probe.probe_many(targets, max_workers=12, samples=3, timeout=2.5)
            probes_by_id = {r['id']: r for r in results}
            cache.set_(cache_key, probes_by_id)
        for s in services:
            p = probes_by_id.get(s['id'])
            if p:
                s['reachable'] = p.get('reachable', False)
                s['p50_ms']    = p.get('p50_ms')
                s['p95_ms']    = p.get('p95_ms')
                s['error']     = p.get('error')

    return jsonify({
        'status':       'ok',
        'region':       parent,
        'raw_region':   raw_region,
        'is_local_zone': raw_region != parent,
        'pretty_name':  aws_catalog.lz_pretty(raw_region, parent) if raw_region != parent
                        else aws_catalog.REGIONS_BY_CODE.get(parent, {}).get('name', parent),
        'services':     services,
        'probed':       do_probe,
    })


@awsref_bp.route('/awsref/api/region-matrix')
def api_region_matrix():
    """TCP-probe every region + LZ from this host. Returns latency stats per
    target so the user can pick the closest region.

    Query params:
        refresh — '1' bypasses cache and re-probes immediately.
    """
    cache_key = 'region_matrix_v1'
    if request.args.get('refresh') != '1':
        cached = cache.get(cache_key, cache._PROBE_TTL)
        if cached is not None:
            return jsonify({**cached, 'cached': True})

    targets = aws_catalog.all_region_entries(include_lzs=True)
    # Map each to {host, port} for the probe + keep metadata
    probe_inputs = [{**t, 'host': t['endpoint'], 'port': 443} for t in targets]
    results = probe.probe_many(probe_inputs, max_workers=12, samples=5, timeout=3.0)

    # Sort: reachable first, then by p50 ascending. Match Go reference behaviour.
    def _sort_key(r):
        return (
            0 if r.get('reachable') else 1,
            r.get('p50_ms', 99999),
        )
    results.sort(key=_sort_key)

    import time as _t
    payload = {
        'status':      'ok',
        'rows':        results,
        'probed_at':   _t.strftime('%Y-%m-%dT%H:%M:%SZ', _t.gmtime()),
        'parallelism': 12,
        'sample_count': 5,
        'totals': {
            'rows':       len(results),
            'reachable':  sum(1 for r in results if r.get('reachable')),
            'regions':    sum(1 for r in results if r.get('type') == 'region'),
            'local_zones': sum(1 for r in results if r.get('type') == 'local-zone'),
        },
    }
    cache.set_(cache_key, payload)
    return jsonify({**payload, 'cached': False})


# Allowed dropdown values that match the reference benchsuite UI exactly.
_ALLOWED_PERCENTILES = {'p_10', 'p_25', 'p_50', 'p_75', 'p_90', 'p_98', 'p_99'}
_ALLOWED_TIMEFRAMES  = {'1D', '1W', '1M', '1Y'}


@awsref_bp.route('/awsref/api/cloudping-matrix')
def api_cloudping_matrix():
    """Full pairwise AWS region × region latency matrix, augmented with LZ
    rows/columns by mirroring each LZ's parent region row & column.

    Query params:
        percentile — one of p_10/p_25/p_50/p_75/p_90/p_98/p_99 (default p_50)
        timeframe  — one of 1D/1W/1M/1Y (default 1D)
        refresh    — '1' bypasses cache

    Without a CLOUDPING_PROXY_URL env var, only p_50/1D is fetchable from
    cloudping.co's public homepage; non-default selections return the same
    p_50/1D data with `metadata.data_substituted=True` so the UI can warn.
    """
    pct = request.args.get('percentile', 'p_50')
    tf  = request.args.get('timeframe',  '1D')
    if pct not in _ALLOWED_PERCENTILES or tf not in _ALLOWED_TIMEFRAMES:
        return jsonify({'status': 'error',
                        'error':  'invalid percentile or timeframe'}), 400

    cache_key = f'cloudping_matrix::{pct}::{tf}'
    if request.args.get('refresh') != '1':
        cached = cache.get(cache_key, cache._REGIONAL_JSON_TTL)
        if cached is not None:
            return jsonify({**cached, 'cached': True})

    region_names = {r['code']: r['name'] for r in aws_catalog.AWS_REGIONS}
    result = public_sources.fetch_cloudping_matrix(
        percentile=pct,
        timeframe=tf,
        lz_by_region=aws_catalog.LZ_BY_REGION,
        region_names=region_names,
        lz_city_names=aws_catalog.LZ_CITY_NAMES,
    )
    if result.get('status') != 'ok':
        return jsonify(result), 502

    cache.set_(cache_key, result)
    return jsonify({**result, 'cached': False})


@awsref_bp.route('/awsref/api/lz-services')
def api_lz_services():
    """Local Zone services catalog — every AWS service AWS publishes for the
    parent region, with supported/partial/unsupported status and notes.

    Three data layers, merged in priority order:
      1. Hand-curated entries (verified-live nuance + bespoke notes)
      2. Auto-derived from our internal SERVICE_CATALOG (lz_scope-based)
      3. AWS's public regional-services JSON (every service AWS publishes)

    Layer 3 makes the catalog comprehensive — typically 180+ entries per LZ.
    """
    raw = request.args.get('region', '')
    if not _valid_region(raw):
        return jsonify({'status': 'error', 'error': 'invalid region'}), 400
    parent = aws_catalog.parent_region(raw)
    is_lz  = (raw != parent)

    # Layer 3: fetch AWS's regional-services JSON (24h cache). On failure,
    # fall back to layers 1+2 — we still ship ~40 entries.
    regional_services = []
    aws_rt_status = 'skipped'
    if is_lz:
        cache_key = 'aws_regional_services_v1'
        cached = cache.get(cache_key, cache._REGIONAL_JSON_TTL)
        if cached is None:
            try:
                raw_json = public_sources.fetch_regional_services(timeout=20.0)
                cache.set_(cache_key, raw_json)
                cached = raw_json
                aws_rt_status = 'fresh'
            except Exception as exc:
                aws_rt_status = f'error: {exc}'
                cached = None
        else:
            aws_rt_status = 'cached'

        if cached:
            region_map = public_sources.regional_services_to_region_map(cached)
            regional_services = sorted(region_map.get(parent, []))

    entries = aws_catalog.lz_services_catalog(raw, regional_services) if is_lz else []
    stats = {'supported':   sum(1 for e in entries if e['status'] == 'supported'),
             'partial':     sum(1 for e in entries if e['status'] == 'partial'),
             'unsupported': sum(1 for e in entries if e['status'] == 'unsupported')}
    src_counts = {'curated': sum(1 for e in entries if e.get('source') == 'curated'),
                  'derived': sum(1 for e in entries if e.get('source') == 'derived'),
                  'aws-rt':  sum(1 for e in entries if e.get('source') == 'aws-rt')}
    return jsonify({
        'status':       'ok',
        'region':       parent,
        'lz':           raw if is_lz else None,
        'is_lz':        is_lz,
        'city':         aws_catalog.lz_city(raw) if is_lz else None,
        'entries':      entries,
        'totals':       {'entries': len(entries), **stats},
        'source_counts': src_counts,
        'aws_rt':       aws_rt_status,
        'parent_published_services': len(regional_services),
        'source':       'ScanBox static catalog + AWS regional-services JSON',
    })


@awsref_bp.route('/awsref/api/lz-instance-types')
def api_lz_instance_types():
    """Local Zone EC2 instance type offerings. Without AWS credentials we
    return the generic c7i + m7i families AWS has standardised for current-
    generation LZs. For LZ-specific real lists, run
    `aws ec2 describe-instance-type-offerings --location-type
    availability-zone --filters Name=location,Values=<lz>` with valid
    credentials in an AWS shell.
    """
    raw = request.args.get('region', '')
    if not _valid_region(raw):
        return jsonify({'status': 'error', 'error': 'invalid region'}), 400
    parent = aws_catalog.parent_region(raw)
    is_lz  = (raw != parent)
    if not is_lz:
        return jsonify({'status': 'ok', 'region': parent, 'is_lz': False,
                        'instance_types': [], 'source': 'not an LZ'})
    return jsonify({
        'status':         'ok',
        'region':         parent,
        'lz':             raw,
        'is_lz':          True,
        'instance_types': aws_catalog.LZ_INSTANCE_TYPES_DEFAULT,
        'note':           'Standard current-gen LZ families (c7i + m7i). '
                          'Run DescribeInstanceTypeOfferings with AWS credentials '
                          'for a live, LZ-specific list.',
        'source':         'ScanBox static catalog (LZ_INSTANCE_TYPES_DEFAULT)',
    })


@awsref_bp.route('/awsref/api/endpoints')
def api_endpoints():
    """TCP-probe every AWS service endpoint in a given region. Useful for
    spotting service-specific reachability issues (e.g. egress filter
    blocking only the Bedrock endpoint)."""
    raw_region = request.args.get('region', 'eu-central-1')
    if not _valid_region(raw_region):
        return jsonify({'status': 'error', 'error': 'invalid region'}), 400
    parent = aws_catalog.parent_region(raw_region)

    cache_key = f'endpoints_probe::{parent}'
    if request.args.get('refresh') != '1':
        cached = cache.get(cache_key, cache._PROBE_TTL)
        if cached is not None:
            return jsonify({**cached, 'cached': True})

    services = aws_catalog.services_for_region(raw_region)
    targets = [{
        'id':       s['id'],
        'service':  s['name'],
        'category': s['category'],
        'host':     s['endpoint'],
        'port':     s['port'],
        'lz_scope': s['lz_scope'],
    } for s in services
        # Skip link-local IMDS — only reachable from inside an EC2 instance.
        if not s['endpoint'].startswith('169.254.')]

    results = probe.probe_many(targets, max_workers=12, samples=5, timeout=2.5)
    # Reachable first, then by latency.
    results.sort(key=lambda r: (0 if r.get('reachable') else 1, r.get('p50_ms', 99999)))

    import time as _t
    payload = {
        'status':     'ok',
        'region':     parent,
        'raw_region': raw_region,
        'endpoints':  results,
        'probed_at':  _t.strftime('%Y-%m-%dT%H:%M:%SZ', _t.gmtime()),
        'totals': {
            'total':     len(results),
            'reachable': sum(1 for r in results if r.get('reachable')),
        },
    }
    cache.set_(cache_key, payload)
    return jsonify({**payload, 'cached': False})
