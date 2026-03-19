"""
Map Inventory — AWS Amplify Collector
Resource types: app, branch
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_amplify_resources(session, region, account_id):
    """Collect AWS Amplify resources in the given region."""
    resources = []
    try:
        client = session.client('amplify', region_name=region)
    except Exception:
        return resources

    # ── Apps ─────────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_apps(**kwargs)
            for app in resp.get('apps', []):
                app_id = app.get('appId', '')
                app_name = app.get('name', app_id)
                app_arn = app.get('appArn', '')
                created = str(app.get('createTime', ''))

                tags = app.get('tags', {})

                resources.append(make_resource(
                    service='amplify',
                    resource_type='app',
                    resource_id=app_id,
                    arn=app_arn,
                    name=app_name,
                    region=region,
                    details={
                        'description': app.get('description', ''),
                        'repository': app.get('repository', ''),
                        'platform': app.get('platform', ''),
                        'framework': app.get('framework', ''),
                        'default_domain': app.get('defaultDomain', ''),
                        'create_time': created,
                        'update_time': str(app.get('updateTime', '')),
                        'iam_service_role_arn': app.get('iamServiceRoleArn', ''),
                        'environment_variables': list(app.get('environmentVariables', {}).keys()),
                    },
                    tags=tags,
                ))

                # ── Branches per App ─────────────────────────────────
                try:
                    br_next = None
                    while True:
                        br_kwargs = {'appId': app_id}
                        if br_next:
                            br_kwargs['nextToken'] = br_next
                        br_resp = client.list_branches(**br_kwargs)
                        for branch in br_resp.get('branches', []):
                            br_name = branch.get('branchName', '')
                            br_arn = branch.get('branchArn', '')
                            br_created = str(branch.get('createTime', ''))

                            br_tags = branch.get('tags', {})

                            resources.append(make_resource(
                                service='amplify',
                                resource_type='branch',
                                resource_id=f"{app_id}/{br_name}",
                                arn=br_arn,
                                name=br_name,
                                region=region,
                                details={
                                    'app_id': app_id,
                                    'app_name': app_name,
                                    'display_name': branch.get('displayName', ''),
                                    'stage': branch.get('stage', ''),
                                    'framework': branch.get('framework', ''),
                                    'active_job_id': branch.get('activeJobId', ''),
                                    'total_number_of_jobs': branch.get('totalNumberOfJobs', ''),
                                    'enable_auto_build': branch.get('enableAutoBuild', False),
                                    'create_time': br_created,
                                    'update_time': str(branch.get('updateTime', '')),
                                    'ttl': branch.get('ttl', ''),
                                },
                                tags=br_tags,
                            ))
                        br_next = br_resp.get('nextToken')
                        if not br_next:
                            break
                except Exception:
                    pass

            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
