"""
Map Inventory — CodeDeploy Collector
Resource types: application, deployment-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_codedeploy_resources(session, region, account_id):
    """Collect CodeDeploy resources in the given region."""
    resources = []
    try:
        client = session.client('codedeploy', region_name=region)
    except Exception:
        return resources

    # ── Applications ────────────────────────────────────────────────
    app_names = []
    try:
        paginator = client.get_paginator('list_applications')
        for page in paginator.paginate():
            app_names.extend(page.get('applications', []))
    except Exception:
        pass

    for app_name in app_names:
        try:
            resp = client.get_application(applicationName=app_name)
            app = resp.get('application', {})
            app_id = app.get('applicationId', app_name)
            arn = f'arn:aws:codedeploy:{region}:{account_id}:application:{app_name}'
            resources.append(make_resource(
                service='codedeploy',
                resource_type='application',
                resource_id=app_id,
                arn=arn,
                name=app_name,
                region=region,
                details={
                    'compute_platform': app.get('computePlatform', ''),
                    'create_time': str(app.get('createTime', '')),
                    'linked_to_github': app.get('linkedToGitHub', False),
                },
            ))
        except Exception:
            pass

        # ── Deployment Groups per Application ───────────────────────
        try:
            dg_paginator = client.get_paginator('list_deployment_groups')
            for dg_page in dg_paginator.paginate(applicationName=app_name):
                for dg_name in dg_page.get('deploymentGroups', []):
                    try:
                        dg_resp = client.get_deployment_group(
                            applicationName=app_name,
                            deploymentGroupName=dg_name
                        )
                        dg = dg_resp.get('deploymentGroupInfo', {})
                        dg_id = dg.get('deploymentGroupId', dg_name)
                        resources.append(make_resource(
                            service='codedeploy',
                            resource_type='deployment-group',
                            resource_id=dg_id,
                            arn=f'arn:aws:codedeploy:{region}:{account_id}:deploymentgroup:{app_name}/{dg_name}',
                            name=dg_name,
                            region=region,
                            details={
                                'application_name': app_name,
                                'compute_platform': dg.get('computePlatform', ''),
                                'deployment_config_name': dg.get('deploymentConfigName', ''),
                                'service_role_arn': dg.get('serviceRoleArn', ''),
                            },
                        ))
                    except Exception:
                        pass
        except Exception:
            pass

    return resources
