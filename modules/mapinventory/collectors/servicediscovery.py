"""
Map Inventory — AWS Cloud Map (Service Discovery) Collector
Resource types: namespace, service
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_servicediscovery_resources(session, region, account_id):
    """Collect Cloud Map (Service Discovery) resources in the given region."""
    resources = []
    try:
        client = session.client('servicediscovery', region_name=region)
    except Exception:
        return resources

    # ── Namespaces ──────────────────────────────────────────────────
    ns_ids = []
    try:
        paginator = client.get_paginator('list_namespaces')
        for page in paginator.paginate():
            for ns in page.get('Namespaces', []):
                nsid = ns.get('Id', '')
                arn = ns.get('Arn', '')
                ns_ids.append(nsid)
                resources.append(make_resource(
                    service='servicediscovery',
                    resource_type='namespace',
                    resource_id=nsid,
                    arn=arn,
                    name=ns.get('Name', nsid),
                    region=region,
                    details={
                        'type': ns.get('Type', ''),
                        'description': ns.get('Description', ''),
                        'service_count': ns.get('ServiceCount', 0),
                        'create_date': str(ns.get('CreateDate', '')),
                    },
                ))
    except Exception:
        pass

    # ── Services ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_services')
        for page in paginator.paginate():
            for svc in page.get('Services', []):
                sid = svc.get('Id', '')
                arn = svc.get('Arn', '')
                resources.append(make_resource(
                    service='servicediscovery',
                    resource_type='service',
                    resource_id=sid,
                    arn=arn,
                    name=svc.get('Name', sid),
                    region=region,
                    details={
                        'description': svc.get('Description', ''),
                        'instance_count': svc.get('InstanceCount', 0),
                        'type': svc.get('Type', ''),
                        'create_date': str(svc.get('CreateDate', '')),
                        'dns_config': str(svc.get('DnsConfig', {})),
                    },
                ))
    except Exception:
        pass

    return resources
