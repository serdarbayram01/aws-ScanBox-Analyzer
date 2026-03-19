"""
Map Inventory — VPC Lattice Collector
Resource types: service-network, service, target-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_vpc_lattice_resources(session, region, account_id):
    """Collect all VPC Lattice resource types in the given region."""
    resources = []
    try:
        client = session.client('vpc-lattice', region_name=region)
    except Exception:
        return resources

    # ── Service Networks ─────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_service_networks')
        for page in paginator.paginate():
            for sn in page.get('items', []):
                sn_id = sn.get('id', '')
                sn_arn = sn.get('arn', '')
                sn_name = sn.get('name', sn_id)
                # Fetch tags
                sn_tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=sn_arn)
                    sn_tags = tag_resp.get('tags', {})
                except Exception:
                    pass
                resources.append(make_resource(
                    service='vpc-lattice',
                    resource_type='service-network',
                    resource_id=sn_id,
                    arn=sn_arn,
                    name=sn_name,
                    region=region,
                    details={
                        'status': sn.get('status', ''),
                        'auth_type': sn.get('authType', ''),
                        'created_at': str(sn.get('createdAt', '')),
                        'last_updated_at': str(sn.get('lastUpdatedAt', '')),
                        'number_of_associated_services': sn.get(
                            'numberOfAssociatedServices', 0),
                        'number_of_associated_vpcs': sn.get(
                            'numberOfAssociatedVPCs', 0),
                    },
                    tags=sn_tags if isinstance(sn_tags, dict) else {},
                ))
    except Exception:
        pass

    # ── Services ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_services')
        for page in paginator.paginate():
            for svc in page.get('items', []):
                svc_id = svc.get('id', '')
                svc_arn = svc.get('arn', '')
                svc_name = svc.get('name', svc_id)
                # Fetch tags
                svc_tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=svc_arn)
                    svc_tags = tag_resp.get('tags', {})
                except Exception:
                    pass
                resources.append(make_resource(
                    service='vpc-lattice',
                    resource_type='service',
                    resource_id=svc_id,
                    arn=svc_arn,
                    name=svc_name,
                    region=region,
                    details={
                        'status': svc.get('status', ''),
                        'dns_name': svc.get('dnsEntry', {}).get('domainName', ''),
                        'custom_domain_name': svc.get('customDomainName', ''),
                        'created_at': str(svc.get('createdAt', '')),
                        'last_updated_at': str(svc.get('lastUpdatedAt', '')),
                    },
                    tags=svc_tags if isinstance(svc_tags, dict) else {},
                ))
    except Exception:
        pass

    # ── Target Groups ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_target_groups')
        for page in paginator.paginate():
            for tg in page.get('items', []):
                tg_id = tg.get('id', '')
                tg_arn = tg.get('arn', '')
                tg_name = tg.get('name', tg_id)
                # Fetch tags
                tg_tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=tg_arn)
                    tg_tags = tag_resp.get('tags', {})
                except Exception:
                    pass
                resources.append(make_resource(
                    service='vpc-lattice',
                    resource_type='target-group',
                    resource_id=tg_id,
                    arn=tg_arn,
                    name=tg_name,
                    region=region,
                    details={
                        'status': tg.get('status', ''),
                        'type': tg.get('type', ''),
                        'vpc_id': tg.get('vpcIdentifier', ''),
                        'protocol': tg.get('protocol', ''),
                        'port': tg.get('port', ''),
                        'ip_address_type': tg.get('ipAddressType', ''),
                        'created_at': str(tg.get('createdAt', '')),
                        'last_updated_at': str(tg.get('lastUpdatedAt', '')),
                        'service_arns': tg.get('serviceArns', []),
                    },
                    tags=tg_tags if isinstance(tg_tags, dict) else {},
                ))
    except Exception:
        pass

    return resources
