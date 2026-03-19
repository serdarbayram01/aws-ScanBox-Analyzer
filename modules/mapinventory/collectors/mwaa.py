"""
Map Inventory — Amazon MWAA (Managed Workflows for Apache Airflow) Collector
Resource types: environment
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_mwaa_resources(session, region, account_id):
    """Collect MWAA environments in the given region."""
    resources = []
    try:
        client = session.client('mwaa', region_name=region)
    except Exception:
        return resources

    # ── Environments ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_environments')
        for page in paginator.paginate():
            for name in page.get('Environments', []):
                details = {}
                tags_dict = {}
                arn = f'arn:aws:airflow:{region}:{account_id}:environment/{name}'
                try:
                    resp = client.get_environment(Name=name)
                    env = resp.get('Environment', {})
                    arn = env.get('Arn', arn)
                    tags_dict = env.get('Tags', {})
                    details = {
                        'status': env.get('Status', ''),
                        'airflow_version': env.get('AirflowVersion', ''),
                        'environment_class': env.get('EnvironmentClass', ''),
                        'max_workers': env.get('MaxWorkers', 0),
                        'min_workers': env.get('MinWorkers', 0),
                        'schedulers': env.get('Schedulers', 0),
                        'webserver_url': env.get('WebserverUrl', ''),
                        'source_bucket_arn': env.get('SourceBucketArn', ''),
                        'dag_s3_path': env.get('DagS3Path', ''),
                        'execution_role_arn': env.get('ExecutionRoleArn', ''),
                        'created_at': str(env.get('CreatedAt', '')),
                        'kms_key': env.get('KmsKey', ''),
                        'weekly_maintenance_window_start': env.get('WeeklyMaintenanceWindowStart', ''),
                    }
                except Exception:
                    pass
                resources.append(make_resource(
                    service='mwaa',
                    resource_type='environment',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details=details,
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
