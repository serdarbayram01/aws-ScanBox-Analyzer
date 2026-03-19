"""
Map Inventory — MediaStore Collector
Resource types: container
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_mediastore_resources(session, region, account_id):
    """Collect MediaStore containers in the given region."""
    resources = []
    try:
        client = session.client('mediastore', region_name=region)
    except Exception:
        return resources

    # ── Containers ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_containers')
        for page in paginator.paginate():
            for c in page.get('Containers', []):
                name = c.get('Name', '')
                arn = c.get('ARN', '')
                tags_dict = {}
                try:
                    tag_resp = client.list_tags_for_resource(Resource=arn)
                    tags_dict = {t['Key']: t['Value'] for t in tag_resp.get('Tags', []) if isinstance(t, dict)}
                except Exception:
                    pass
                resources.append(make_resource(
                    service='mediastore',
                    resource_type='container',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': c.get('Status', ''),
                        'endpoint': c.get('Endpoint', ''),
                        'creation_time': str(c.get('CreationTime', '')),
                        'access_logging_enabled': c.get('AccessLoggingEnabled', False),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
