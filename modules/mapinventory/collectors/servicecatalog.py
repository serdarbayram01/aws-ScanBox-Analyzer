"""
Map Inventory — AWS Service Catalog Collector
Resource types: portfolio, product
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_servicecatalog_resources(session, region, account_id):
    """Collect Service Catalog resources in the given region."""
    resources = []
    try:
        client = session.client('servicecatalog', region_name=region)
    except Exception:
        return resources

    # ── Portfolios ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_portfolios')
        for page in paginator.paginate():
            for p in page.get('PortfolioDetails', []):
                pid = p.get('Id', '')
                arn = p.get('ARN', '')
                resources.append(make_resource(
                    service='servicecatalog',
                    resource_type='portfolio',
                    resource_id=pid,
                    arn=arn,
                    name=p.get('DisplayName', pid),
                    region=region,
                    details={
                        'description': p.get('Description', ''),
                        'provider_name': p.get('ProviderName', ''),
                        'created_time': str(p.get('CreatedTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Products ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('search_products_as_admin')
        for page in paginator.paginate():
            for pv in page.get('ProductViewDetails', []):
                pvs = pv.get('ProductViewSummary', {})
                pid = pvs.get('ProductId', '')
                name = pvs.get('Name', pid)
                resources.append(make_resource(
                    service='servicecatalog',
                    resource_type='product',
                    resource_id=pid,
                    arn=pv.get('ProductARN', ''),
                    name=name,
                    region=region,
                    details={
                        'description': pvs.get('ShortDescription', ''),
                        'owner': pvs.get('Owner', ''),
                        'type': pvs.get('Type', ''),
                        'distributor': pvs.get('Distributor', ''),
                        'has_default_path': pvs.get('HasDefaultPath', False),
                        'support_email': pvs.get('SupportEmail', ''),
                        'created_time': str(pv.get('CreatedTime', '')),
                        'status': pv.get('Status', ''),
                    },
                ))
    except Exception:
        pass

    return resources
