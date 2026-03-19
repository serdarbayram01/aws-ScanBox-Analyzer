"""
Map Inventory — AWS Outposts Collector
Resource types: outpost, site
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_outposts_resources(session, region, account_id):
    """Collect AWS Outposts resources in the given region."""
    resources = []
    try:
        client = session.client('outposts', region_name=region)
    except Exception:
        return resources

    # ── Sites ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_sites')
        for page in paginator.paginate():
            for s in page.get('Sites', []):
                sid = s.get('SiteId', '')
                arn = s.get('SiteArn', '')
                tags_dict = s.get('Tags', {})
                resources.append(make_resource(
                    service='outposts',
                    resource_type='site',
                    resource_id=sid,
                    arn=arn,
                    name=s.get('Name', sid),
                    region=region,
                    details={
                        'description': s.get('Description', ''),
                        'account_id': s.get('AccountId', ''),
                        'operating_address_city': s.get('OperatingAddress', {}).get('City', ''),
                        'operating_address_country': s.get('OperatingAddress', {}).get('CountryCode', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Outposts ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_outposts')
        for page in paginator.paginate():
            for o in page.get('Outposts', []):
                oid = o.get('OutpostId', '')
                arn = o.get('OutpostArn', '')
                tags_dict = o.get('Tags', {})
                resources.append(make_resource(
                    service='outposts',
                    resource_type='outpost',
                    resource_id=oid,
                    arn=arn,
                    name=o.get('Name', oid),
                    region=region,
                    details={
                        'description': o.get('Description', ''),
                        'life_cycle_status': o.get('LifeCycleStatus', ''),
                        'availability_zone': o.get('AvailabilityZone', ''),
                        'site_id': o.get('SiteId', ''),
                        'site_arn': o.get('SiteArn', ''),
                        'owner_id': o.get('OwnerId', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
