"""
Map Inventory — Amazon CloudWatch Synthetics Collector
Resource types: canary
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_synthetics_resources(session, region, account_id):
    """Collect CloudWatch Synthetics canaries in the given region."""
    resources = []
    try:
        client = session.client('synthetics', region_name=region)
    except Exception:
        return resources

    # ── Canaries ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_canaries')
        for page in paginator.paginate():
            for c in page.get('Canaries', []):
                name = c.get('Name', '')
                arn = c.get('Id', '')  # Id field contains the ARN-like identifier
                tags_dict = c.get('Tags', {})
                status = c.get('Status', {})
                schedule = c.get('Schedule', {})
                resources.append(make_resource(
                    service='synthetics',
                    resource_type='canary',
                    resource_id=name,
                    arn=f'arn:aws:synthetics:{region}:{account_id}:canary:{name}',
                    name=name,
                    region=region,
                    details={
                        'status': status.get('State', ''),
                        'status_reason': status.get('StateReason', ''),
                        'schedule_expression': schedule.get('Expression', ''),
                        'schedule_duration': schedule.get('DurationInSeconds', 0),
                        'runtime_version': c.get('RuntimeVersion', ''),
                        'engine_arn': c.get('EngineArn', ''),
                        'artifact_s3_location': c.get('ArtifactS3Location', ''),
                        'execution_role_arn': c.get('ExecutionRoleArn', ''),
                        'success_retention_period': c.get('SuccessRetentionPeriodInDays', 0),
                        'failure_retention_period': c.get('FailureRetentionPeriodInDays', 0),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
