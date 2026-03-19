"""
Map Inventory — AWS Compute Optimizer Collector
Resource types: recommendation (EC2 right-sizing)
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_computeoptimizer_resources(session, region, account_id):
    """Collect Compute Optimizer EC2 right-sizing recommendations."""
    resources = []
    try:
        client = session.client('compute-optimizer', region_name=region)
    except Exception:
        return resources

    # ── EC2 Instance Recommendations ────────────────────────────────
    try:
        resp = client.get_ec2_instance_recommendations(
            accountIds=[account_id],
            maxResults=200
        )
        for rec in resp.get('instanceRecommendations', []):
            inst_arn = rec.get('instanceArn', '')
            inst_name = rec.get('instanceName', '')
            finding = rec.get('finding', '')
            current_type = rec.get('currentInstanceType', '')
            options = rec.get('recommendationOptions', [])
            top_option = options[0] if options else {}
            resources.append(make_resource(
                service='computeoptimizer',
                resource_type='recommendation',
                resource_id=inst_arn.split('/')[-1] if '/' in inst_arn else inst_arn,
                arn=inst_arn,
                name=inst_name or inst_arn,
                region=region,
                details={
                    'finding': finding,
                    'finding_reason_codes': rec.get('findingReasonCodes', []),
                    'current_instance_type': current_type,
                    'recommended_instance_type': top_option.get('instanceType', ''),
                    'recommended_instance_gpu_info': str(top_option.get('instanceGpuInfo', {})),
                    'migration_effort': top_option.get('migrationEffort', ''),
                    'performance_risk': top_option.get('performanceRisk', 0),
                    'rank': top_option.get('rank', 0),
                    'look_back_period': rec.get('lookBackPeriodInDays', 0),
                    'last_refresh_timestamp': str(rec.get('lastRefreshTimestamp', '')),
                },
            ))
    except Exception:
        pass

    return resources
