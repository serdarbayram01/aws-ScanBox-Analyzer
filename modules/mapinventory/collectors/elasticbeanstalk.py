"""
Map Inventory — Elastic Beanstalk Collector
Resource types: application, application-version, environment
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_elasticbeanstalk_resources(session, region, account_id):
    """Collect Elastic Beanstalk resources in the given region."""
    resources = []
    try:
        client = session.client('elasticbeanstalk', region_name=region)
    except Exception:
        return resources

    # ── Applications ─────────────────────────────────────────────────
    try:
        resp = client.describe_applications()
        for app in resp.get('Applications', []):
            app_name = app.get('ApplicationName', '')
            app_arn = app.get('ApplicationArn', '')
            created = str(app.get('DateCreated', ''))
            updated = str(app.get('DateUpdated', ''))

            # Get tags
            tags = {}
            try:
                tag_resp = client.list_tags_for_resource(ResourceArn=app_arn)
                tag_list = tag_resp.get('ResourceTags', [])
                tags = tags_to_dict(tag_list)
            except Exception:
                pass

            resources.append(make_resource(
                service='elasticbeanstalk',
                resource_type='application',
                resource_id=app_name,
                arn=app_arn,
                name=app_name,
                region=region,
                details={
                    'description': app.get('Description', ''),
                    'date_created': created,
                    'date_updated': updated,
                    'versions': app.get('Versions', []),
                    'configured_environments': app.get('ConfigurationTemplates', []),
                },
                tags=tags,
            ))
    except Exception:
        pass

    # ── Application Versions ─────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_application_versions')
        for page in paginator.paginate():
            for ver in page.get('ApplicationVersions', []):
                ver_label = ver.get('VersionLabel', '')
                app_name = ver.get('ApplicationName', '')
                ver_arn = ver.get('ApplicationVersionArn', '')
                created = str(ver.get('DateCreated', ''))

                resources.append(make_resource(
                    service='elasticbeanstalk',
                    resource_type='application-version',
                    resource_id=f"{app_name}/{ver_label}",
                    arn=ver_arn,
                    name=ver_label,
                    region=region,
                    details={
                        'application_name': app_name,
                        'description': ver.get('Description', ''),
                        'status': ver.get('Status', ''),
                        'date_created': created,
                        'date_updated': str(ver.get('DateUpdated', '')),
                        'source_bundle': ver.get('SourceBundle', {}),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Environments ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_environments')
        for page in paginator.paginate(IncludeDeleted=False):
            for env in page.get('Environments', []):
                env_id = env.get('EnvironmentId', '')
                env_name = env.get('EnvironmentName', env_id)
                env_arn = env.get('EnvironmentArn', '')
                created = str(env.get('DateCreated', ''))

                # Get tags
                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=env_arn)
                    tag_list = tag_resp.get('ResourceTags', [])
                    tags = tags_to_dict(tag_list)
                except Exception:
                    pass

                resources.append(make_resource(
                    service='elasticbeanstalk',
                    resource_type='environment',
                    resource_id=env_id,
                    arn=env_arn,
                    name=env_name,
                    region=region,
                    details={
                        'application_name': env.get('ApplicationName', ''),
                        'version_label': env.get('VersionLabel', ''),
                        'solution_stack': env.get('SolutionStackName', ''),
                        'platform_arn': env.get('PlatformArn', ''),
                        'status': env.get('Status', ''),
                        'health': env.get('Health', ''),
                        'health_status': env.get('HealthStatus', ''),
                        'cname': env.get('CNAME', ''),
                        'endpoint_url': env.get('EndpointURL', ''),
                        'tier': env.get('Tier', {}),
                        'date_created': created,
                        'date_updated': str(env.get('DateUpdated', '')),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
