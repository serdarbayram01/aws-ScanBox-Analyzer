"""
Map Inventory — Amazon Managed Grafana Collector
Resource types: workspace
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_grafana_resources(session, region, account_id):
    """Collect Amazon Managed Grafana workspaces in the given region."""
    resources = []
    try:
        client = session.client('grafana', region_name=region)
    except Exception:
        return resources

    # ── Workspaces ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_workspaces')
        for page in paginator.paginate():
            for ws in page.get('workspaces', []):
                wid = ws.get('id', '')
                arn = f'arn:aws:grafana:{region}:{account_id}:/workspaces/{wid}'
                name = ws.get('name', wid)
                details = {
                    'status': ws.get('status', ''),
                    'endpoint': ws.get('endpoint', ''),
                    'grafana_version': ws.get('grafanaVersion', ''),
                    'authentication': str(ws.get('authentication', {}).get('providers', [])),
                    'created': str(ws.get('created', '')),
                    'modified': str(ws.get('modified', '')),
                }
                tags_dict = ws.get('tags', {})
                resources.append(make_resource(
                    service='grafana',
                    resource_type='workspace',
                    resource_id=wid,
                    arn=arn,
                    name=name,
                    region=region,
                    details=details,
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
