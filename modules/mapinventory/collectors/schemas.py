"""
Map Inventory — EventBridge Schema Registry Collector
Resource types: registry, schema
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_schemas_resources(session, region, account_id):
    """Collect EventBridge Schema Registry resources in the given region."""
    resources = []
    try:
        client = session.client('schemas', region_name=region)
    except Exception:
        return resources

    # ── Registries ──────────────────────────────────────────────────
    registry_names = []
    try:
        paginator = client.get_paginator('list_registries')
        for page in paginator.paginate():
            for r in page.get('Registries', []):
                name = r.get('RegistryName', '')
                arn = r.get('RegistryArn', '')
                is_default = name.startswith('aws.')
                registry_names.append(name)
                tags_dict = r.get('Tags', {})
                resources.append(make_resource(
                    service='schemas',
                    resource_type='registry',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={},
                    tags=tags_dict,
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Schemas ─────────────────────────────────────────────────────
    for reg_name in registry_names:
        try:
            paginator = client.get_paginator('list_schemas')
            for page in paginator.paginate(RegistryName=reg_name):
                for s in page.get('Schemas', []):
                    sname = s.get('SchemaName', '')
                    arn = s.get('SchemaArn', '')
                    is_default = reg_name.startswith('aws.')
                    tags_dict = s.get('Tags', {})
                    resources.append(make_resource(
                        service='schemas',
                        resource_type='schema',
                        resource_id=f'{reg_name}/{sname}',
                        arn=arn,
                        name=sname,
                        region=region,
                        details={
                            'registry_name': reg_name,
                            'version_count': s.get('VersionCount', 0),
                            'last_modified': str(s.get('LastModified', '')),
                        },
                        tags=tags_dict,
                        is_default=is_default,
                    ))
        except Exception:
            pass

    return resources
