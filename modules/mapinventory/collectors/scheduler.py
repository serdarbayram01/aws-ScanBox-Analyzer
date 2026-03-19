"""
Map Inventory — EventBridge Scheduler Collector
Resource types: schedule, schedule-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_scheduler_resources(session, region, account_id):
    """Collect EventBridge Scheduler resources in the given region."""
    resources = []
    try:
        client = session.client('scheduler', region_name=region)
    except Exception:
        return resources

    # ── Schedule Groups ─────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_schedule_groups')
        for page in paginator.paginate():
            for g in page.get('ScheduleGroups', []):
                name = g.get('Name', '')
                arn = g.get('Arn', '')
                is_default = (name == 'default')
                resources.append(make_resource(
                    service='scheduler',
                    resource_type='schedule-group',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'state': g.get('State', ''),
                        'creation_date': str(g.get('CreationDate', '')),
                        'last_modification_date': str(g.get('LastModificationDate', '')),
                    },
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Schedules ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_schedules')
        for page in paginator.paginate():
            for s in page.get('Schedules', []):
                name = s.get('Name', '')
                arn = s.get('Arn', '')
                resources.append(make_resource(
                    service='scheduler',
                    resource_type='schedule',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'group_name': s.get('GroupName', ''),
                        'state': s.get('State', ''),
                        'schedule_expression': s.get('ScheduleExpression', ''),
                        'creation_date': str(s.get('CreationDate', '')),
                        'last_modification_date': str(s.get('LastModificationDate', '')),
                    },
                ))
    except Exception:
        pass

    return resources
