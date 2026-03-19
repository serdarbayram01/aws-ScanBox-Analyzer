"""
Map Inventory — Amazon IVS (Interactive Video Service) Collector
Resource types: channel, recording-configuration, playback-key-pair
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ivs_resources(session, region, account_id):
    """Collect Amazon IVS resources in the given region."""
    resources = []
    try:
        client = session.client('ivs', region_name=region)
    except Exception:
        return resources

    # ── Channels ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_channels')
        for page in paginator.paginate():
            for ch in page.get('channels', []):
                arn = ch.get('arn', '')
                name = ch.get('name', arn.split('/')[-1] if '/' in arn else arn)
                tags_dict = ch.get('tags', {})
                resources.append(make_resource(
                    service='ivs',
                    resource_type='channel',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'latency_mode': ch.get('latencyMode', ''),
                        'type': ch.get('type', ''),
                        'recording_configuration_arn': ch.get('recordingConfigurationArn', ''),
                        'authorized': ch.get('authorized', False),
                        'insecure_ingest': ch.get('insecureIngest', False),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Recording Configurations ────────────────────────────────────
    try:
        paginator = client.get_paginator('list_recording_configurations')
        for page in paginator.paginate():
            for rc in page.get('recordingConfigurations', []):
                arn = rc.get('arn', '')
                name = rc.get('name', arn.split('/')[-1] if '/' in arn else arn)
                tags_dict = rc.get('tags', {})
                resources.append(make_resource(
                    service='ivs',
                    resource_type='recording-configuration',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'state': rc.get('state', ''),
                        'destination_configuration': str(rc.get('destinationConfiguration', {})),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Playback Key Pairs ──────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_playback_key_pairs')
        for page in paginator.paginate():
            for kp in page.get('keyPairs', []):
                arn = kp.get('arn', '')
                name = kp.get('name', arn.split('/')[-1] if '/' in arn else arn)
                tags_dict = kp.get('tags', {})
                resources.append(make_resource(
                    service='ivs',
                    resource_type='playback-key-pair',
                    resource_id=arn.split('/')[-1] if '/' in arn else arn,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'fingerprint': kp.get('fingerprint', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
