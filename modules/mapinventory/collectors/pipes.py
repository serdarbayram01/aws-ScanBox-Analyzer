"""
Map Inventory — EventBridge Pipes Collector
Resource types: pipe
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_pipes_resources(session, region, account_id):
    """Collect EventBridge Pipes resources in the given region."""
    resources = []
    try:
        client = session.client('pipes', region_name=region)
    except Exception:
        return resources

    # ── Pipes ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_pipes')
        for page in paginator.paginate():
            for p in page.get('Pipes', []):
                name = p.get('Name', '')
                arn = p.get('Arn', '')
                resources.append(make_resource(
                    service='pipes',
                    resource_type='pipe',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'source': p.get('Source', ''),
                        'target': p.get('Target', ''),
                        'desired_state': p.get('DesiredState', ''),
                        'current_state': p.get('CurrentState', ''),
                        'creation_time': str(p.get('CreationTime', '')),
                        'last_modified_time': str(p.get('LastModifiedTime', '')),
                        'enrichment': p.get('Enrichment', ''),
                    },
                ))
    except Exception:
        pass

    return resources
