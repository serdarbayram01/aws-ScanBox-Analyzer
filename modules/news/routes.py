"""
News module — Flask routes.

URL surface:
    GET  /news                 -> render the page
    GET  /news/api/feed        -> JSON of the cached feed (no network)
    POST /news/api/refresh     -> fetch + merge + persist (5 min soft TTL,
                                  pass ?force=1 to bypass)
"""

from flask import Blueprint, jsonify, render_template, request

from . import fetcher

news_bp = Blueprint('news', __name__)


@news_bp.route('/news')
def index():
    return render_template('news/index.html')


@news_bp.route('/news/api/feed')
def api_feed():
    feed = fetcher.load()
    # Re-evaluate isNew on every read so badges don't go stale across days.
    feed['items'] = fetcher._refresh_isnew_flags(feed.get('items', []))
    return jsonify({'status': 'ok', **feed})


@news_bp.route('/news/api/refresh', methods=['POST'])
def api_refresh():
    force = request.args.get('force') == '1'
    try:
        feed, refreshed = fetcher.refresh(force=force)
    except Exception as e:  # noqa: BLE001 - surface upstream RSS errors verbatim
        return jsonify({'status': 'error', 'error': str(e)}), 502
    return jsonify({
        'status':      'ok',
        'refreshed':   refreshed,
        'lastUpdated': feed.get('lastUpdated'),
        'itemCount':   feed.get('itemCount', 0),
    })
