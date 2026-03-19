"""
Map Inventory — AWS Resilience Hub Collector
Resource types: app, resiliency-policy
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_resiliencehub_resources(session, region, account_id):
    """Collect Resilience Hub resources in the given region."""
    resources = []
    try:
        client = session.client('resiliencehub', region_name=region)
    except Exception:
        return resources

    # ── Apps ────────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_apps')
        for page in paginator.paginate():
            for a in page.get('appSummaries', []):
                arn = a.get('appArn', '')
                name = a.get('name', arn.split('/')[-1] if '/' in arn else arn)
                resources.append(make_resource(
                    service='resiliencehub',
                    resource_type='app',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': a.get('description', ''),
                        'compliance_status': a.get('complianceStatus', ''),
                        'assessment_schedule': a.get('assessmentSchedule', ''),
                        'resiliency_score': a.get('resiliencyScore', 0),
                        'status': a.get('status', ''),
                        'creation_time': str(a.get('creationTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Resiliency Policies ─────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_resiliency_policies')
        for page in paginator.paginate():
            for p in page.get('resiliencyPolicies', []):
                arn = p.get('policyArn', '')
                name = p.get('policyName', arn.split('/')[-1] if '/' in arn else arn)
                tags_dict = p.get('tags', {})
                resources.append(make_resource(
                    service='resiliencehub',
                    resource_type='resiliency-policy',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': p.get('policyDescription', ''),
                        'tier': p.get('tier', ''),
                        'estimated_cost_tier': p.get('estimatedCostTier', ''),
                        'creation_time': str(p.get('creationTime', '')),
                        'policy': str(p.get('policy', {})),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
