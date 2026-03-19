"""
Map Inventory — Amazon Managed Service for Prometheus (AMP) Collector
Resource types: workspace
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_amp_resources(session, region, account_id):
    """Collect Amazon Managed Prometheus workspaces in the given region."""
    resources = []
    try:
        client = session.client('amp', region_name=region)
    except Exception:
        return resources

    # ── Workspaces ───────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_workspaces(**kwargs)
            for ws in resp.get('workspaces', []):
                ws_id = ws.get('workspaceId', '')
                ws_alias = ws.get('alias', '')
                ws_arn = ws.get('arn', '')
                status = ws.get('status', {}).get('statusCode', '')
                created = str(ws.get('createdAt', ''))

                tags = ws.get('tags', {})

                resources.append(make_resource(
                    service='amp',
                    resource_type='workspace',
                    resource_id=ws_id,
                    arn=ws_arn,
                    name=ws_alias or ws_id,
                    region=region,
                    details={
                        'alias': ws_alias,
                        'status': status,
                        'created_at': created,
                        'prometheus_endpoint': ws.get('prometheusEndpoint', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
