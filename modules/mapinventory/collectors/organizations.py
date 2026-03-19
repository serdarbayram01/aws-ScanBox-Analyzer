"""
Map Inventory — AWS Organizations Collector (GLOBAL — us-east-1 only)
Resource types: organization, root, organizational-unit, account,
                policy, delegated-administrator
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_organizations_resources(session, region, account_id):
    """Collect AWS Organizations resources. Must be called with region='us-east-1'."""
    resources = []
    try:
        client = session.client('organizations', region_name='us-east-1')
    except Exception:
        return resources

    # ── Organization ──────────────────────────────────────────────────
    org_id = ''
    try:
        resp = client.describe_organization()
        org = resp.get('Organization', {})
        org_id = org.get('Id', '')
        org_arn = org.get('Arn', '')
        master_id = org.get('MasterAccountId', '')
        resources.append(make_resource(
            service='organizations',
            resource_type='organization',
            resource_id=org_id,
            arn=org_arn,
            name=org_id,
            region='global',
            details={
                'master_account_id': master_id,
                'master_account_email': org.get('MasterAccountEmail', ''),
                'feature_set': org.get('FeatureSet', ''),
                'available_policy_types': [
                    pt.get('Type', '') for pt in org.get('AvailablePolicyTypes', [])
                ],
            },
            tags={},
        ))
    except Exception:
        # Not in an organization or no permission
        return resources

    # ── Roots ─────────────────────────────────────────────────────────
    root_ids = []
    try:
        resp = client.list_roots()
        for root in resp.get('Roots', []):
            root_id = root.get('Id', '')
            root_ids.append(root_id)
            root_arn = root.get('Arn', '')
            root_name = root.get('Name', root_id)

            tags = {}
            try:
                tag_resp = client.list_tags_for_resource(ResourceId=root_id)
                raw = tag_resp.get('Tags', [])
                tags = tags_to_dict(raw)
            except Exception:
                pass

            resources.append(make_resource(
                service='organizations',
                resource_type='root',
                resource_id=root_id,
                arn=root_arn,
                name=root_name,
                region='global',
                details={
                    'policy_types': [
                        {'type': pt.get('Type', ''), 'status': pt.get('Status', '')}
                        for pt in root.get('PolicyTypes', [])
                    ],
                },
                tags=tags,
            ))
    except Exception:
        pass

    # ── Organizational Units (recursive) ──────────────────────────────
    def _list_ous(parent_id):
        """Recursively list all OUs under a parent."""
        try:
            paginator = client.get_paginator('list_organizational_units_for_parent')
            for page in paginator.paginate(ParentId=parent_id):
                for ou in page.get('OrganizationalUnits', []):
                    ou_id = ou.get('Id', '')
                    ou_arn = ou.get('Arn', '')
                    ou_name = ou.get('Name', ou_id)

                    tags = {}
                    try:
                        tag_resp = client.list_tags_for_resource(ResourceId=ou_id)
                        tags = tags_to_dict(tag_resp.get('Tags', []))
                    except Exception:
                        pass

                    resources.append(make_resource(
                        service='organizations',
                        resource_type='organizational-unit',
                        resource_id=ou_id,
                        arn=ou_arn,
                        name=ou_name,
                        region='global',
                        details={
                            'parent_id': parent_id,
                        },
                        tags=tags,
                    ))
                    # Recurse into child OUs
                    _list_ous(ou_id)
        except Exception:
            pass

    for rid in root_ids:
        _list_ous(rid)

    # ── Accounts ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_accounts')
        for page in paginator.paginate():
            for acct in page.get('Accounts', []):
                acct_id = acct.get('Id', '')
                acct_name = acct.get('Name', acct_id)
                acct_arn = acct.get('Arn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceId=acct_id)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='organizations',
                    resource_type='account',
                    resource_id=acct_id,
                    arn=acct_arn,
                    name=acct_name,
                    region='global',
                    details={
                        'email': acct.get('Email', ''),
                        'status': acct.get('Status', ''),
                        'joined_method': acct.get('JoinedMethod', ''),
                        'joined_timestamp': str(acct.get('JoinedTimestamp', '')),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Policies ──────────────────────────────────────────────────────
    policy_types = [
        'SERVICE_CONTROL_POLICY',
        'TAG_POLICY',
        'BACKUP_POLICY',
        'AISERVICES_OPT_OUT_POLICY',
    ]
    for policy_type in policy_types:
        try:
            paginator = client.get_paginator('list_policies')
            for page in paginator.paginate(Filter=policy_type):
                for pol in page.get('Policies', []):
                    pol_id = pol.get('Id', '')
                    pol_name = pol.get('Name', pol_id)
                    pol_arn = pol.get('Arn', '')
                    is_default = pol.get('AwsManaged', False)

                    resources.append(make_resource(
                        service='organizations',
                        resource_type='policy',
                        resource_id=pol_id,
                        arn=pol_arn,
                        name=pol_name,
                        region='global',
                        details={
                            'type': pol.get('Type', ''),
                            'description': pol.get('Description', ''),
                            'aws_managed': pol.get('AwsManaged', False),
                        },
                        tags={},
                        is_default=is_default,
                    ))
        except Exception:
            pass

    # ── Delegated Administrators ──────────────────────────────────────
    try:
        paginator = client.get_paginator('list_delegated_administrators')
        for page in paginator.paginate():
            for da in page.get('DelegatedAdministrators', []):
                da_id = da.get('Id', '')
                da_name = da.get('Name', da_id)
                da_arn = da.get('Arn', '')

                resources.append(make_resource(
                    service='organizations',
                    resource_type='delegated-administrator',
                    resource_id=da_id,
                    arn=da_arn,
                    name=da_name,
                    region='global',
                    details={
                        'email': da.get('Email', ''),
                        'status': da.get('Status', ''),
                        'joined_method': da.get('JoinedMethod', ''),
                        'joined_timestamp': str(da.get('JoinedTimestamp', '')),
                        'delegation_enabled_date': str(da.get('DelegationEnabledDate', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
