"""
Map Inventory — Amazon Location Service Collector
Resource types: map, place-index, route-calculator, tracker, geofence-collection
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_location_resources(session, region, account_id):
    """Collect Amazon Location Service resources in the given region."""
    resources = []
    try:
        client = session.client('location', region_name=region)
    except Exception:
        return resources

    # ── Maps ────────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_maps')
        for page in paginator.paginate():
            for m in page.get('Entries', []):
                name = m.get('MapName', '')
                resources.append(make_resource(
                    service='location',
                    resource_type='map',
                    resource_id=name,
                    arn=f'arn:aws:geo:{region}:{account_id}:map/{name}',
                    name=name,
                    region=region,
                    details={
                        'description': m.get('Description', ''),
                        'data_source': m.get('DataSource', ''),
                        'pricing_plan': m.get('PricingPlan', ''),
                        'create_time': str(m.get('CreateTime', '')),
                        'update_time': str(m.get('UpdateTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Place Indexes ───────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_place_indexes')
        for page in paginator.paginate():
            for pi in page.get('Entries', []):
                name = pi.get('IndexName', '')
                resources.append(make_resource(
                    service='location',
                    resource_type='place-index',
                    resource_id=name,
                    arn=f'arn:aws:geo:{region}:{account_id}:place-index/{name}',
                    name=name,
                    region=region,
                    details={
                        'description': pi.get('Description', ''),
                        'data_source': pi.get('DataSource', ''),
                        'pricing_plan': pi.get('PricingPlan', ''),
                        'create_time': str(pi.get('CreateTime', '')),
                        'update_time': str(pi.get('UpdateTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Route Calculators ───────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_route_calculators')
        for page in paginator.paginate():
            for rc in page.get('Entries', []):
                name = rc.get('CalculatorName', '')
                resources.append(make_resource(
                    service='location',
                    resource_type='route-calculator',
                    resource_id=name,
                    arn=f'arn:aws:geo:{region}:{account_id}:route-calculator/{name}',
                    name=name,
                    region=region,
                    details={
                        'description': rc.get('Description', ''),
                        'data_source': rc.get('DataSource', ''),
                        'pricing_plan': rc.get('PricingPlan', ''),
                        'create_time': str(rc.get('CreateTime', '')),
                        'update_time': str(rc.get('UpdateTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Trackers ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_trackers')
        for page in paginator.paginate():
            for t in page.get('Entries', []):
                name = t.get('TrackerName', '')
                resources.append(make_resource(
                    service='location',
                    resource_type='tracker',
                    resource_id=name,
                    arn=f'arn:aws:geo:{region}:{account_id}:tracker/{name}',
                    name=name,
                    region=region,
                    details={
                        'description': t.get('Description', ''),
                        'pricing_plan': t.get('PricingPlan', ''),
                        'create_time': str(t.get('CreateTime', '')),
                        'update_time': str(t.get('UpdateTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Geofence Collections ────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_geofence_collections')
        for page in paginator.paginate():
            for gc in page.get('Entries', []):
                name = gc.get('CollectionName', '')
                resources.append(make_resource(
                    service='location',
                    resource_type='geofence-collection',
                    resource_id=name,
                    arn=f'arn:aws:geo:{region}:{account_id}:geofence-collection/{name}',
                    name=name,
                    region=region,
                    details={
                        'description': gc.get('Description', ''),
                        'pricing_plan': gc.get('PricingPlan', ''),
                        'create_time': str(gc.get('CreateTime', '')),
                        'update_time': str(gc.get('UpdateTime', '')),
                    },
                ))
    except Exception:
        pass

    return resources
