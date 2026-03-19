"""
Map Inventory — Global Accelerator Collector (GLOBAL - us-west-2)
Resource types: accelerator, listener, endpoint-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_globalaccelerator_resources(session, region, account_id):
    """Collect all Global Accelerator resource types (global, via us-west-2)."""
    resources = []
    try:
        client = session.client('globalaccelerator', region_name='us-west-2')
    except Exception:
        return resources

    # ── Accelerators ─────────────────────────────────────────────────
    accelerators = []
    try:
        paginator = client.get_paginator('list_accelerators')
        for page in paginator.paginate():
            for acc in page.get('Accelerators', []):
                acc_arn = acc.get('AcceleratorArn', '')
                acc_name = acc.get('Name', '')
                accelerators.append(acc_arn)
                # Fetch tags
                acc_tags = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=acc_arn)
                    acc_tags = tag_resp.get('Tags', [])
                except Exception:
                    pass
                ip_sets = acc.get('IpSets', [])
                ip_addresses = []
                for ip_set in ip_sets:
                    ip_addresses.extend(ip_set.get('IpAddresses', []))
                resources.append(make_resource(
                    service='globalaccelerator',
                    resource_type='accelerator',
                    resource_id=acc_arn.split('/')[-1] if '/' in acc_arn else acc_name,
                    arn=acc_arn,
                    name=acc_name,
                    region='global',
                    details={
                        'status': acc.get('Status', ''),
                        'enabled': acc.get('Enabled', False),
                        'ip_address_type': acc.get('IpAddressType', ''),
                        'ip_addresses': ip_addresses,
                        'dns_name': acc.get('DnsName', ''),
                        'created_at': str(acc.get('CreatedTime', '')),
                        'last_modified': str(acc.get('LastModifiedTime', '')),
                    },
                    tags=tags_to_dict(acc_tags),
                ))
    except Exception:
        pass

    # ── Listeners (per accelerator) ──────────────────────────────────
    for acc_arn in accelerators:
        try:
            paginator = client.get_paginator('list_listeners')
            for page in paginator.paginate(AcceleratorArn=acc_arn):
                for listener in page.get('Listeners', []):
                    listener_arn = listener.get('ListenerArn', '')
                    port_ranges = listener.get('PortRanges', [])
                    port_desc = ', '.join(
                        f"{pr.get('FromPort', '')}-{pr.get('ToPort', '')}"
                        for pr in port_ranges
                    )
                    resources.append(make_resource(
                        service='globalaccelerator',
                        resource_type='listener',
                        resource_id=listener_arn.split('/')[-1] if '/' in listener_arn else listener_arn,
                        arn=listener_arn,
                        name=f"Listener ({port_desc})",
                        region='global',
                        details={
                            'accelerator_arn': acc_arn,
                            'protocol': listener.get('Protocol', ''),
                            'port_ranges': port_ranges,
                            'client_affinity': listener.get('ClientAffinity', ''),
                        },
                        tags={},
                    ))

                    # ── Endpoint Groups (per listener) ───────────────
                    try:
                        eg_paginator = client.get_paginator('list_endpoint_groups')
                        for eg_page in eg_paginator.paginate(ListenerArn=listener_arn):
                            for eg in eg_page.get('EndpointGroups', []):
                                eg_arn = eg.get('EndpointGroupArn', '')
                                eg_region = eg.get('EndpointGroupRegion', '')
                                endpoints = eg.get('EndpointDescriptions', [])
                                resources.append(make_resource(
                                    service='globalaccelerator',
                                    resource_type='endpoint-group',
                                    resource_id=eg_arn.split('/')[-1] if '/' in eg_arn else eg_arn,
                                    arn=eg_arn,
                                    name=f"EndpointGroup ({eg_region})",
                                    region='global',
                                    details={
                                        'listener_arn': listener_arn,
                                        'endpoint_group_region': eg_region,
                                        'traffic_dial_percentage': eg.get(
                                            'TrafficDialPercentage', 100),
                                        'health_check_port': eg.get('HealthCheckPort', ''),
                                        'health_check_protocol': eg.get(
                                            'HealthCheckProtocol', ''),
                                        'health_check_path': eg.get('HealthCheckPath', ''),
                                        'health_check_interval': eg.get(
                                            'HealthCheckIntervalSeconds', ''),
                                        'threshold_count': eg.get('ThresholdCount', ''),
                                        'endpoint_count': len(endpoints),
                                        'endpoints': [
                                            {
                                                'endpoint_id': ep.get('EndpointId', ''),
                                                'weight': ep.get('Weight', 0),
                                                'health_state': ep.get('HealthState', ''),
                                            }
                                            for ep in endpoints
                                        ],
                                    },
                                    tags={},
                                ))
                    except Exception:
                        pass
        except Exception:
            pass

    return resources
