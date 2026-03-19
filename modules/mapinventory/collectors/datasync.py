"""
Map Inventory — AWS DataSync Collector
Resource types: task, agent, location
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_datasync_resources(session, region, account_id):
    """Collect DataSync resources in the given region."""
    resources = []
    try:
        client = session.client('datasync', region_name=region)
    except Exception:
        return resources

    # ── Agents ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_agents')
        for page in paginator.paginate():
            for a in page.get('Agents', []):
                arn = a.get('AgentArn', '')
                name = a.get('Name', arn.split('/')[-1] if '/' in arn else arn)
                resources.append(make_resource(
                    service='datasync',
                    resource_type='agent',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': a.get('Status', ''),
                        'platform': str(a.get('Platform', {})),
                    },
                ))
    except Exception:
        pass

    # ── Tasks ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_tasks')
        for page in paginator.paginate():
            for t in page.get('Tasks', []):
                arn = t.get('TaskArn', '')
                name = t.get('Name', arn.split('/')[-1] if '/' in arn else arn)
                resources.append(make_resource(
                    service='datasync',
                    resource_type='task',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': t.get('Status', ''),
                    },
                ))
    except Exception:
        pass

    # ── Locations ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_locations')
        for page in paginator.paginate():
            for loc in page.get('Locations', []):
                arn = loc.get('LocationArn', '')
                uri = loc.get('LocationUri', '')
                resources.append(make_resource(
                    service='datasync',
                    resource_type='location',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=uri or arn,
                    region=region,
                    details={
                        'location_uri': uri,
                    },
                ))
    except Exception:
        pass

    return resources
