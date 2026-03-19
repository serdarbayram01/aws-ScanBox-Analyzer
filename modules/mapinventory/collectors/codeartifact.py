"""
Map Inventory — CodeArtifact Collector
Resource types: domain, repository
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_codeartifact_resources(session, region, account_id):
    """Collect CodeArtifact resources in the given region."""
    resources = []
    try:
        client = session.client('codeartifact', region_name=region)
    except Exception:
        return resources

    # ── Domains ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_domains')
        for page in paginator.paginate():
            for d in page.get('domains', []):
                name = d.get('name', '')
                arn = d.get('arn', '')
                resources.append(make_resource(
                    service='codeartifact',
                    resource_type='domain',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'owner': d.get('owner', ''),
                        'status': d.get('status', ''),
                        'created_time': str(d.get('createdTime', '')),
                        'encryption_key': d.get('encryptionKey', ''),
                    },
                ))
    except Exception:
        pass

    # ── Repositories ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_repositories')
        for page in paginator.paginate():
            for r in page.get('repositories', []):
                name = r.get('name', '')
                arn = r.get('arn', '')
                resources.append(make_resource(
                    service='codeartifact',
                    resource_type='repository',
                    resource_id=f"{r.get('domainName', '')}/{name}",
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'domain_name': r.get('domainName', ''),
                        'domain_owner': r.get('domainOwner', ''),
                        'description': r.get('description', ''),
                    },
                ))
    except Exception:
        pass

    return resources
