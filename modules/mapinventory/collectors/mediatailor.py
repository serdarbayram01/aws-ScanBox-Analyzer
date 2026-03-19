"""
Map Inventory — MediaTailor Collector
Resource types: channel, source-location, playback-configuration
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_mediatailor_resources(session, region, account_id):
    """Collect MediaTailor resources in the given region."""
    resources = []
    try:
        client = session.client('mediatailor', region_name=region)
    except Exception:
        return resources

    # ── Playback Configurations ─────────────────────────────────────
    try:
        paginator = client.get_paginator('list_playback_configurations')
        for page in paginator.paginate():
            for pc in page.get('Items', []):
                name = pc.get('Name', '')
                arn = pc.get('PlaybackConfigurationArn', '')
                tags_dict = pc.get('Tags', {})
                resources.append(make_resource(
                    service='mediatailor',
                    resource_type='playback-configuration',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'ad_decision_server_url': pc.get('AdDecisionServerUrl', ''),
                        'cdn_configuration': str(pc.get('CdnConfiguration', {})),
                        'video_content_source_url': pc.get('VideoContentSourceUrl', ''),
                        'session_initialization_endpoint_prefix': pc.get('SessionInitializationEndpointPrefix', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Channels ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_channels')
        for page in paginator.paginate():
            for ch in page.get('Items', []):
                name = ch.get('ChannelName', '')
                arn = ch.get('Arn', '')
                tags_dict = ch.get('Tags', {})
                resources.append(make_resource(
                    service='mediatailor',
                    resource_type='channel',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'channel_state': ch.get('ChannelState', ''),
                        'creation_time': str(ch.get('CreationTime', '')),
                        'last_modified_time': str(ch.get('LastModifiedTime', '')),
                        'tier': ch.get('Tier', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Source Locations ────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_source_locations')
        for page in paginator.paginate():
            for sl in page.get('Items', []):
                name = sl.get('SourceLocationName', '')
                arn = sl.get('Arn', '')
                tags_dict = sl.get('Tags', {})
                resources.append(make_resource(
                    service='mediatailor',
                    resource_type='source-location',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'http_configuration': str(sl.get('HttpConfiguration', {})),
                        'creation_time': str(sl.get('CreationTime', '')),
                        'last_modified_time': str(sl.get('LastModifiedTime', '')),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
