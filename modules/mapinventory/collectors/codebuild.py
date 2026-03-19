"""
Map Inventory — CodeBuild Collector
Resource types: project, report-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_codebuild_resources(session, region, account_id):
    """Collect CodeBuild resources for a given region."""
    resources = []
    try:
        client = session.client('codebuild', region_name=region)
    except Exception:
        return resources

    # ── Projects ──────────────────────────────────────────────────────
    try:
        project_names = []
        paginator = client.get_paginator('list_projects')
        for page in paginator.paginate():
            project_names.extend(page.get('projects', []))

        # batch_get_projects accepts up to 100
        for i in range(0, len(project_names), 100):
            batch = project_names[i:i + 100]
            try:
                resp = client.batch_get_projects(names=batch)
                for proj in resp.get('projects', []):
                    proj_name = proj.get('name', '')
                    proj_arn = proj.get('arn', '')
                    tags_list = proj.get('tags', [])
                    source = proj.get('source', {})
                    env = proj.get('environment', {})
                    resources.append(make_resource(
                        service='codebuild',
                        resource_type='project',
                        resource_id=proj_name,
                        arn=proj_arn,
                        name=proj_name,
                        region=region,
                        details={
                            'source_type': source.get('type', ''),
                            'source_location': source.get('location', ''),
                            'environment_type': env.get('type', ''),
                            'compute_type': env.get('computeType', ''),
                            'image': env.get('image', ''),
                            'privileged_mode': env.get('privilegedMode', False),
                            'concurrent_build_limit': proj.get('concurrentBuildLimit', 0),
                            'build_timeout': proj.get('timeoutInMinutes', 0),
                            'encryption_key': proj.get('encryptionKey', ''),
                            'last_modified': str(proj.get('lastModified', '')),
                            'created': str(proj.get('created', '')),
                        },
                        tags=tags_to_dict(tags_list),
                    ))
            except Exception:
                pass
    except Exception:
        pass

    # ── Report Groups ─────────────────────────────────────────────────
    try:
        rg_arns = []
        paginator = client.get_paginator('list_report_groups')
        for page in paginator.paginate():
            rg_arns.extend(page.get('reportGroups', []))

        # batch_get_report_groups accepts up to 100
        for i in range(0, len(rg_arns), 100):
            batch = rg_arns[i:i + 100]
            try:
                resp = client.batch_get_report_groups(reportGroupArns=batch)
                for rg in resp.get('reportGroups', []):
                    rg_arn = rg.get('arn', '')
                    rg_name = rg.get('name', '')
                    tags_list = rg.get('tags', [])
                    export_config = rg.get('exportConfig', {})
                    resources.append(make_resource(
                        service='codebuild',
                        resource_type='report-group',
                        resource_id=rg_name,
                        arn=rg_arn,
                        name=rg_name,
                        region=region,
                        details={
                            'type': rg.get('type', ''),
                            'status': rg.get('status', ''),
                            'export_type': export_config.get('exportConfigType', 'NO_EXPORT'),
                            'created': str(rg.get('created', '')),
                            'last_modified': str(rg.get('lastModified', '')),
                        },
                        tags=tags_to_dict(tags_list),
                    ))
            except Exception:
                pass
    except Exception:
        pass

    return resources
