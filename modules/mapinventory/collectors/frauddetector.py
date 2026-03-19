"""
Map Inventory — Amazon Fraud Detector Collector
Resource types: detector, model, event-type
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_frauddetector_resources(session, region, account_id):
    """Collect Amazon Fraud Detector resources in the given region."""
    resources = []
    try:
        client = session.client('frauddetector', region_name=region)
    except Exception:
        return resources

    # ── Detectors ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_detectors')
        for page in paginator.paginate():
            for d in page.get('detectors', []):
                did = d.get('detectorId', '')
                arn = d.get('arn', '')
                resources.append(make_resource(
                    service='frauddetector',
                    resource_type='detector',
                    resource_id=did,
                    arn=arn,
                    name=did,
                    region=region,
                    details={
                        'description': d.get('description', ''),
                        'event_type_name': d.get('eventTypeName', ''),
                        'created_time': d.get('createdTime', ''),
                        'last_updated_time': d.get('lastUpdatedTime', ''),
                    },
                ))
    except Exception:
        pass

    # ── Models ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_models')
        for page in paginator.paginate():
            for m in page.get('models', []):
                mid = m.get('modelId', '')
                arn = m.get('arn', '')
                resources.append(make_resource(
                    service='frauddetector',
                    resource_type='model',
                    resource_id=mid,
                    arn=arn,
                    name=mid,
                    region=region,
                    details={
                        'model_type': m.get('modelType', ''),
                        'description': m.get('description', ''),
                        'event_type_name': m.get('eventTypeName', ''),
                        'created_time': m.get('createdTime', ''),
                        'last_updated_time': m.get('lastUpdatedTime', ''),
                    },
                ))
    except Exception:
        pass

    # ── Event Types ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_event_types')
        for page in paginator.paginate():
            for et in page.get('eventTypes', []):
                name = et.get('name', '')
                arn = et.get('arn', '')
                resources.append(make_resource(
                    service='frauddetector',
                    resource_type='event-type',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': et.get('description', ''),
                        'entity_types': et.get('entityTypes', []),
                        'event_variables': et.get('eventVariables', []),
                        'labels': et.get('labels', []),
                        'created_time': et.get('createdTime', ''),
                        'last_updated_time': et.get('lastUpdatedTime', ''),
                    },
                ))
    except Exception:
        pass

    return resources
