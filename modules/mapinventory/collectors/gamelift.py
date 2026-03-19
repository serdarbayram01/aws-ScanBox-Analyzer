"""
Map Inventory — Amazon GameLift Collector
Resource types: fleet, build, game-session-queue, matchmaking-configuration
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_gamelift_resources(session, region, account_id):
    """Collect Amazon GameLift resources in the given region."""
    resources = []
    try:
        client = session.client('gamelift', region_name=region)
    except Exception:
        return resources

    # ── Builds ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_builds')
        for page in paginator.paginate():
            for b in page.get('Builds', []):
                bid = b.get('BuildId', '')
                arn = b.get('BuildArn', '')
                resources.append(make_resource(
                    service='gamelift',
                    resource_type='build',
                    resource_id=bid,
                    arn=arn,
                    name=b.get('Name', bid),
                    region=region,
                    details={
                        'status': b.get('Status', ''),
                        'version': b.get('Version', ''),
                        'size_on_disk': b.get('SizeOnDisk', 0),
                        'operating_system': b.get('OperatingSystem', ''),
                        'creation_time': str(b.get('CreationTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Fleets ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_fleets')
        for page in paginator.paginate():
            fleet_ids = page.get('FleetIds', [])
            if fleet_ids:
                try:
                    desc = client.describe_fleet_attributes(FleetIds=fleet_ids)
                    for f in desc.get('FleetAttributes', []):
                        fid = f.get('FleetId', '')
                        arn = f.get('FleetArn', '')
                        resources.append(make_resource(
                            service='gamelift',
                            resource_type='fleet',
                            resource_id=fid,
                            arn=arn,
                            name=f.get('Name', fid),
                            region=region,
                            details={
                                'status': f.get('Status', ''),
                                'fleet_type': f.get('FleetType', ''),
                                'instance_type': f.get('InstanceType', ''),
                                'build_id': f.get('BuildId', ''),
                                'script_id': f.get('ScriptId', ''),
                                'operating_system': f.get('OperatingSystem', ''),
                                'creation_time': str(f.get('CreationTime', '')),
                                'compute_type': f.get('ComputeType', ''),
                            },
                        ))
                except Exception:
                    pass
    except Exception:
        pass

    # ── Game Session Queues ─────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_game_session_queues')
        for page in paginator.paginate():
            for q in page.get('GameSessionQueues', []):
                name = q.get('Name', '')
                arn = q.get('GameSessionQueueArn', '')
                resources.append(make_resource(
                    service='gamelift',
                    resource_type='game-session-queue',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'timeout_in_seconds': q.get('TimeoutInSeconds', 0),
                        'destinations': [d.get('DestinationArn', '') for d in q.get('Destinations', [])],
                    },
                ))
    except Exception:
        pass

    # ── Matchmaking Configurations ──────────────────────────────────
    try:
        paginator = client.get_paginator('describe_matchmaking_configurations')
        for page in paginator.paginate():
            for mc in page.get('Configurations', []):
                name = mc.get('Name', '')
                arn = mc.get('ConfigurationArn', '')
                resources.append(make_resource(
                    service='gamelift',
                    resource_type='matchmaking-configuration',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': mc.get('Description', ''),
                        'rule_set_name': mc.get('RuleSetName', ''),
                        'acceptance_required': mc.get('AcceptanceRequired', False),
                        'acceptance_timeout_seconds': mc.get('AcceptanceTimeoutSeconds', 0),
                        'additional_player_count': mc.get('AdditionalPlayerCount', 0),
                        'backfill_mode': mc.get('BackfillMode', ''),
                        'flex_match_mode': mc.get('FlexMatchMode', ''),
                        'creation_time': str(mc.get('CreationTime', '')),
                    },
                ))
    except Exception:
        pass

    return resources
