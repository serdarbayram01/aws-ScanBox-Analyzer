"""
Map Inventory — MediaConnect Collector
Resource types: flow
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_mediaconnect_resources(session, region, account_id):
    """Collect MediaConnect flows in the given region."""
    resources = []
    try:
        client = session.client('mediaconnect', region_name=region)
    except Exception:
        return resources

    # ── Flows ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_flows')
        for page in paginator.paginate():
            for f in page.get('Flows', []):
                fid = f.get('FlowArn', '').split(':')[-1] if f.get('FlowArn') else f.get('Name', '')
                arn = f.get('FlowArn', '')
                resources.append(make_resource(
                    service='mediaconnect',
                    resource_type='flow',
                    resource_id=fid,
                    arn=arn,
                    name=f.get('Name', fid),
                    region=region,
                    details={
                        'status': f.get('Status', ''),
                        'description': f.get('Description', ''),
                        'availability_zone': f.get('AvailabilityZone', ''),
                        'source_type': f.get('SourceType', ''),
                    },
                ))
    except Exception:
        pass

    return resources
