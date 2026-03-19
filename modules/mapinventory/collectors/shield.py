"""
Map Inventory — AWS Shield Collector (GLOBAL)
Resource types: subscription, protection
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_shield_resources(session, region, account_id):
    """Collect AWS Shield subscription and protections (global service)."""
    resources = []
    try:
        client = session.client('shield', region_name='us-east-1')
    except Exception:
        return resources

    # ── Subscription ─────────────────────────────────────────────────
    try:
        resp = client.describe_subscription()
        sub = resp.get('Subscription', {})
        if sub:
            sub_arn = sub.get('SubscriptionArn', '')
            limits = sub.get('SubscriptionLimits', {})
            resources.append(make_resource(
                service='shield',
                resource_type='subscription',
                resource_id='shield-advanced-subscription',
                arn=sub_arn,
                name='Shield Advanced Subscription',
                region='global',
                details={
                    'start_time': str(sub.get('StartTime', '')),
                    'end_time': str(sub.get('EndTime', '')),
                    'time_commitment_in_seconds': sub.get(
                        'TimeCommitmentInSeconds', 0),
                    'auto_renew': sub.get('AutoRenew', ''),
                    'proactive_engagement_status': sub.get(
                        'ProactiveEngagementStatus', ''),
                    'protection_limit': limits.get(
                        'ProtectionLimits', {}).get('Max', ''),
                    'protection_group_limit': limits.get(
                        'ProtectionGroupLimits', {}).get('Max', ''),
                },
                tags={},
            ))
    except Exception:
        # ResourceNotFoundException means no Shield Advanced subscription
        pass

    # ── Protections ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_protections')
        for page in paginator.paginate():
            for prot in page.get('Protections', []):
                prot_id = prot.get('Id', '')
                prot_arn = prot.get('ProtectionArn', '')
                prot_name = prot.get('Name', prot_id)
                resource_arn = prot.get('ResourceArn', '')
                # Fetch tags
                prot_tags = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceARN=prot_arn)
                    prot_tags = tag_resp.get('Tags', [])
                except Exception:
                    pass
                # Determine resource type from ARN
                resource_type_from_arn = ''
                if resource_arn:
                    parts = resource_arn.split(':')
                    if len(parts) >= 6:
                        resource_type_from_arn = parts[2]
                resources.append(make_resource(
                    service='shield',
                    resource_type='protection',
                    resource_id=prot_id,
                    arn=prot_arn,
                    name=prot_name,
                    region='global',
                    details={
                        'resource_arn': resource_arn,
                        'protected_resource_type': resource_type_from_arn,
                        'application_layer_automatic_response': prot.get(
                            'ApplicationLayerAutomaticResponseConfiguration', {}),
                    },
                    tags=tags_to_dict(prot_tags),
                ))
    except Exception:
        pass

    return resources
