"""
Map Inventory — Firewall Manager (FMS) Collector
Resource types: policy, admin-account
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_fms_resources(session, region, account_id):
    """Collect AWS Firewall Manager resources in the given region."""
    resources = []
    try:
        client = session.client('fms', region_name=region)
    except Exception:
        return resources

    # ── Admin Account ────────────────────────────────────────────────
    try:
        resp = client.get_admin_account()
        admin_account = resp.get('AdminAccount', '')
        role_status = resp.get('RoleStatus', '')
        if admin_account:
            arn = f"arn:aws:fms:{region}:{account_id}:admin-account/{admin_account}"
            resources.append(make_resource(
                service='fms',
                resource_type='admin-account',
                resource_id=admin_account,
                arn=arn,
                name=f"FMS Admin: {admin_account}",
                region=region,
                details={
                    'admin_account': admin_account,
                    'role_status': role_status,
                },
                tags={},
            ))
    except Exception:
        pass

    # ── Policies ─────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_policies(**kwargs)
            for policy in resp.get('PolicyList', []):
                policy_id = policy.get('PolicyId', '')
                policy_name = policy.get('PolicyName', policy_id)
                policy_arn = policy.get('PolicyArn', '')
                resource_type = policy.get('ResourceType', '')
                security_service = policy.get('SecurityServiceType', '')

                # Get tags for the policy
                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=policy_arn)
                    tag_list = tag_resp.get('TagList', [])
                    tags = tags_to_dict(tag_list)
                except Exception:
                    pass

                resources.append(make_resource(
                    service='fms',
                    resource_type='policy',
                    resource_id=policy_id,
                    arn=policy_arn,
                    name=policy_name,
                    region=region,
                    details={
                        'resource_type': resource_type,
                        'security_service_type': security_service,
                        'remediation_enabled': policy.get('RemediationEnabled', False),
                        'delete_unused_managed_resources': policy.get('DeleteUnusedFMManagedResources', False),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
