"""
Map Inventory — MediaPackage Collector
Resource types: channel, origin-endpoint
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_mediapackage_resources(session, region, account_id):
    """Collect MediaPackage resources in the given region."""
    resources = []
    try:
        client = session.client('mediapackage', region_name=region)
    except Exception:
        return resources

    # ── Channels ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_channels')
        for page in paginator.paginate():
            for ch in page.get('Channels', []):
                cid = ch.get('Id', '')
                arn = ch.get('Arn', '')
                tags_dict = ch.get('Tags', {})
                resources.append(make_resource(
                    service='mediapackage',
                    resource_type='channel',
                    resource_id=cid,
                    arn=arn,
                    name=ch.get('Description', cid) or cid,
                    region=region,
                    details={
                        'description': ch.get('Description', ''),
                        'hls_ingest': str(ch.get('HlsIngest', {})),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Origin Endpoints ────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_origin_endpoints')
        for page in paginator.paginate():
            for ep in page.get('OriginEndpoints', []):
                eid = ep.get('Id', '')
                arn = ep.get('Arn', '')
                tags_dict = ep.get('Tags', {})
                resources.append(make_resource(
                    service='mediapackage',
                    resource_type='origin-endpoint',
                    resource_id=eid,
                    arn=arn,
                    name=ep.get('Description', eid) or eid,
                    region=region,
                    details={
                        'channel_id': ep.get('ChannelId', ''),
                        'description': ep.get('Description', ''),
                        'url': ep.get('Url', ''),
                        'origination': ep.get('Origination', ''),
                        'startover_window_seconds': ep.get('StartoverWindowSeconds', 0),
                        'time_delay_seconds': ep.get('TimeDelaySeconds', 0),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
