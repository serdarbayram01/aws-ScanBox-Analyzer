"""
Map Inventory — Directory Service Collector
Resource types: directory
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ds_resources(session, region, account_id):
    """Collect all Directory Service directories in the given region."""
    resources = []
    try:
        client = session.client('ds', region_name=region)
    except Exception:
        return resources

    # ── Directories ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_directories')
        for page in paginator.paginate():
            for d in page.get('DirectoryDescriptions', []):
                dir_id = d.get('DirectoryId', '')
                dir_name = d.get('Name', dir_id)
                arn = f"arn:aws:ds:{region}:{account_id}:directory/{dir_id}"
                # Fetch tags
                dir_tags = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceId=dir_id)
                    dir_tags = tag_resp.get('Tags', [])
                except Exception:
                    pass
                vpc_settings = d.get('VpcSettings', {})
                resources.append(make_resource(
                    service='ds',
                    resource_type='directory',
                    resource_id=dir_id,
                    arn=arn,
                    name=dir_name,
                    region=region,
                    details={
                        'short_name': d.get('ShortName', ''),
                        'type': d.get('Type', ''),
                        'size': d.get('Size', ''),
                        'edition': d.get('Edition', ''),
                        'stage': d.get('Stage', ''),
                        'launch_time': str(d.get('LaunchTime', '')),
                        'dns_ip_addrs': d.get('DnsIpAddrs', []),
                        'vpc_id': vpc_settings.get('VpcId', ''),
                        'subnet_ids': vpc_settings.get('SubnetIds', []),
                        'availability_zones': vpc_settings.get('AvailabilityZones', []),
                        'access_url': d.get('AccessUrl', ''),
                        'sso_enabled': d.get('SsoEnabled', False),
                        'description': d.get('Description', ''),
                    },
                    tags=tags_to_dict(dir_tags),
                ))
    except Exception:
        pass

    return resources
