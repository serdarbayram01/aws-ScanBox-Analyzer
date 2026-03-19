"""
Map Inventory — AWS Device Farm Collector
Resource types: project
Only available in us-west-2.
"""

from .base import make_resource, tags_to_dict


def collect_devicefarm_resources(session, region, account_id):
    """Collect Device Farm projects (us-west-2 only)."""
    resources = []
    # Device Farm is only available in us-west-2
    if region != 'us-west-2':
        return resources
    try:
        client = session.client('devicefarm', region_name='us-west-2')
    except Exception:
        return resources

    # ── Projects ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_projects')
        for page in paginator.paginate():
            for p in page.get('projects', []):
                arn = p.get('arn', '')
                name = p.get('name', '')
                pid = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='devicefarm',
                    resource_type='project',
                    resource_id=pid,
                    arn=arn,
                    name=name or pid,
                    region='us-west-2',
                    details={
                        'created': str(p.get('created', '')),
                        'default_job_timeout_minutes': p.get('defaultJobTimeoutMinutes', 0),
                    },
                ))
    except Exception:
        pass

    return resources
