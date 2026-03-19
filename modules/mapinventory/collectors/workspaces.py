"""
Map Inventory — Amazon WorkSpaces Collector
Resource types: workspace, directory
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_workspaces_resources(session, region, account_id):
    """Collect Amazon WorkSpaces resources in the given region."""
    resources = []
    try:
        client = session.client('workspaces', region_name=region)
    except Exception:
        return resources

    # ── Directories ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_workspace_directories')
        for page in paginator.paginate():
            for d in page.get('Directories', []):
                did = d.get('DirectoryId', '')
                resources.append(make_resource(
                    service='workspaces',
                    resource_type='directory',
                    resource_id=did,
                    arn=f'arn:aws:workspaces:{region}:{account_id}:directory/{did}',
                    name=d.get('DirectoryName', did),
                    region=region,
                    details={
                        'directory_type': d.get('DirectoryType', ''),
                        'state': d.get('State', ''),
                        'alias': d.get('Alias', ''),
                        'registration_code': d.get('RegistrationCode', ''),
                        'tenancy': d.get('Tenancy', ''),
                    },
                ))
    except Exception:
        pass

    # ── WorkSpaces ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_workspaces')
        for page in paginator.paginate():
            for ws in page.get('Workspaces', []):
                wid = ws.get('WorkspaceId', '')
                tags_dict = {}
                try:
                    tag_resp = client.describe_tags(ResourceId=wid)
                    tags_dict = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass
                name = get_tag_value(tag_resp.get('TagList', []) if tags_dict else [], 'Name') or ws.get('ComputerName', wid)
                resources.append(make_resource(
                    service='workspaces',
                    resource_type='workspace',
                    resource_id=wid,
                    arn=f'arn:aws:workspaces:{region}:{account_id}:workspace/{wid}',
                    name=name,
                    region=region,
                    details={
                        'directory_id': ws.get('DirectoryId', ''),
                        'user_name': ws.get('UserName', ''),
                        'state': ws.get('State', ''),
                        'bundle_id': ws.get('BundleId', ''),
                        'computer_name': ws.get('ComputerName', ''),
                        'running_mode': ws.get('WorkspaceProperties', {}).get('RunningMode', ''),
                        'compute_type': ws.get('WorkspaceProperties', {}).get('ComputeTypeName', ''),
                        'root_volume_size': ws.get('WorkspaceProperties', {}).get('RootVolumeSizeGib', 0),
                        'user_volume_size': ws.get('WorkspaceProperties', {}).get('UserVolumeSizeGib', 0),
                        'subnet_id': ws.get('SubnetId', ''),
                        'ip_address': ws.get('IpAddress', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
