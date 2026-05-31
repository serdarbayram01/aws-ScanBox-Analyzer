"""
News module — RSS fetcher / parser / persister.

Mirrors the JS reference scripts (fetch-rss.js + parse-rss.js) using stdlib only:
- urllib for HTTP
- regex for RSS parsing (no XML library needed)
- hashlib for stable item IDs (sha256 of URL, first 16 chars)
- threading.Lock for single-flight refresh
- atomic JSON write via os.replace

Public API:
    load()                                   -> dict       (current feed; never raises)
    refresh(force=False)                     -> (dict, bool) (feed, was_refreshed)
    parse_rss(xml_str)                       -> list[dict] (items in the schema)
    fetch_rss(url=RSS_URL, retries=3, ...)   -> str        (raw XML)
"""

import hashlib
import html as _html
import json
import os
import re
import threading
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .aws_services import AWS_SERVICES

RSS_URL    = 'https://aws.amazon.com/about-aws/whats-new/recent/feed/'  # back-compat
DATA_PATH  = os.path.join(os.path.dirname(__file__), 'data', 'whats-new.json')
MAX_ITEMS  = 500
FRESH_TTL  = 300  # seconds — soft freshness for refresh()
USER_AGENT = 'ScanBox-News/1.0 (+https://github.com/serdarbayram01/aws-ScanBox-Analyzer)'

# Multi-feed support. Each entry produces items tagged with `source` (used as
# a primary category badge so the frontend filter dropdown can target it).
# To revert to single-feed behaviour, replace the list with:
#   RSS_FEEDS = [{'source': "What's New", 'url': RSS_URL}]
# and restore fetcher.py.bak.original.
RSS_FEEDS = [
    {'source': "What's New",          'url': 'https://aws.amazon.com/about-aws/whats-new/recent/feed/'},
    {'source': "Official Blog",       'url': 'https://aws.amazon.com/blogs/aws/feed'},
    {'source': "Security Bulletins",  'url': 'https://aws.amazon.com/security/security-bulletins/feed'},
]

_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# RSS parsing helpers (regex-based, ports parse-rss.js verbatim where possible)
# ---------------------------------------------------------------------------

_CDATA_RE    = re.compile(r'<!\[CDATA\[([\s\S]*?)\]\]>')
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_SCRIPT_RE   = re.compile(r'<script[\s\S]*?</script>', re.IGNORECASE)
_STYLE_RE    = re.compile(r'<style[\s\S]*?</style>',   re.IGNORECASE)
_ON_ATTR_RE  = re.compile(r'\son\w+="[^"]*"|\son\w+=\'[^\']*\'', re.IGNORECASE)
_ITEM_RE     = re.compile(r'<item>([\s\S]*?)</item>', re.IGNORECASE)
_WS_RE       = re.compile(r'\s+')


def _extract_tag(xml: str, tag: str) -> str:
    """Return the first <tag>...</tag> body, with CDATA stripped, or ''."""
    m = re.search(rf'<{tag}(?:\s[^>]*)?>([\s\S]*?)</{tag}>', xml, re.IGNORECASE)
    if not m:
        return ''
    return _CDATA_RE.sub(r'\1', m.group(1)).strip()


def _extract_all(xml: str, tag: str):
    """Return every <tag>...</tag> body (CDATA stripped, empty bodies skipped)."""
    out = []
    for m in re.finditer(rf'<{tag}(?:\s[^>]*)?>([\s\S]*?)</{tag}>', xml, re.IGNORECASE):
        val = _CDATA_RE.sub(r'\1', m.group(1)).strip()
        if val:
            out.append(val)
    return out


def _strip_html(s: str) -> str:
    """Decode entities, drop tags, collapse whitespace."""
    return _WS_RE.sub(' ', _HTML_TAG_RE.sub(' ', _html.unescape(s))).strip()


def _sanitize_html(s: str) -> str:
    """Strip <script>/<style> blocks and inline on*= handlers."""
    return _ON_ATTR_RE.sub('', _STYLE_RE.sub('', _SCRIPT_RE.sub('', s))).strip()


def _parse_categories(raws):
    """Convert AWS RSS category paths into clean human labels.

    Examples
    --------
    'marketing:marchitecture/databases,general:products/amazon-timestream'
        -> ['Amazon Timestream']
    'general:products/aws-lambda' -> ['AWS Lambda']
    'Launch'                       -> ['Launch']
    """
    clean = []
    seen = set()
    for raw in raws:
        for part in (p.strip() for p in raw.split(',') if p.strip()):
            segment = part.rsplit('/', 1)[-1] if '/' in part else part
            if not segment:
                continue
            if segment.startswith('marchitecture') or segment == 'marketing':
                continue
            label = segment
            if label.startswith('amazon-'):
                label = 'Amazon ' + label[len('amazon-'):]
            elif label.startswith('aws-'):
                label = 'AWS ' + label[len('aws-'):]
            label = label.replace('-', ' ')
            label = re.sub(r'\b\w', lambda m: m.group(0).upper(), label).strip()
            if len(label) > 1 and label not in seen:
                seen.add(label)
                clean.append(label)
    return clean


def _extract_services(text: str):
    upper = text.upper()
    found = []
    seen = set()
    for svc in AWS_SERVICES:
        pat = r'\b' + re.escape(svc.upper()) + r'\b'
        if re.search(pat, upper) and svc not in seen:
            seen.add(svc)
            found.append(svc)
    return found


