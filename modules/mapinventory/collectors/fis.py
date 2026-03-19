"""
Map Inventory — AWS Fault Injection Simulator (FIS) Collector
Resource types: experiment-template
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_fis_resources(session, region, account_id):
    """Collect FIS experiment templates in the given region."""
    resources = []
    try:
        client = session.client('fis', region_name=region)
    except Exception:
        return resources

    # ── Experiment Templates ────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_experiment_templates')
        for page in paginator.paginate():
            for et in page.get('experimentTemplates', []):
                eid = et.get('id', '')
                tags_dict = et.get('tags', {})
                resources.append(make_resource(
                    service='fis',
                    resource_type='experiment-template',
                    resource_id=eid,
                    arn=f'arn:aws:fis:{region}:{account_id}:experiment-template/{eid}',
                    name=et.get('description', eid) or eid,
                    region=region,
                    details={
                        'description': et.get('description', ''),
                        'creation_time': str(et.get('creationTime', '')),
                        'last_update_time': str(et.get('lastUpdateTime', '')),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
