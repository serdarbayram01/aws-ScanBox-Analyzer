"""
Map Inventory — Lake Formation Collector
Resource types: resource, data-lake-settings
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_lakeformation_resources(session, region, account_id):
    """Collect Lake Formation resources in the given region."""
    resources = []
    try:
        client = session.client('lakeformation', region_name=region)
    except Exception:
        return resources

    # ── Data Lake Settings ──────────────────────────────────────────
    try:
        settings = client.get_data_lake_settings()
        s = settings.get('DataLakeSettings', {})
        resources.append(make_resource(
            service='lakeformation',
            resource_type='data-lake-settings',
            resource_id=f'datalake-settings-{region}',
            arn=f'arn:aws:lakeformation:{region}:{account_id}:data-lake-settings',
            name=f'Data Lake Settings ({region})',
            region=region,
            details={
                'admins': [a.get('DataLakePrincipalIdentifier', '') for a in s.get('DataLakeAdmins', [])],
                'create_database_default_permissions': str(s.get('CreateDatabaseDefaultPermissions', [])),
                'create_table_default_permissions': str(s.get('CreateTableDefaultPermissions', [])),
            },
        ))
    except Exception:
        pass

    # ── Registered Resources ────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_resources')
        for page in paginator.paginate():
            for res in page.get('ResourceInfoList', []):
                arn = res.get('ResourceArn', '')
                resources.append(make_resource(
                    service='lakeformation',
                    resource_type='resource',
                    resource_id=arn,
                    arn=arn,
                    name=arn.split(':')[-1] if ':' in arn else arn,
                    region=region,
                    details={
                        'role_arn': res.get('RoleArn', ''),
                        'last_modified': str(res.get('LastModified', '')),
                    },
                ))
    except Exception:
        pass

    return resources