def _to_iso(pubdate: str) -> str:
    """Best-effort RFC-2822 / ISO-8601 → ISO-8601 UTC string."""
    if pubdate:
        try:
            dt = parsedate_to_datetime(pubdate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc).isoformat()


def parse_rss(xml: str, source: str = ''):
    """Turn raw RSS XML into a list of WhatsNewItem dicts.

    `source`, when provided, is prepended to each item's categories so the UI
    filter dropdown can target it as a feed-level facet (e.g. "Official Blog").
    """
    items = []
    now   = datetime.now(timezone.utc)
    week  = timedelta(days=7)

    for m in _ITEM_RE.finditer(xml):
        raw = m.group(1)
        title = _extract_tag(raw, 'title')
        link  = _extract_tag(raw, 'link') or _extract_tag(raw, 'guid')
        if not title or not link:
            continue
        description    = _extract_tag(raw, 'description')
        pub_date       = _extract_tag(raw, 'pubDate')
        raw_categories = _extract_all(raw, 'category')

        item_id      = hashlib.sha256(link.encode('utf-8')).hexdigest()[:16]
        published_at = _to_iso(pub_date)
        desc_plain   = _strip_html(description)[:600]
        desc_html    = _sanitize_html(description)
        categories   = _parse_categories(raw_categories)
        # Surface the feed source as the primary category so the existing
        # category filter UI can target it without any frontend changes.
        if source and source not in categories:
            categories.insert(0, source)
        services     = _extract_services(title + ' ' + ' '.join(raw_categories))

        try:
            pub_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            is_new = (now - pub_dt) < week
        except ValueError:
            is_new = False

        tag_set = set()
        tags = []
        for t_ in (*categories, *services):
            tl = t_.lower()
            if tl not in tag_set:
                tag_set.add(tl)
                tags.append(tl)

        items.append({
            'id':              item_id,
            'title':           title,
            'description':     desc_plain,
            'descriptionHtml': desc_html,
            'url':             link,
            'publishedAt':     published_at,
            'updatedAt':       published_at,
            'source':          source or "What's New",
            'categories':      categories,
            'services':        services,
            'tags':            tags,
            'isNew':           is_new,
        })
    return items


# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------

def fetch_rss(url: str = RSS_URL, retries: int = 3, timeout: int = 15) -> str:
    """GET the RSS feed with simple linear backoff (2/4/6 s)."""
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/rss+xml, application/xml;q=0.9, */*;q=0.8'})
            with urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, 'status', 200)
                if status != 200:
                    raise URLError(f'HTTP {status}')
                return resp.read().decode('utf-8', errors='replace')
        except (URLError, HTTPError, TimeoutError, OSError) as e:
            last_err = e
            time.sleep((attempt + 1) * 2)
    raise last_err if last_err else RuntimeError('RSS fetch failed')


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _empty_feed():
    return {'lastUpdated': None, 'itemCount': 0, 'items': []}


def load() -> dict:
    """Read the cached feed JSON. Never raises — returns empty feed on miss."""
    if not os.path.exists(DATA_PATH):
        return _empty_feed()
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_feed()
        data.setdefault('lastUpdated', None)
        items = data.get('items') or []
        data['items']     = items
        data['itemCount'] = len(items)
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_feed()


def _refresh_isnew_flags(items):
    """Recompute isNew on every load-time call so the flag doesn't go stale.
    Also back-fills `source` on legacy cache entries written before multi-feed
    support was introduced — so the filter dropdown groups them correctly."""
    now = datetime.now(timezone.utc)
    week = timedelta(days=7)
    for it in items:
        try:
            pub = datetime.fromisoformat(it['publishedAt'].replace('Z', '+00:00'))
            it['isNew'] = (now - pub) < week
        except (KeyError, ValueError, TypeError):
            it['isNew'] = False
        if not it.get('source'):
            it['source'] = "What's New"
            cats = it.get('categories') or []
            if "What's New" not in cats:
                it['categories'] = ["What's New", *cats]
    return items


def refresh(force: bool = False):
    """Fetch + parse + merge + atomic write.

    Returns
    -------
    (feed_dict, refreshed_bool)
        refreshed_bool is False when the cached file is fresh enough and
        force=False (no network call was made).
    """
    with _LOCK:
        if not force and os.path.exists(DATA_PATH):
            age = time.time() - os.path.getmtime(DATA_PATH)
            if age < FRESH_TTL:
                feed = load()
                feed['items'] = _refresh_isnew_flags(feed.get('items', []))
                return feed, False

        new_items = []
        fetch_errors = []
        for feed in RSS_FEEDS:
            try:
                xml = fetch_rss(feed['url'])
                new_items.extend(parse_rss(xml, source=feed.get('source', '')))
            except Exception as e:  # noqa: BLE001 — record per-feed errors
                fetch_errors.append({'source': feed.get('source', ''), 'error': str(e)})
        # If every feed failed, propagate the first error so callers see it.
        if not new_items and fetch_errors:
            raise RuntimeError(fetch_errors[0]['error'])

        existing = load().get('items', [])

        by_id = {it['id']: it for it in existing}
        for it in new_items:
            by_id[it['id']] = it  # newer overrides older on ID collision

        merged = sorted(by_id.values(), key=lambda x: x.get('publishedAt', ''), reverse=True)[:MAX_ITEMS]
        merged = _refresh_isnew_flags(merged)

        feed = {
            'lastUpdated': datetime.now(timezone.utc).isoformat(),
            'itemCount':   len(merged),
            'items':       merged,
        }

        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        tmp = DATA_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(feed, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_PATH)
        return feed, True
