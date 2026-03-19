"""
Map Inventory — VPC Collector
Resource types: vpc, subnet, route-table, internet-gateway, nat-gateway,
                vpc-endpoint, vpc-peering, transit-gateway,
                transit-gateway-attachment, dhcp-options, network-acl
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_vpc_resources(session, region, account_id):
    """Collect all VPC-related resources in the given region."""
    resources = []
    try:
        ec2 = session.client('ec2', region_name=region)
    except Exception:
        return resources

    # Track default VPC IDs and default DHCP option IDs for is_default flagging
    default_vpc_ids = set()
    default_dhcp_ids = set()

    # ── VPCs ───────────────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_vpcs')
        for page in paginator.paginate():
            for vpc in page.get('Vpcs', []):
                vpc_id = vpc['VpcId']
                tags = vpc.get('Tags', [])
                name = get_tag_value(tags, 'Name') or vpc_id
                is_default = vpc.get('IsDefault', False)
                arn = f"arn:aws:ec2:{region}:{account_id}:vpc/{vpc_id}"

                if is_default:
                    default_vpc_ids.add(vpc_id)
                    dhcp_id = vpc.get('DhcpOptionsId', '')
                    if dhcp_id:
                        default_dhcp_ids.add(dhcp_id)

                resources.append(make_resource(
                    service='vpc',
                    resource_type='vpc',
                    resource_id=vpc_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'cidr_block': vpc.get('CidrBlock', ''),
                        'state': vpc.get('State', ''),
                        'dhcp_options_id': vpc.get('DhcpOptionsId', ''),
                        'instance_tenancy': vpc.get('InstanceTenancy', ''),
                        'is_default': is_default,
                    },
                    tags=tags_to_dict(tags),
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Subnets ────────────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_subnets')
        for page in paginator.paginate():
            for subnet in page.get('Subnets', []):
                subnet_id = subnet['SubnetId']
                tags = subnet.get('Tags', [])
                name = get_tag_value(tags, 'Name') or subnet_id
                is_default = subnet.get('DefaultForAz', False)
                arn = subnet.get('SubnetArn', f"arn:aws:ec2:{region}:{account_id}:subnet/{subnet_id}")
                resources.append(make_resource(
                    service='vpc',
                    resource_type='subnet',
                    resource_id=subnet_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'vpc_id': subnet.get('VpcId', ''),
                        'cidr_block': subnet.get('CidrBlock', ''),
                        'availability_zone': subnet.get('AvailabilityZone', ''),
                        'available_ips': subnet.get('AvailableIpAddressCount', 0),
                        'map_public_ip': subnet.get('MapPublicIpOnLaunch', False),
                        'state': subnet.get('State', ''),
                    },
                    tags=tags_to_dict(tags),
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Route Tables ───────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_route_tables')
        for page in paginator.paginate():
            for rt in page.get('RouteTables', []):
                rt_id = rt['RouteTableId']
                tags = rt.get('Tags', [])
                name = get_tag_value(tags, 'Name') or rt_id
                vpc_id = rt.get('VpcId', '')
                arn = f"arn:aws:ec2:{region}:{account_id}:route-table/{rt_id}"

                # Check if this is the main route table
                is_main = any(
                    assoc.get('Main', False)
                    for assoc in rt.get('Associations', [])
                )
                is_default = (vpc_id in default_vpc_ids) and is_main

                resources.append(make_resource(
                    service='vpc',
                    resource_type='route-table',
                    resource_id=rt_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'vpc_id': vpc_id,
                        'is_main': is_main,
                        'routes_count': len(rt.get('Routes', [])),
                        'associations_count': len(rt.get('Associations', [])),
                    },
                    tags=tags_to_dict(tags),
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Internet Gateways ──────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_internet_gateways')
        for page in paginator.paginate():
            for igw in page.get('InternetGateways', []):
                igw_id = igw['InternetGatewayId']
                tags = igw.get('Tags', [])
                name = get_tag_value(tags, 'Name') or igw_id
                arn = f"arn:aws:ec2:{region}:{account_id}:internet-gateway/{igw_id}"

                attached_vpcs = [
                    att.get('VpcId', '')
                    for att in igw.get('Attachments', [])
                ]
                is_default = any(v in default_vpc_ids for v in attached_vpcs)

                resources.append(make_resource(
                    service='vpc',
                    resource_type='internet-gateway',
                    resource_id=igw_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'attached_vpcs': attached_vpcs,
                        'state': igw.get('Attachments', [{}])[0].get('State', '') if igw.get('Attachments') else '',
                    },
                    tags=tags_to_dict(tags),
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── NAT Gateways ───────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_nat_gateways')
        for page in paginator.paginate():
            for ngw in page.get('NatGateways', []):
                state = ngw.get('State', '')
                if state == 'deleted':
                    continue
                ngw_id = ngw['NatGatewayId']
                tags = ngw.get('Tags', [])
                name = get_tag_value(tags, 'Name') or ngw_id
                arn = f"arn:aws:ec2:{region}:{account_id}:natgateway/{ngw_id}"
                resources.append(make_resource(
                    service='vpc',
                    resource_type='nat-gateway',
                    resource_id=ngw_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'vpc_id': ngw.get('VpcId', ''),
                        'subnet_id': ngw.get('SubnetId', ''),
                        'state': state,
                        'connectivity_type': ngw.get('ConnectivityType', ''),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── VPC Endpoints ──────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_vpc_endpoints')
        for page in paginator.paginate():
            for ep in page.get('VpcEndpoints', []):
                ep_id = ep['VpcEndpointId']
                tags = ep.get('Tags', [])
                name = get_tag_value(tags, 'Name') or ep_id
                arn = f"arn:aws:ec2:{region}:{account_id}:vpc-endpoint/{ep_id}"
                resources.append(make_resource(
                    service='vpc',
                    resource_type='vpc-endpoint',
                    resource_id=ep_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'vpc_id': ep.get('VpcId', ''),
                        'service_name': ep.get('ServiceName', ''),
                        'state': ep.get('State', ''),
                        'type': ep.get('VpcEndpointType', ''),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── VPC Peering Connections ────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_vpc_peering_connections')
        for page in paginator.paginate():
            for pcx in page.get('VpcPeeringConnections', []):
                status_code = pcx.get('Status', {}).get('Code', '')
                if status_code in ('deleted', 'rejected', 'failed'):
                    continue
                pcx_id = pcx['VpcPeeringConnectionId']
                tags = pcx.get('Tags', [])
                name = get_tag_value(tags, 'Name') or pcx_id
                arn = f"arn:aws:ec2:{region}:{account_id}:vpc-peering-connection/{pcx_id}"
                resources.append(make_resource(
                    service='vpc',
                    resource_type='vpc-peering',
                    resource_id=pcx_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'requester_vpc': pcx.get('RequesterVpcInfo', {}).get('VpcId', ''),
                        'accepter_vpc': pcx.get('AccepterVpcInfo', {}).get('VpcId', ''),
                        'status': status_code,
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Transit Gateways ───────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_transit_gateways')
        for page in paginator.paginate():
            for tgw in page.get('TransitGateways', []):
                if tgw.get('OwnerId', '') != account_id:
                    continue
                tgw_id = tgw['TransitGatewayId']
                tags = tgw.get('Tags', [])
                name = get_tag_value(tags, 'Name') or tgw_id
                tgw_arn = tgw.get('TransitGatewayArn', f"arn:aws:ec2:{region}:{account_id}:transit-gateway/{tgw_id}")
                resources.append(make_resource(
                    service='vpc',
                    resource_type='transit-gateway',
                    resource_id=tgw_id,
                    arn=tgw_arn,
                    name=name,
                    region=region,
                    details={
                        'state': tgw.get('State', ''),
                        'description': tgw.get('Description', ''),
                        'amazon_side_asn': tgw.get('Options', {}).get('AmazonSideAsn', ''),
                        'auto_accept_shared': tgw.get('Options', {}).get('AutoAcceptSharedAttachments', ''),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Transit Gateway Attachments ────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_transit_gateway_attachments')
        for page in paginator.paginate():
            for att in page.get('TransitGatewayAttachments', []):
                att_id = att['TransitGatewayAttachmentId']
                tags = att.get('Tags', [])
                name = get_tag_value(tags, 'Name') or att_id
                arn = f"arn:aws:ec2:{region}:{account_id}:transit-gateway-attachment/{att_id}"
                resources.append(make_resource(
                    service='vpc',
                    resource_type='transit-gateway-attachment',
                    resource_id=att_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'transit_gateway_id': att.get('TransitGatewayId', ''),
                        'resource_type': att.get('ResourceType', ''),
                        'resource_id': att.get('ResourceId', ''),
                        'state': att.get('State', ''),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── DHCP Options ───────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_dhcp_options')
        for page in paginator.paginate():
            for dhcp in page.get('DhcpOptions', []):
                dhcp_id = dhcp['DhcpOptionsId']
                tags = dhcp.get('Tags', [])
                name = get_tag_value(tags, 'Name') or dhcp_id
                is_default = dhcp_id in default_dhcp_ids
                arn = f"arn:aws:ec2:{region}:{account_id}:dhcp-options/{dhcp_id}"

                # Parse DHCP configurations
                configs = {}
                for cfg in dhcp.get('DhcpConfigurations', []):
                    key = cfg.get('Key', '')
                    values = [v.get('Value', '') for v in cfg.get('Values', [])]
                    configs[key] = values

                resources.append(make_resource(
                    service='vpc',
                    resource_type='dhcp-options',
                    resource_id=dhcp_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'configurations': configs,
                    },
                    tags=tags_to_dict(tags),
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Network ACLs ───────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_network_acls')
        for page in paginator.paginate():
            for nacl in page.get('NetworkAcls', []):
                nacl_id = nacl['NetworkAclId']
                tags = nacl.get('Tags', [])
                name = get_tag_value(tags, 'Name') or nacl_id
                is_default = nacl.get('IsDefault', False)
                arn = f"arn:aws:ec2:{region}:{account_id}:network-acl/{nacl_id}"
                resources.append(make_resource(
                    service='vpc',
                    resource_type='network-acl',
                    resource_id=nacl_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'vpc_id': nacl.get('VpcId', ''),
                        'is_default': is_default,
                        'entries_count': len(nacl.get('Entries', [])),
                        'associations_count': len(nacl.get('Associations', [])),
                    },
                    tags=tags_to_dict(tags),
                    is_default=is_default,
                ))
    except Exception:
        pass

    return resources
