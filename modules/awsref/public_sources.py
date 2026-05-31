"""Fetchers for AWS public JSON sources — no auth, no boto3, no signing.

These are the same URLs the AWS Console itself fetches over plain HTTPS GET
to render region/service availability tables. We use them as the ground
truth for *which* services AWS publishes in *which* regions.

Also includes a scraper for cloudping.co — the cloudping.co homepage server-
side-renders a pairwise AWS region latency matrix into its Next.js RSC
payload, which we extract via regex. No authentication required.

Optional upstream: if `CLOUDPING_PROXY_URL` env var is set, we proxy through
that server (which is expected to expose `/api/cloudping?percentile=X&
timeframe=Y` returning the reference benchsuite shape). This unlocks the
full P10..P99 × 1D/1W/1M/1Y matrix instead of just P50/1D from the public
homepage scrape."""

import json
import os
import re
import urllib.error
import urllib.request

# AWS Console's region-service availability table (public, JSON, no auth).
REGIONAL_TABLE_URL = 'https://api.regional-table.region-services.aws.a2z.com/index.json'

# AWS public IP-ranges JSON — each entry tagged with region and service.
IP_RANGES_URL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'

# cloudping.co homepage: SSR'd HTML containing the embedded pairwise matrix
# for the default percentile/timeframe (p50/1D). Other combinations are
# client-side AJAX-only and require an authenticated session.
CLOUDPING_HOME_URL = 'https://www.cloudping.co/'

_UA = 'ScanBox-AWSRef/2.0 (+https://github.com/serdarbayram01/aws-ScanBox-Analyzer)'

# Matches every '<region-from>:{<region-to>:ms,...}' block in the Next.js
# RSC stream where strings are backslash-escaped. Region code shape:
# 2-letter geo + dash + word(s) + dash + digit (e.g. eu-central-1, ap-east-2).
_CP_ROW_RE  = re.compile(r'\\"([a-z][a-z0-9-]+)\\":\{((?:\\"[a-z][a-z0-9-]+\\":[\d.]+,?)+)\}')
_CP_PAIR_RE = re.compile(r'\\"([a-z][a-z0-9-]+)\\":([\d.]+)')


