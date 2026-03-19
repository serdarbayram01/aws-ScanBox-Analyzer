"""
Map Inventory — AWS Resource Groups Collector
Resource types: group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_resourcegroups_resources(session, region, account_id):
    """Collect Resource Groups in the given region."""
    resources = []
    try:
        client = session.client('resource-groups', region_name=region)
    except Exception:
        return resources

    # ── Groups ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_groups')
        for page in paginator.paginate():
            for g in page.get('Groups', []):
                name = g.get('Name', '')
                arn = g.get('GroupArn', '')
                resources.append(make_resource(
                    service='resourcegroups',
                    resource_type='group',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': g.get('Description', ''),
                    },
                ))
    except Exception:
        pass

    return resources
