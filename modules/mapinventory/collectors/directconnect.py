"""
Map Inventory — Direct Connect Collector
Resource types: connection, virtual-interface, direct-connect-gateway, lag
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_directconnect_resources(session, region, account_id):
    """Collect all Direct Connect resource types in the given region."""
    resources = []
    try:
        client = session.client('directconnect', region_name=region)
    except Exception:
        return resources

    # ── Connections ──────────────────────────────────────────────────
    try:
        resp = client.describe_connections()
        for conn in resp.get('connections', []):
            conn_id = conn.get('connectionId', '')
            conn_name = conn.get('connectionName', conn_id)
            arn = f"arn:aws:directconnect:{region}:{account_id}:dxcon/{conn_id}"
            tags = conn.get('tags', [])
            resources.append(make_resource(
                service='directconnect',
                resource_type='connection',
                resource_id=conn_id,
                arn=arn,
                name=conn_name,
                region=region,
                details={
                    'state': conn.get('connectionState', ''),
                    'bandwidth': conn.get('bandwidth', ''),
                    'location': conn.get('location', ''),
                    'vlan': conn.get('vlan', ''),
                    'partner_name': conn.get('partnerName', ''),
                    'lag_id': conn.get('lagId', ''),
                    'aws_device': conn.get('awsDevice', ''),
                    'has_logical_redundancy': conn.get('hasLogicalRedundancy', ''),
                    'provider_name': conn.get('providerName', ''),
                    'encryption_mode': conn.get('encryptionMode', ''),
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Virtual Interfaces ───────────────────────────────────────────
    try:
        resp = client.describe_virtual_interfaces()
        for vif in resp.get('virtualInterfaces', []):
            vif_id = vif.get('virtualInterfaceId', '')
            vif_name = vif.get('virtualInterfaceName', vif_id)
            arn = f"arn:aws:directconnect:{region}:{account_id}:dxvif/{vif_id}"
            tags = vif.get('tags', [])
            resources.append(make_resource(
                service='directconnect',
                resource_type='virtual-interface',
                resource_id=vif_id,
                arn=arn,
                name=vif_name,
                region=region,
                details={
                    'state': vif.get('virtualInterfaceState', ''),
                    'type': vif.get('virtualInterfaceType', ''),
                    'connection_id': vif.get('connectionId', ''),
                    'vlan': vif.get('vlan', ''),
                    'asn': vif.get('asn', ''),
                    'amazon_side_asn': vif.get('amazonSideAsn', ''),
                    'direct_connect_gateway_id': vif.get('directConnectGatewayId', ''),
                    'virtual_gateway_id': vif.get('virtualGatewayId', ''),
                    'mtu': vif.get('mtu', ''),
                    'jumbo_frame_capable': vif.get('jumboFrameCapable', False),
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Direct Connect Gateways ──────────────────────────────────────
    try:
        resp = client.describe_direct_connect_gateways()
        for gw in resp.get('directConnectGateways', []):
            gw_id = gw.get('directConnectGatewayId', '')
            gw_name = gw.get('directConnectGatewayName', gw_id)
            arn = f"arn:aws:directconnect::{account_id}:dx-gateway/{gw_id}"
            resources.append(make_resource(
                service='directconnect',
                resource_type='direct-connect-gateway',
                resource_id=gw_id,
                arn=arn,
                name=gw_name,
                region='global',
                details={
                    'state': gw.get('directConnectGatewayState', ''),
                    'amazon_side_asn': gw.get('amazonSideAsn', ''),
                    'owner_account': gw.get('ownerAccount', ''),
                    'stale_association_count': gw.get('staleAssociationCount', 0),
                },
                tags={},
            ))
    except Exception:
        pass

    # ── LAGs (Link Aggregation Groups) ───────────────────────────────
    try:
        resp = client.describe_lags()
        for lag in resp.get('lags', []):
            lag_id = lag.get('lagId', '')
            lag_name = lag.get('lagName', lag_id)
            arn = f"arn:aws:directconnect:{region}:{account_id}:dxlag/{lag_id}"
            tags = lag.get('tags', [])
            resources.append(make_resource(
                service='directconnect',
                resource_type='lag',
                resource_id=lag_id,
                arn=arn,
                name=lag_name,
                region=region,
                details={
                    'state': lag.get('lagState', ''),
                    'location': lag.get('location', ''),
                    'bandwidth': lag.get('connectionsBandwidth', ''),
                    'minimum_links': lag.get('minimumLinks', 0),
                    'number_of_connections': lag.get('numberOfConnections', 0),
                    'aws_device': lag.get('awsDevice', ''),
                    'has_logical_redundancy': lag.get('hasLogicalRedundancy', ''),
                    'encryption_mode': lag.get('encryptionMode', ''),
                    'provider_name': lag.get('providerName', ''),
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    return resources
