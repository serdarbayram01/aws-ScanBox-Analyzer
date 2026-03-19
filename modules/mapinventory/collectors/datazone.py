"""
Map Inventory — DataZone Collector
Resource types: domain, project
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_datazone_resources(session, region, account_id):
    """Collect DataZone resources in the given region."""
    resources = []
    try:
        client = session.client('datazone', region_name=region)
    except Exception:
        return resources

    # ── Domains ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_domains')
        for page in paginator.paginate():
            for d in page.get('items', []):
                domain_id = d.get('id', '')
                arn = d.get('arn', '')
                name = d.get('name', domain_id)
                resources.append(make_resource(
                    service='datazone',
                    resource_type='domain',
                    resource_id=domain_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': d.get('status', ''),
                        'description': d.get('description', ''),
                        'created_at': str(d.get('createdAt', '')),
                        'managed_account_id': d.get('managedAccountId', ''),
                    },
                ))

                # ── Projects within domain ──────────────────────────
                try:
                    proj_paginator = client.get_paginator('list_projects')
                    for ppage in proj_paginator.paginate(domainIdentifier=domain_id):
                        for p in ppage.get('items', []):
                            proj_id = p.get('id', '')
                            resources.append(make_resource(
                                service='datazone',
                                resource_type='project',
                                resource_id=proj_id,
                                arn=f'arn:aws:datazone:{region}:{account_id}:domain/{domain_id}/project/{proj_id}',
                                name=p.get('name', proj_id),
                                region=region,
                                details={
                                    'domain_id': domain_id,
                                    'description': p.get('description', ''),
                                    'created_at': str(p.get('createdAt', '')),
                                },
                            ))
                except Exception:
                    pass
    except Exception:
        pass

    return resources
