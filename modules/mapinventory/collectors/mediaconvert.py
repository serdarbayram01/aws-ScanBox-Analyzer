"""
Map Inventory — MediaConvert Collector
Resource types: queue, job-template, preset
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_mediaconvert_resources(session, region, account_id):
    """Collect MediaConvert resources in the given region."""
    resources = []
    try:
        client = session.client('mediaconvert', region_name=region)
    except Exception:
        return resources

    # MediaConvert requires discovering the account endpoint first
    try:
        endpoints = client.describe_endpoints(MaxResults=1)
        endpoint_url = endpoints.get('Endpoints', [{}])[0].get('Url', '')
        if endpoint_url:
            client = session.client('mediaconvert', region_name=region, endpoint_url=endpoint_url)
    except Exception:
        pass

    # ── Queues ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_queues')
        for page in paginator.paginate():
            for q in page.get('Queues', []):
                name = q.get('Name', '')
                arn = q.get('Arn', '')
                is_default = (name == 'Default')
                resources.append(make_resource(
                    service='mediaconvert',
                    resource_type='queue',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': q.get('Status', ''),
                        'pricing_plan': q.get('PricingPlan', ''),
                        'type': q.get('Type', ''),
                        'created_at': str(q.get('CreatedAt', '')),
                    },
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Job Templates ───────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_job_templates')
        for page in paginator.paginate():
            for jt in page.get('JobTemplates', []):
                name = jt.get('Name', '')
                arn = jt.get('Arn', '')
                resources.append(make_resource(
                    service='mediaconvert',
                    resource_type='job-template',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': jt.get('Description', ''),
                        'type': jt.get('Type', ''),
                        'created_at': str(jt.get('CreatedAt', '')),
                        'last_updated': str(jt.get('LastUpdated', '')),
                    },
                ))
    except Exception:
        pass

    # ── Presets ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_presets')
        for page in paginator.paginate():
            for p in page.get('Presets', []):
                name = p.get('Name', '')
                arn = p.get('Arn', '')
                resources.append(make_resource(
                    service='mediaconvert',
                    resource_type='preset',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': p.get('Description', ''),
                        'type': p.get('Type', ''),
                        'created_at': str(p.get('CreatedAt', '')),
                        'last_updated': str(p.get('LastUpdated', '')),
                    },
                ))
    except Exception:
        pass

    return resources
