"""
Map Inventory — AWS Health Collector
Resource types: event
GLOBAL — uses us-east-1.
"""

from .base import make_resource, tags_to_dict


def collect_health_resources(session, region, account_id):
    """Collect AWS Health events (global service, us-east-1)."""
    resources = []
    try:
        client = session.client('health', region_name='us-east-1')
    except Exception:
        return resources

    # ── Events ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_events')
        for page in paginator.paginate():
            for e in page.get('events', []):
                arn = e.get('arn', '')
                eid = arn.split('/')[-1] if '/' in arn else arn
                service_name = e.get('service', '')
                event_type_code = e.get('eventTypeCode', '')
                resources.append(make_resource(
                    service='health',
                    resource_type='event',
                    resource_id=eid,
                    arn=arn,
                    name=event_type_code or eid,
                    region=e.get('region', 'global'),
                    details={
                        'event_type_code': event_type_code,
                        'event_type_category': e.get('eventTypeCategory', ''),
                        'aws_service': service_name,
                        'availability_zone': e.get('availabilityZone', ''),
                        'start_time': str(e.get('startTime', '')),
                        'end_time': str(e.get('endTime', '')),
                        'last_updated_time': str(e.get('lastUpdatedTime', '')),
                        'status_code': e.get('statusCode', ''),
                        'event_scope_code': e.get('eventScopeCode', ''),
                    },
                ))
    except Exception:
        pass

    return resources
