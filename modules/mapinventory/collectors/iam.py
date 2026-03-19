"""
Map Inventory — IAM Collector (GLOBAL service)
Resource types: user, group, role, policy, instance-profile,
                saml-provider, oidc-provider
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_iam_resources(session, region, account_id):
    """Collect all IAM resources. IAM is global; region parameter is ignored."""
    resources = []
    try:
        iam = session.client('iam')
    except Exception:
        return resources

    # ── Users ──────────────────────────────────────────────────────────
    try:
        paginator = iam.get_paginator('list_users')
        for page in paginator.paginate():
            for user in page.get('Users', []):
                user_name = user['UserName']
                user_arn = user['Arn']

                # MFA devices
                mfa_enabled = False
                try:
                    mfa_resp = iam.list_mfa_devices(UserName=user_name)
                    mfa_enabled = len(mfa_resp.get('MFADevices', [])) > 0
                except Exception:
                    pass

                # Access keys
                access_keys_count = 0
                try:
                    ak_resp = iam.list_access_keys(UserName=user_name)
                    access_keys_count = len(ak_resp.get('AccessKeyMetadata', []))
                except Exception:
                    pass

                # Attached policies
                attached_policies = []
                try:
                    ap_resp = iam.list_attached_user_policies(UserName=user_name)
                    attached_policies = [p['PolicyName'] for p in ap_resp.get('AttachedPolicies', [])]
                except Exception:
                    pass

                # Groups
                groups = []
                try:
                    g_resp = iam.list_groups_for_user(UserName=user_name)
                    groups = [g['GroupName'] for g in g_resp.get('Groups', [])]
                except Exception:
                    pass

                # Tags
                tags = {}
                try:
                    t_resp = iam.list_user_tags(UserName=user_name)
                    tags = tags_to_dict(t_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='iam',
                    resource_type='user',
                    resource_id=user_name,
                    arn=user_arn,
                    name=user_name,
                    region='global',
                    details={
                        'path': user.get('Path', '/'),
                        'create_date': str(user.get('CreateDate', '')),
                        'password_last_used': str(user.get('PasswordLastUsed', '')),
                        'mfa_enabled': mfa_enabled,
                        'access_keys_count': access_keys_count,
                        'attached_policies': attached_policies,
                        'groups': groups,
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Groups ─────────────────────────────────────────────────────────
    try:
        paginator = iam.get_paginator('list_groups')
        for page in paginator.paginate():
            for group in page.get('Groups', []):
                group_name = group['GroupName']
                group_arn = group['Arn']

                attached_policies = []
                try:
                    ap_resp = iam.list_attached_group_policies(GroupName=group_name)
                    attached_policies = [p['PolicyName'] for p in ap_resp.get('AttachedPolicies', [])]
                except Exception:
                    pass

                resources.append(make_resource(
                    service='iam',
                    resource_type='group',
                    resource_id=group_name,
                    arn=group_arn,
                    name=group_name,
                    region='global',
                    details={
                        'path': group.get('Path', '/'),
                        'create_date': str(group.get('CreateDate', '')),
                        'attached_policies': attached_policies,
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Roles ──────────────────────────────────────────────────────────
    try:
        paginator = iam.get_paginator('list_roles')
        for page in paginator.paginate():
            for role in page.get('Roles', []):
                role_name = role['RoleName']
                role_arn = role['Arn']

                # Tags
                tags = {}
                try:
                    t_resp = iam.list_role_tags(RoleName=role_name)
                    tags = tags_to_dict(t_resp.get('Tags', []))
                except Exception:
                    pass

                # Attached policies
                attached_policies = []
                try:
                    ap_resp = iam.list_attached_role_policies(RoleName=role_name)
                    attached_policies = [p['PolicyName'] for p in ap_resp.get('AttachedPolicies', [])]
                except Exception:
                    pass

                # Trust policy
                trust_policy = role.get('AssumeRolePolicyDocument', {})

                resources.append(make_resource(
                    service='iam',
                    resource_type='role',
                    resource_id=role_name,
                    arn=role_arn,
                    name=role_name,
                    region='global',
                    details={
                        'path': role.get('Path', '/'),
                        'create_date': str(role.get('CreateDate', '')),
                        'max_session_duration': role.get('MaxSessionDuration', 3600),
                        'description': role.get('Description', ''),
                        'attached_policies': attached_policies,
                        'trust_policy': trust_policy,
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Policies (customer-managed only) ───────────────────────────────
    try:
        paginator = iam.get_paginator('list_policies')
        for page in paginator.paginate(Scope='Local'):
            for policy in page.get('Policies', []):
                policy_name = policy['PolicyName']
                policy_arn = policy['Arn']

                tags = {}
                try:
                    t_resp = iam.list_policy_tags(PolicyArn=policy_arn)
                    tags = tags_to_dict(t_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='iam',
                    resource_type='policy',
                    resource_id=policy_name,
                    arn=policy_arn,
                    name=policy_name,
                    region='global',
                    details={
                        'path': policy.get('Path', '/'),
                        'create_date': str(policy.get('CreateDate', '')),
                        'update_date': str(policy.get('UpdateDate', '')),
                        'attachment_count': policy.get('AttachmentCount', 0),
                        'default_version': policy.get('DefaultVersionId', ''),
                        'is_attachable': policy.get('IsAttachable', True),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Instance Profiles ──────────────────────────────────────────────
    try:
        paginator = iam.get_paginator('list_instance_profiles')
        for page in paginator.paginate():
            for ip in page.get('InstanceProfiles', []):
                ip_name = ip['InstanceProfileName']
                ip_arn = ip['Arn']

                tags = {}
                try:
                    t_resp = iam.list_instance_profile_tags(InstanceProfileName=ip_name)
                    tags = tags_to_dict(t_resp.get('Tags', []))
                except Exception:
                    pass

                roles = [r['RoleName'] for r in ip.get('Roles', [])]

                resources.append(make_resource(
                    service='iam',
                    resource_type='instance-profile',
                    resource_id=ip_name,
                    arn=ip_arn,
                    name=ip_name,
                    region='global',
                    details={
                        'path': ip.get('Path', '/'),
                        'create_date': str(ip.get('CreateDate', '')),
                        'roles': roles,
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── SAML Providers ─────────────────────────────────────────────────
    try:
        saml_resp = iam.list_saml_providers()
        for provider in saml_resp.get('SAMLProviderList', []):
            provider_arn = provider['Arn']
            # Extract name from ARN: arn:aws:iam::123456:saml-provider/MyProvider
            provider_name = provider_arn.rsplit('/', 1)[-1]

            tags = {}
            try:
                t_resp = iam.list_saml_provider_tags(SAMLProviderArn=provider_arn)
                tags = tags_to_dict(t_resp.get('Tags', []))
            except Exception:
                pass

            resources.append(make_resource(
                service='iam',
                resource_type='saml-provider',
                resource_id=provider_name,
                arn=provider_arn,
                name=provider_name,
                region='global',
                details={
                    'valid_until': str(provider.get('ValidUntil', '')),
                    'create_date': str(provider.get('CreateDate', '')),
                },
                tags=tags,
            ))
    except Exception:
        pass

    # ── OIDC Providers ─────────────────────────────────────────────────
    try:
        oidc_resp = iam.list_open_id_connect_providers()
        for provider in oidc_resp.get('OpenIDConnectProviderList', []):
            provider_arn = provider['Arn']
            provider_name = provider_arn.rsplit('/', 1)[-1]

            details = {
                'url': '',
                'client_ids': [],
                'thumbprints': [],
                'create_date': '',
            }
            tags = {}
            try:
                detail_resp = iam.get_open_id_connect_provider(
                    OpenIDConnectProviderArn=provider_arn
                )
                details['url'] = detail_resp.get('Url', '')
                details['client_ids'] = detail_resp.get('ClientIDList', [])
                details['thumbprints'] = detail_resp.get('ThumbprintList', [])
                details['create_date'] = str(detail_resp.get('CreateDate', ''))
                tags = tags_to_dict(detail_resp.get('Tags', []))
            except Exception:
                pass

            resources.append(make_resource(
                service='iam',
                resource_type='oidc-provider',
                resource_id=provider_name,
                arn=provider_arn,
                name=provider_name,
                region='global',
                details=details,
                tags=tags,
            ))
    except Exception:
        pass

    return resources
