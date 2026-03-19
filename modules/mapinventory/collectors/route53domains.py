"""
Map Inventory — Amazon Route 53 Domains Collector
Resource types: domain
GLOBAL service — Route 53 Domains API is only available in us-east-1.
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_route53domains_resources(session, region, account_id):
    """Collect Route 53 registered domains. Only runs in us-east-1."""
    resources = []

    # Route 53 Domains API is only available in us-east-1
    if region != 'us-east-1':
        return resources

    try:
        client = session.client('route53domains', region_name='us-east-1')
    except Exception:
        return resources

    # ── Domains ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_domains')
        for page in paginator.paginate():
            for domain_summary in page.get('Domains', []):
                domain_name = domain_summary.get('DomainName', '')

                # Get detailed info
                details_dict = {
                    'auto_renew': domain_summary.get('AutoRenew', False),
                    'transfer_lock': domain_summary.get('TransferLock', False),
                    'expiry': str(domain_summary.get('Expiry', '')),
                }

                try:
                    detail = client.get_domain_detail(DomainName=domain_name)
                    details_dict.update({
                        'registrar_name': detail.get('RegistrarName', ''),
                        'creation_date': str(detail.get('CreationDate', '')),
                        'expiration_date': str(detail.get('ExpirationDate', '')),
                        'updated_date': str(detail.get('UpdatedDate', '')),
                        'status_list': detail.get('StatusList', []),
                        'nameservers': [ns.get('Name', '') for ns in detail.get('Nameservers', [])],
                        'auto_renew': detail.get('AutoRenew', False),
                        'admin_privacy': detail.get('AdminPrivacy', False),
                        'registrant_privacy': detail.get('RegistrantPrivacy', False),
                        'tech_privacy': detail.get('TechPrivacy', False),
                        'dnssec_status': detail.get('DnssecKeys', []) != [],
                    })
                except Exception:
                    pass

                tags = {}
                try:
                    tag_resp = client.list_tags_for_domain(DomainName=domain_name)
                    tags = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass

                domain_arn = f"arn:aws:route53domains:::domain/{domain_name}"
                resources.append(make_resource(
                    service='route53domains',
                    resource_type='domain',
                    resource_id=domain_name,
                    arn=domain_arn,
                    name=domain_name,
                    region='global',
                    details=details_dict,
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
