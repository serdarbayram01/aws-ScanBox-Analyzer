"""
Map Inventory — Security Hub Collector
Resource types: hub, standard, finding-aggregator
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_securityhub_resources(session, region, account_id):
    """Collect all Security Hub resource types in the given region."""
    resources = []
    try:
        client = session.client('securityhub', region_name=region)
    except Exception:
        return resources

    # ── Hub ──────────────────────────────────────────────────────────
    try:
        resp = client.describe_hub()
        hub_arn = resp.get('HubArn', '')
        resources.append(make_resource(
            service='securityhub',
            resource_type='hub',
            resource_id='securityhub',
            arn=hub_arn,
            name='Security Hub',
            region=region,
            details={
                'subscribed_at': resp.get('SubscribedAt', ''),
                'auto_enable_controls': resp.get('AutoEnableControls', False),
                'control_finding_generator': resp.get(
                    'ControlFindingGenerator', ''),
            },
            tags={},
        ))
    except Exception:
        # InvalidAccessException means Security Hub is not enabled
        return resources

    # ── Standards ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_enabled_standards')
        for page in paginator.paginate():
            for std in page.get('StandardsSubscriptions', []):
                std_sub_arn = std.get('StandardsSubscriptionArn', '')
                std_arn = std.get('StandardsArn', '')
                # Derive a readable name from the ARN
                std_name = std_arn.split('/')[-1] if '/' in std_arn else std_arn
                resources.append(make_resource(
                    service='securityhub',
                    resource_type='standard',
                    resource_id=std_sub_arn.split('/')[-1] if '/' in std_sub_arn else std_sub_arn,
                    arn=std_sub_arn,
                    name=std_name,
                    region=region,
                    details={
                        'standards_arn': std_arn,
                        'standards_status': std.get('StandardsStatus', ''),
                        'standards_status_reason': std.get(
                            'StandardsStatusReason', {}).get('StatusReasonCode', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Finding Aggregators ──────────────────────────────────────────
    try:
        resp = client.list_finding_aggregators()
        for agg in resp.get('FindingAggregators', []):
            agg_arn = agg.get('FindingAggregatorArn', '')
            # Fetch details
            try:
                detail = client.get_finding_aggregator(
                    FindingAggregatorArn=agg_arn)
                resources.append(make_resource(
                    service='securityhub',
                    resource_type='finding-aggregator',
                    resource_id=agg_arn.split('/')[-1] if '/' in agg_arn else agg_arn,
                    arn=agg_arn,
                    name='Finding Aggregator',
                    region=region,
                    details={
                        'region_linking_mode': detail.get('RegionLinkingMode', ''),
                        'regions': detail.get('Regions', []),
                    },
                    tags={},
                ))
            except Exception:
                resources.append(make_resource(
                    service='securityhub',
                    resource_type='finding-aggregator',
                    resource_id=agg_arn.split('/')[-1] if '/' in agg_arn else agg_arn,
                    arn=agg_arn,
                    name='Finding Aggregator',
                    region=region,
                    details={},
                    tags={},
                ))
    except Exception:
        pass

    return resources
