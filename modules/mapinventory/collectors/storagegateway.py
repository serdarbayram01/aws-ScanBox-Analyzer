"""
Map Inventory — Storage Gateway Collector
Resource types: gateway, volume, tape
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_storagegateway_resources(session, region, account_id):
    """Collect all Storage Gateway resource types in the given region."""
    resources = []
    try:
        client = session.client('storagegateway', region_name=region)
    except Exception:
        return resources

    # ── Gateways ─────────────────────────────────────────────────────
    gateways = []
    try:
        paginator = client.get_paginator('list_gateways')
        for page in paginator.paginate():
            for gw in page.get('Gateways', []):
                gateways.append(gw)
                gw_arn = gw.get('GatewayARN', '')
                gw_id = gw.get('GatewayId', '')
                gw_name = gw.get('GatewayName', gw_id)
                # Fetch tags for this gateway
                gw_tags = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceARN=gw_arn)
                    gw_tags = tag_resp.get('Tags', [])
                except Exception:
                    pass
                resources.append(make_resource(
                    service='storagegateway',
                    resource_type='gateway',
                    resource_id=gw_id,
                    arn=gw_arn,
                    name=gw_name,
                    region=region,
                    details={
                        'gateway_type': gw.get('GatewayType', ''),
                        'gateway_operational_state': gw.get('GatewayOperationalState', ''),
                        'ec2_instance_id': gw.get('Ec2InstanceId', ''),
                        'ec2_instance_region': gw.get('Ec2InstanceRegion', ''),
                        'host_environment': gw.get('HostEnvironment', ''),
                    },
                    tags=tags_to_dict(gw_tags),
                ))
    except Exception:
        pass

    # ── Volumes (from cached gateways) ───────────────────────────────
    for gw in gateways:
        gw_arn = gw.get('GatewayARN', '')
        try:
            paginator = client.get_paginator('list_volumes')
            for page in paginator.paginate(GatewayARN=gw_arn):
                for vol in page.get('VolumeInfos', []):
                    vol_arn = vol.get('VolumeARN', '')
                    vol_id = vol.get('VolumeId', '')
                    vol_type = vol.get('VolumeType', '')
                    # Fetch tags
                    vol_tags = []
                    try:
                        tag_resp = client.list_tags_for_resource(ResourceARN=vol_arn)
                        vol_tags = tag_resp.get('Tags', [])
                    except Exception:
                        pass
                    resources.append(make_resource(
                        service='storagegateway',
                        resource_type='volume',
                        resource_id=vol_id,
                        arn=vol_arn,
                        name=get_tag_value(vol_tags, 'Name') or vol_id,
                        region=region,
                        details={
                            'volume_type': vol_type,
                            'volume_size_bytes': vol.get('VolumeSizeInBytes', 0),
                            'gateway_arn': gw_arn,
                            'gateway_id': gw.get('GatewayId', ''),
                        },
                        tags=tags_to_dict(vol_tags),
                    ))
        except Exception:
            pass

    # ── Tapes (from cached gateways) ─────────────────────────────────
    for gw in gateways:
        gw_arn = gw.get('GatewayARN', '')
        if gw.get('GatewayType', '') not in ('VTL', 'VTL_SNOW'):
            continue
        try:
            paginator = client.get_paginator('list_tapes')
            for page in paginator.paginate():
                for tape in page.get('TapeInfos', []):
                    tape_arn = tape.get('TapeARN', '')
                    tape_barcode = tape.get('TapeBarcode', '')
                    # Fetch tags
                    tape_tags = []
                    try:
                        tag_resp = client.list_tags_for_resource(ResourceARN=tape_arn)
                        tape_tags = tag_resp.get('Tags', [])
                    except Exception:
                        pass
                    resources.append(make_resource(
                        service='storagegateway',
                        resource_type='tape',
                        resource_id=tape_barcode,
                        arn=tape_arn,
                        name=tape_barcode,
                        region=region,
                        details={
                            'tape_size_bytes': tape.get('TapeSizeInBytes', 0),
                            'tape_status': tape.get('TapeStatus', ''),
                            'gateway_arn': tape.get('GatewayARN', ''),
                            'pool_id': tape.get('PoolId', ''),
                        },
                        tags=tags_to_dict(tape_tags),
                    ))
        except Exception:
            pass

    return resources