def _fetch_json(url: str, timeout: float = 15.0) -> dict:
    """Plain HTTPS GET returning parsed JSON. No auth headers, no signing.
    Raises urllib.error on network or parse failure."""
    req = urllib.request.Request(url, headers={
        'User-Agent': _UA,
        'Accept':     'application/json',
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_regional_services(timeout: float = 15.0) -> dict:
    """Return parsed AWS regional-services JSON. Shape (as of 2026-05):

        {
          "prices": [
            {"id": "service:region",
             "attributes": {
                "aws:region":      "us-east-1",
                "aws:serviceName": "Amazon EC2",
                "aws:serviceUrl":  "/ec2/...",
                "aws:productUrl":  "/...",
             }},
            ...
          ],
          "metadata": {...}
        }

    Raises urllib.error on failure — caller decides whether to fall back to
    the static catalog."""
    return _fetch_json(REGIONAL_TABLE_URL, timeout)


def fetch_ip_ranges(timeout: float = 15.0) -> dict:
    """Return parsed AWS IP-ranges JSON.

        {
          "syncToken": "...",
          "createDate": "2026-05-15-...",
          "prefixes":   [{"ip_prefix": "...", "region": "...", "service": "..."}, ...],
          "ipv6_prefixes": [...]
        }
    """
    return _fetch_json(IP_RANGES_URL, timeout)


# Intra-region (parent region ↔ its own LZ, or two LZs sharing a parent) is
# treated as a small constant since cloudping doesn't measure it. Matches the
# reference benchsuite's choice (~3.5 ms placeholder).
_INTRA_REGION_MS = 3.5


def _augment_with_lzs(region_matrix: dict, lz_by_region: dict) -> tuple:
    """Mirror each LZ's parent region row/column into the matrix to produce a
    full (regions + LZs) × (regions + LZs) grid.

    Returns (data, codes, types, parents) where:
        data[from_code][to_code] -> latency_ms (None for unmeasured)
        codes  -> sorted list of all codes (regions + LZs)
        types  -> {code: 'region' | 'local-zone'}
        parents -> {lz_code: parent_region_code}
    """
    # Build parent map: each region maps to itself; each LZ to its parent.
    parents = {}
    types = {}
    for region in region_matrix:
        parents[region] = region
        types[region] = 'region'
    for parent, lzs in lz_by_region.items():
        for lz in lzs:
            parents[lz] = parent
            types[lz] = 'local-zone'
            # If the parent isn't in cloudping data, skip — LZ has no anchor.
            if parent not in region_matrix:
                continue

    all_codes = sorted(parents.keys())
    data = {}
    for from_code in all_codes:
        from_parent = parents[from_code]
        if from_parent not in region_matrix:
            continue
        parent_row = region_matrix[from_parent]
        row = {}
        for to_code in all_codes:
            if from_code == to_code:
                continue  # self diagonal — rendered as "—"
            to_parent = parents[to_code]
            if from_parent == to_parent:
                row[to_code] = _INTRA_REGION_MS
            elif to_parent in region_matrix:
                v = parent_row.get(to_parent)
                if v is not None:
                    row[to_code] = v
        data[from_code] = row
    return data, all_codes, types, parents


def _fetch_from_proxy(proxy_url: str, percentile: str, timeframe: str,
                     timeout: float = 20.0) -> dict:
    """Fetch matrix from a benchsuite-compatible proxy (reference Go server
    shape). Returns the parsed JSON or raises urllib.error."""
    url = proxy_url.rstrip('/') + f'/api/cloudping?percentile={percentile}&timeframe={timeframe}'
    req = urllib.request.Request(url, headers={
        'User-Agent': _UA, 'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_cloudping_matrix(percentile: str = 'p_50', timeframe: str = '1D',
                           timeout: float = 20.0,
                           lz_by_region: dict = None,
                           region_names: dict = None,
                           lz_city_names: dict = None) -> dict:
    """Fetch the AWS region × region latency matrix (augmented with LZ rows
    and columns) for a given percentile/timeframe.

    Resolution order:
      1. If `CLOUDPING_PROXY_URL` env var is set, GET it. The proxy is
         expected to be a benchsuite-compatible server. This unlocks all
         P10..P99 × 1D/1W/1M/1Y combinations.
      2. Otherwise scrape cloudping.co's public homepage — this only carries
         P50/1D data. Non-default requests are honoured by returning the
         P50/1D dataset with `metadata.data_substituted=True` so the caller
         can warn the user.

    Returns the reference benchsuite shape:
        {
          'status':   'ok'|'error',
          'metadata': {percentile, timeframe, fetched_at, source,
                       augmented, unit, data_substituted (optional)},
          'data':     {from_code: {to_code: ms, ...}, ...},
          'codes':    [...],            # sorted, regions + LZs
          'types':    {code: 'region'|'local-zone'},
          'parents':  {lz_code: parent_region_code},
          'names':    {code: 'Friendly Name'},
        }
    """
    import time as _t
    lz_by_region  = lz_by_region  or {}
    region_names  = region_names  or {}
    lz_city_names = lz_city_names or {}

    proxy_url = os.environ.get('CLOUDPING_PROXY_URL', '').strip()

    # -------- 1) Try proxy first if configured --------
    if proxy_url:
        try:
            data = _fetch_from_proxy(proxy_url, percentile, timeframe, timeout)
            if 'data' in data and 'codes' in data:
                # Proxy already returned benchsuite shape — pass it through
                # and just normalise the source/unit fields.
                md = dict(data.get('metadata') or {})
                md.setdefault('source', f'proxied via {proxy_url}')
                md.setdefault('unit', 'milliseconds')
                md.setdefault('augmented',
                              "Local Zones added by mirroring their parent region's row & column")
                names = data.get('names') or region_names
                return {
                    'status':   'ok',
                    'metadata': md,
                    'data':     data['data'],
                    'codes':    data['codes'],
                    'types':    data.get('types', {}),
                    'parents':  data.get('parents', {}),
                    'names':    names,
                }
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            # Fall through to homepage scrape on proxy failure.
            proxy_err = str(exc)
        else:
            proxy_err = None
    else:
        proxy_err = None

    # -------- 2) Scrape cloudping.co homepage (only P50/1D) --------
    req = urllib.request.Request(CLOUDPING_HOME_URL, headers={
        'User-Agent': _UA,
        'Accept':     'text/html,application/xhtml+xml',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except (urllib.error.URLError, TimeoutError) as exc:
        return {'status': 'error',
                'error':  f'Could not reach cloudping.co: {exc}'}

    region_matrix = {}
    for from_r, payload in _CP_ROW_RE.findall(html):
        pairs = _CP_PAIR_RE.findall(payload)
        if not pairs:
            continue
        region_matrix[from_r] = {to: float(ms) for to, ms in pairs}

    if not region_matrix:
        return {'status': 'error',
                'error':  'cloudping.co page did not contain an embedded matrix '
                          '(layout may have changed)'}

    # Augment with LZ rows/columns
    data, codes, types, parents = _augment_with_lzs(region_matrix, lz_by_region)

    # Build friendly names: regions use given names map; LZs use city name
    # parsed from the LZ code's 3-letter slug.
    names = {}
    for c in codes:
        if c in region_names:
            names[c] = region_names[c]
        else:
            # LZ codes look like "us-east-1-bos-1a" — slug is the 4th segment
            parts = c.split('-')
            slug = parts[3] if len(parts) >= 5 else c
            names[c] = lz_city_names.get(slug, slug.upper())

    requested_default = (percentile == 'p_50' and timeframe == '1D')
    md = {
        'percentile':  percentile,
        'timeframe':   timeframe,
        'fetched_at':  _t.strftime('%Y-%m-%dT%H:%M:%SZ', _t.gmtime()),
        'source':      'cloudping.co (homepage SSR scrape — no API key)',
        'augmented':   "Local Zones added by mirroring their parent region's row & column",
        'unit':        'milliseconds',
    }
    if not requested_default:
        # Honest disclosure: the data is P50/1D regardless of what was asked.
        md['data_substituted'] = True
        md['actual_percentile'] = 'p_50'
        md['actual_timeframe']  = '1D'
        if proxy_err:
            md['proxy_error'] = proxy_err

    return {
        'status':   'ok',
        'metadata': md,
        'data':     data,
        'codes':    codes,
        'types':    types,
        'parents':  parents,
        'names':    names,
    }


def regional_services_to_region_map(raw: dict) -> dict:
    """Convert the regional-services JSON into a {region_code: set(service_name)}
    map. Defensive parsing — unknown shapes return an empty map."""
    out = {}
    for item in (raw or {}).get('prices', []) or []:
        attrs = item.get('attributes') or {}
        region = attrs.get('aws:region')
        svc    = attrs.get('aws:serviceName')
        if region and svc:
            out.setdefault(region, set()).add(svc)
    return out
