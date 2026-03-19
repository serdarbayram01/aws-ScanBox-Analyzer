"""
Map Inventory — AWS X-Ray Collector
Resource types: group, sampling-rule
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_xray_resources(session, region, account_id):
    """Collect X-Ray groups and sampling rules in the given region."""
    resources = []
    try:
        client = session.client('xray', region_name=region)
    except Exception:
        return resources

    # ── Groups ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_groups')
        for page in paginator.paginate():
            for g in page.get('Groups', []):
                name = g.get('GroupName', '')
                arn = g.get('GroupARN', '')
                is_default = (name == 'Default')
                resources.append(make_resource(
                    service='xray',
                    resource_type='group',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'filter_expression': g.get('FilterExpression', ''),
                        'insights_enabled': g.get('InsightsConfiguration', {}).get('InsightsEnabled', False),
                        'notifications_enabled': g.get('InsightsConfiguration', {}).get('NotificationsEnabled', False),
                    },
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Sampling Rules ──────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_sampling_rules')
        for page in paginator.paginate():
            for sr in page.get('SamplingRuleRecords', []):
                rule = sr.get('SamplingRule', {})
                name = rule.get('RuleName', '')
                arn = rule.get('RuleARN', '')
                is_default = (name == 'Default')
                resources.append(make_resource(
                    service='xray',
                    resource_type='sampling-rule',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'priority': rule.get('Priority', 0),
                        'fixed_rate': rule.get('FixedRate', 0),
                        'reservoir_size': rule.get('ReservoirSize', 0),
                        'service_name': rule.get('ServiceName', ''),
                        'service_type': rule.get('ServiceType', ''),
                        'host': rule.get('Host', ''),
                        'http_method': rule.get('HTTPMethod', ''),
                        'url_path': rule.get('URLPath', ''),
                        'resource_arn': rule.get('ResourceARN', ''),
                        'version': rule.get('Version', 1),
                        'modified_at': str(sr.get('ModifiedAt', '')),
                        'created_at': str(sr.get('CreatedAt', '')),
                    },
                    is_default=is_default,
                ))
    except Exception:
        pass

    return resources
