"""
Map Inventory — AWS SSO (IAM Identity Center) Collector — GLOBAL
Resource types: instance, permission-set
Uses sso-admin client.
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_sso_resources(session, region, account_id):
    """Collect IAM Identity Center (SSO) resources. Uses sso-admin client."""
    resources = []
    try:
        client = session.client('sso-admin', region_name=region)
    except Exception:
        return resources

    # ── Instances ───────────────────────────────────────────────────
    instance_arns = []
    try:
        paginator = client.get_paginator('list_instances')
        for page in paginator.paginate():
            for inst in page.get('Instances', []):
                inst_arn = inst.get('InstanceArn', '')
                instance_arns.append(inst_arn)
                resources.append(make_resource(
                    service='sso',
                    resource_type='instance',
                    resource_id=inst_arn.split('/')[-1] if '/' in inst_arn else inst_arn,
                    arn=inst_arn,
                    name=inst.get('Name', '') or inst.get('IdentityStoreId', inst_arn),
                    region='global',
                    details={
                        'identity_store_id': inst.get('IdentityStoreId', ''),
                        'owner_account_id': inst.get('OwnerAccountId', ''),
                        'status': inst.get('Status', ''),
                        'created_date': str(inst.get('CreatedDate', '')),
                    },
                ))
    except Exception:
        pass

    # ── Permission Sets (per instance) ──────────────────────────────
    for inst_arn in instance_arns:
        try:
            paginator = client.get_paginator('list_permission_sets')
            for page in paginator.paginate(InstanceArn=inst_arn):
                for ps_arn in page.get('PermissionSets', []):
                    details = {}
                    name = ps_arn.split('/')[-1] if '/' in ps_arn else ps_arn
                    try:
                        desc = client.describe_permission_set(
                            InstanceArn=inst_arn,
                            PermissionSetArn=ps_arn
                        )
                        ps = desc.get('PermissionSet', {})
                        name = ps.get('Name', name)
                        details = {
                            'description': ps.get('Description', ''),
                            'session_duration': ps.get('SessionDuration', ''),
                            'relay_state': ps.get('RelayState', ''),
                            'created_date': str(ps.get('CreatedDate', '')),
                        }
                    except Exception:
                        pass
                    tags_dict = {}
                    try:
                        tag_resp = client.list_tags_for_resource(
                            InstanceArn=inst_arn,
                            ResourceArn=ps_arn
                        )
                        tags_dict = tags_to_dict(tag_resp.get('Tags', []))
                    except Exception:
                        pass
                    resources.append(make_resource(
                        service='sso',
                        resource_type='permission-set',
                        resource_id=ps_arn.split('/')[-1] if '/' in ps_arn else ps_arn,
                        arn=ps_arn,
                        name=name,
                        region='global',
                        details=details,
                        tags=tags_dict,
                    ))
        except Exception:
            pass

    return resources
