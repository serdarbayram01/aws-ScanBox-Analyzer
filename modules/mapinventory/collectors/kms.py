"""
Map Inventory — KMS Collector
Collects: key (customer-managed only), alias (non-aws/ only)
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_kms_resources(session, region, account_id):
    """Collect KMS resources for a given region."""
    resources = []
    try:
        client = session.client('kms', region_name=region)
    except Exception:
        return resources

    # --- Customer-Managed Keys ---
    try:
        paginator = client.get_paginator('list_keys')
        for page in paginator.paginate():
            for key_entry in page.get('Keys', []):
                key_id = key_entry.get('KeyId', '')
                key_arn = key_entry.get('KeyArn', '')

                try:
                    desc_resp = client.describe_key(KeyId=key_id)
                    meta = desc_resp.get('KeyMetadata', {})

                    # Skip AWS-managed keys
                    if meta.get('KeyManager', '') != 'CUSTOMER':
                        continue

                    key_state = meta.get('KeyState', '')
                    description = meta.get('Description', '')
                    key_usage = meta.get('KeyUsage', '')
                    key_spec = meta.get('KeySpec', '')
                    creation_date = str(meta.get('CreationDate', ''))
                    enabled = meta.get('Enabled', False)
                    rotation_enabled = False
                    try:
                        rot_resp = client.get_key_rotation_status(KeyId=key_id)
                        rotation_enabled = rot_resp.get('KeyRotationEnabled', False)
                    except Exception:
                        pass

                    # Fetch tags
                    tags_dict = {}
                    try:
                        tags_resp = client.list_resource_tags(KeyId=key_id)
                        tags_dict = tags_to_dict(tags_resp.get('Tags', []))
                    except Exception:
                        pass

                    key_name = tags_dict.get('Name', '') or description or key_id

                    resources.append(make_resource(
                        service='kms',
                        resource_type='key',
                        resource_id=key_id,
                        arn=key_arn,
                        name=key_name,
                        region=region,
                        details={
                            'key_state': key_state,
                            'description': description,
                            'key_usage': key_usage,
                            'key_spec': key_spec,
                            'creation_date': creation_date,
                            'enabled': enabled,
                            'rotation_enabled': rotation_enabled,
                        },
                        tags=tags_dict,
                    ))
                except Exception:
                    pass
    except Exception:
        pass

    # --- Aliases (non-aws/ only) ---
    try:
        paginator = client.get_paginator('list_aliases')
        for page in paginator.paginate():
            for alias in page.get('Aliases', []):
                alias_name = alias.get('AliasName', '')
                # Skip AWS-managed aliases
                if alias_name.startswith('alias/aws/'):
                    continue
                alias_arn = alias.get('AliasArn', '')
                target_key_id = alias.get('TargetKeyId', '')

                resources.append(make_resource(
                    service='kms',
                    resource_type='alias',
                    resource_id=alias_name,
                    arn=alias_arn,
                    name=alias_name,
                    region=region,
                    details={
                        'target_key_id': target_key_id,
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
