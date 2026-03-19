"""
Map Inventory — Network Manager Collector (GLOBAL)
Resource types: global-network, core-network, site, link, device
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_networkmanager_resources(session, region, account_id):
    """Collect all Network Manager resource types (global service)."""
    resources = []
    try:
        client = session.client('networkmanager', region_name='us-west-2')
    except Exception:
        return resources

    # ── Global Networks ──────────────────────────────────────────────
    global_networks = []
    try:
        paginator = client.get_paginator('describe_global_networks')
        for page in paginator.paginate():
            for gn in page.get('GlobalNetworks', []):
                gn_id = gn.get('GlobalNetworkId', '')
                gn_arn = gn.get('GlobalNetworkArn', '')
                tags = gn.get('Tags', [])
                global_networks.append(gn_id)
                resources.append(make_resource(
                    service='networkmanager',
                    resource_type='global-network',
                    resource_id=gn_id,
                    arn=gn_arn,
                    name=get_tag_value(tags, 'Name') or gn_id,
                    region='global',
                    details={
                        'state': gn.get('State', ''),
                        'description': gn.get('Description', ''),
                        'created_at': str(gn.get('CreatedAt', '')),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Core Networks ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_core_networks')
        for page in paginator.paginate():
            for cn in page.get('CoreNetworks', []):
                cn_id = cn.get('CoreNetworkId', '')
                cn_arn = cn.get('CoreNetworkArn', '')
                tags = cn.get('Tags', [])
                resources.append(make_resource(
                    service='networkmanager',
                    resource_type='core-network',
                    resource_id=cn_id,
                    arn=cn_arn,
                    name=get_tag_value(tags, 'Name') or cn_id,
                    region='global',
                    details={
                        'state': cn.get('State', ''),
                        'description': cn.get('Description', ''),
                        'global_network_id': cn.get('GlobalNetworkId', ''),
                        'edge_locations': cn.get('Edges', []),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Sites, Links, Devices (per global network) ───────────────────
    for gn_id in global_networks:
        # Sites
        try:
            paginator = client.get_paginator('get_sites')
            for page in paginator.paginate(GlobalNetworkId=gn_id):
                for site in page.get('Sites', []):
                    site_id = site.get('SiteId', '')
                    site_arn = site.get('SiteArn', '')
                    tags = site.get('Tags', [])
                    location = site.get('Location', {})
                    resources.append(make_resource(
                        service='networkmanager',
                        resource_type='site',
                        resource_id=site_id,
                        arn=site_arn,
                        name=get_tag_value(tags, 'Name') or site_id,
                        region='global',
                        details={
                            'state': site.get('State', ''),
                            'description': site.get('Description', ''),
                            'global_network_id': gn_id,
                            'location_address': location.get('Address', ''),
                            'location_latitude': location.get('Latitude', ''),
                            'location_longitude': location.get('Longitude', ''),
                            'created_at': str(site.get('CreatedAt', '')),
                        },
                        tags=tags_to_dict(tags),
                    ))
        except Exception:
            pass

        # Links
        try:
            paginator = client.get_paginator('get_links')
            for page in paginator.paginate(GlobalNetworkId=gn_id):
                for link in page.get('Links', []):
                    link_id = link.get('LinkId', '')
                    link_arn = link.get('LinkArn', '')
                    tags = link.get('Tags', [])
                    bandwidth = link.get('Bandwidth', {})
                    resources.append(make_resource(
                        service='networkmanager',
                        resource_type='link',
                        resource_id=link_id,
                        arn=link_arn,
                        name=get_tag_value(tags, 'Name') or link_id,
                        region='global',
                        details={
                            'state': link.get('State', ''),
                            'description': link.get('Description', ''),
                            'global_network_id': gn_id,
                            'site_id': link.get('SiteId', ''),
                            'type': link.get('Type', ''),
                            'provider': link.get('Provider', ''),
                            'upload_speed_mbps': bandwidth.get('UploadSpeed', 0),
                            'download_speed_mbps': bandwidth.get('DownloadSpeed', 0),
                            'created_at': str(link.get('CreatedAt', '')),
                        },
                        tags=tags_to_dict(tags),
                    ))
        except Exception:
            pass

        # Devices
        try:
            paginator = client.get_paginator('get_devices')
            for page in paginator.paginate(GlobalNetworkId=gn_id):
                for dev in page.get('Devices', []):
                    dev_id = dev.get('DeviceId', '')
                    dev_arn = dev.get('DeviceArn', '')
                    tags = dev.get('Tags', [])
                    location = dev.get('Location', {})
                    resources.append(make_resource(
                        service='networkmanager',
                        resource_type='device',
                        resource_id=dev_id,
                        arn=dev_arn,
                        name=get_tag_value(tags, 'Name') or dev_id,
                        region='global',
                        details={
                            'state': dev.get('State', ''),
                            'description': dev.get('Description', ''),
                            'global_network_id': gn_id,
                            'site_id': dev.get('SiteId', ''),
                            'type': dev.get('Type', ''),
                            'vendor': dev.get('Vendor', ''),
                            'model': dev.get('Model', ''),
                            'serial_number': dev.get('SerialNumber', ''),
                            'location_address': location.get('Address', ''),
                            'created_at': str(dev.get('CreatedAt', '')),
                        },
                        tags=tags_to_dict(tags),
                    ))
        except Exception:
            pass

    return resources
