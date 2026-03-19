"""
Map Inventory — EventBridge Collector
Resource types: event-bus, rule, archive, connection, api-destination
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_events_resources(session, region, account_id):
    """Collect EventBridge resources for a given region."""
    resources = []
    try:
        client = session.client('events', region_name=region)
    except Exception:
        return resources

    # ── Event Buses ───────────────────────────────────────────────────
    bus_names = []
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_event_buses(**kwargs)
            for bus in resp.get('EventBuses', []):
                bus_name = bus.get('Name', '')
                bus_arn = bus.get('Arn', '')
                is_default = (bus_name == 'default')
                bus_names.append(bus_name)

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceARN=bus_arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='events',
                    resource_type='event-bus',
                    resource_id=bus_name,
                    arn=bus_arn,
                    name=bus_name,
                    region=region,
                    details={
                        'policy': bool(bus.get('Policy', '')),
                    },
                    tags=tags,
                    is_default=is_default,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Rules (per event bus) ─────────────────────────────────────────
    for bus_name in bus_names:
        try:
            paginator = client.get_paginator('list_rules')
            for page in paginator.paginate(EventBusName=bus_name):
                for rule in page.get('Rules', []):
                    rule_name = rule.get('Name', '')
                    rule_arn = rule.get('Arn', '')

                    tags = {}
                    try:
                        tag_resp = client.list_tags_for_resource(ResourceARN=rule_arn)
                        tags = tags_to_dict(tag_resp.get('Tags', []))
                    except Exception:
                        pass

                    # Count targets
                    target_count = 0
                    try:
                        t_resp = client.list_targets_by_rule(
                            Rule=rule_name, EventBusName=bus_name)
                        target_count = len(t_resp.get('Targets', []))
                    except Exception:
                        pass

                    resources.append(make_resource(
                        service='events',
                        resource_type='rule',
                        resource_id=rule_name,
                        arn=rule_arn,
                        name=rule_name,
                        region=region,
                        details={
                            'event_bus': bus_name,
                            'state': rule.get('State', ''),
                            'description': rule.get('Description', ''),
                            'schedule_expression': rule.get('ScheduleExpression', ''),
                            'event_pattern': bool(rule.get('EventPattern', '')),
                            'managed_by': rule.get('ManagedBy', ''),
                            'target_count': target_count,
                        },
                        tags=tags,
                    ))
        except Exception:
            pass

    # ── Archives ──────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_archives(**kwargs)
            for arch in resp.get('Archives', []):
                arch_name = arch.get('ArchiveName', '')
                arn = f"arn:aws:events:{region}:{account_id}:archive/{arch_name}"

                resources.append(make_resource(
                    service='events',
                    resource_type='archive',
                    resource_id=arch_name,
                    arn=arn,
                    name=arch_name,
                    region=region,
                    details={
                        'event_source_arn': arch.get('EventSourceArn', ''),
                        'state': arch.get('State', ''),
                        'state_reason': arch.get('StateReason', ''),
                        'retention_days': arch.get('RetentionDays', 0),
                        'size_bytes': arch.get('SizeBytes', 0),
                        'event_count': arch.get('EventCount', 0),
                        'creation_time': str(arch.get('CreationTime', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Connections ───────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_connections(**kwargs)
            for conn in resp.get('Connections', []):
                conn_name = conn.get('Name', '')
                conn_arn = conn.get('ConnectionArn', '')

                resources.append(make_resource(
                    service='events',
                    resource_type='connection',
                    resource_id=conn_name,
                    arn=conn_arn,
                    name=conn_name,
                    region=region,
                    details={
                        'state': conn.get('ConnectionState', ''),
                        'state_reason': conn.get('StateReason', ''),
                        'authorization_type': conn.get('AuthorizationType', ''),
                        'creation_time': str(conn.get('CreationTime', '')),
                        'last_modified_time': str(conn.get('LastModifiedTime', '')),
                        'last_authorized_time': str(conn.get('LastAuthorizedTime', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── API Destinations ──────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_api_destinations(**kwargs)
            for dest in resp.get('ApiDestinations', []):
                dest_name = dest.get('Name', '')
                dest_arn = dest.get('ApiDestinationArn', '')

                resources.append(make_resource(
                    service='events',
                    resource_type='api-destination',
                    resource_id=dest_name,
                    arn=dest_arn,
                    name=dest_name,
                    region=region,
                    details={
                        'state': dest.get('ApiDestinationState', ''),
                        'connection_arn': dest.get('ConnectionArn', ''),
                        'invocation_endpoint': dest.get('InvocationEndpoint', ''),
                        'http_method': dest.get('HttpMethod', ''),
                        'invocation_rate_limit': dest.get('InvocationRateLimitPerSecond', 0),
                        'creation_time': str(dest.get('CreationTime', '')),
                        'last_modified_time': str(dest.get('LastModifiedTime', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
