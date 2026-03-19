"""
Map Inventory — IoT SiteWise Collector
Resource types: asset, asset-model, gateway, portal
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_iotsitewise_resources(session, region, account_id):
    """Collect IoT SiteWise resources in the given region."""
    resources = []
    try:
        client = session.client('iotsitewise', region_name=region)
    except Exception:
        return resources

    # ── Asset Models ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_asset_models')
        for page in paginator.paginate():
            for m in page.get('assetModelSummaries', []):
                mid = m.get('id', '')
                arn = m.get('arn', '')
                resources.append(make_resource(
                    service='iotsitewise',
                    resource_type='asset-model',
                    resource_id=mid,
                    arn=arn,
                    name=m.get('name', mid),
                    region=region,
                    details={
                        'description': m.get('description', ''),
                        'status': str(m.get('status', {}).get('state', '')),
                        'creation_date': str(m.get('creationDate', '')),
                        'last_update_date': str(m.get('lastUpdateDate', '')),
                    },
                ))
    except Exception:
        pass

    # ── Assets ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_assets')
        for page in paginator.paginate(filter='TOP_LEVEL'):
            for a in page.get('assetSummaries', []):
                aid = a.get('id', '')
                arn = a.get('arn', '')
                resources.append(make_resource(
                    service='iotsitewise',
                    resource_type='asset',
                    resource_id=aid,
                    arn=arn,
                    name=a.get('name', aid),
                    region=region,
                    details={
                        'asset_model_id': a.get('assetModelId', ''),
                        'status': str(a.get('status', {}).get('state', '')),
                        'creation_date': str(a.get('creationDate', '')),
                        'last_update_date': str(a.get('lastUpdateDate', '')),
                    },
                ))
    except Exception:
        pass

    # ── Gateways ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_gateways')
        for page in paginator.paginate():
            for g in page.get('gatewaySummaries', []):
                gid = g.get('gatewayId', '')
                resources.append(make_resource(
                    service='iotsitewise',
                    resource_type='gateway',
                    resource_id=gid,
                    arn=f'arn:aws:iotsitewise:{region}:{account_id}:gateway/{gid}',
                    name=g.get('gatewayName', gid),
                    region=region,
                    details={
                        'gateway_platform': str(g.get('gatewayPlatform', {})),
                        'creation_date': str(g.get('creationDate', '')),
                        'last_update_date': str(g.get('lastUpdateDate', '')),
                    },
                ))
    except Exception:
        pass

    # ── Portals ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_portals')
        for page in paginator.paginate():
            for p in page.get('portalSummaries', []):
                pid = p.get('id', '')
                arn = f'arn:aws:iotsitewise:{region}:{account_id}:portal/{pid}'
                resources.append(make_resource(
                    service='iotsitewise',
                    resource_type='portal',
                    resource_id=pid,
                    arn=arn,
                    name=p.get('name', pid),
                    region=region,
                    details={
                        'description': p.get('description', ''),
                        'status': str(p.get('status', {}).get('state', '')),
                        'start_url': p.get('startUrl', ''),
                        'creation_date': str(p.get('creationDate', '')),
                        'last_update_date': str(p.get('lastUpdateDate', '')),
                    },
                ))
    except Exception:
        pass

    return resources
