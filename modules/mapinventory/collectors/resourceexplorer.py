"""
Map Inventory — AWS Resource Explorer Collector
Resource types: index, view
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_resourceexplorer_resources(session, region, account_id):
    """Collect Resource Explorer indexes and views in the given region."""
    resources = []
    try:
        client = session.client('resource-explorer-2', region_name=region)
    except Exception:
        return resources

    # ── Indexes ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_indexes')
        for page in paginator.paginate():
            for idx in page.get('Indexes', []):
                arn = idx.get('Arn', '')
                idx_region = idx.get('Region', region)
                resources.append(make_resource(
                    service='resourceexplorer',
                    resource_type='index',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=f'Resource Explorer Index ({idx_region})',
                    region=idx_region,
                    details={
                        'type': idx.get('Type', ''),
                    },
                ))
    except Exception:
        pass

    # ── Views ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_views')
        for page in paginator.paginate():
            for view_arn in page.get('Views', []):
                name = view_arn.split('/')[-1] if '/' in view_arn else view_arn
                details = {}
                try:
                    resp = client.get_view(ViewArn=view_arn)
                    v = resp.get('View', {})
                    details = {
                        'scope': v.get('Scope', ''),
                        'last_updated_at': str(v.get('LastUpdatedAt', '')),
                        'included_properties': [p.get('Name', '') for p in v.get('IncludedProperties', [])],
                    }
                except Exception:
                    pass
                resources.append(make_resource(
                    service='resourceexplorer',
                    resource_type='view',
                    resource_id=name,
                    arn=view_arn,
                    name=name,
                    region=region,
                    details=details,
                ))
    except Exception:
        pass

    return resources
