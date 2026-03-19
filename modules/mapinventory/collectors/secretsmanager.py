"""
Map Inventory — Secrets Manager Collector
Resource types: secret
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_secretsmanager_resources(session, region, account_id):
    """Collect all Secrets Manager resources in the given region."""
    resources = []
    try:
        sm = session.client('secretsmanager', region_name=region)
    except Exception:
        return resources

    # ── Secrets ──────────────────────────────────────────────────────
    try:
        paginator = sm.get_paginator('list_secrets')
        for page in paginator.paginate():
            for secret in page.get('SecretList', []):
                secret_name = secret.get('Name', '')
                secret_arn = secret.get('ARN', '')
                tags = secret.get('Tags', [])
                display_name = get_tag_value(tags, 'Name') or secret_name
                resources.append(make_resource(
                    service='secretsmanager',
                    resource_type='secret',
                    resource_id=secret_name,
                    arn=secret_arn,
                    name=display_name,
                    region=region,
                    details={
                        'description': secret.get('Description', ''),
                        'kms_key_id': secret.get('KmsKeyId', ''),
                        'rotation_enabled': secret.get('RotationEnabled', False),
                        'rotation_lambda_arn': secret.get('RotationLambdaARN', ''),
                        'last_rotated_date': str(secret.get('LastRotatedDate', '')),
                        'last_changed_date': str(secret.get('LastChangedDate', '')),
                        'last_accessed_date': str(secret.get('LastAccessedDate', '')),
                        'primary_region': secret.get('PrimaryRegion', ''),
                        'rotation_rules': str(secret.get('RotationRules', {})),
                        'created_date': str(secret.get('CreatedDate', '')),
                        'deleted_date': str(secret.get('DeletedDate', '')),
                        'owning_service': secret.get('OwningService', ''),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    return resources
