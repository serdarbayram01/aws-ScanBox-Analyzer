"""
Map Inventory — Amazon DSQL Collector
Resource types: cluster
"""

from .base import make_resource, tags_to_dict


def collect_dsql_resources(session, region, account_id):
    """Collect Amazon DSQL clusters in the given region."""
    resources = []
    try:
        client = session.client('dsql', region_name=region)
    except Exception:
        return resources

    # ── Clusters ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_clusters')
        for page in paginator.paginate():
            for c in page.get('clusters', []):
                cid = c.get('identifier', '')
                arn = c.get('arn', f'arn:aws:dsql:{region}:{account_id}:cluster/{cid}')
                resources.append(make_resource(
                    service='dsql',
                    resource_type='cluster',
                    resource_id=cid,
                    arn=arn,
                    name=cid,
                    region=region,
                    details={
                        'status': c.get('status', ''),
                    },
                ))
    except Exception:
        pass

    return resources
