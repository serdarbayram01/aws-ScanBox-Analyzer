"""
Topology Module — Network Topology Collector
Collects VPC architecture data from AWS accounts for topology visualization.
Runs all collectors in parallel threads, aggregates network topology results.
"""

import concurrent.futures
import logging
import threading
import time
from datetime import datetime, timezone

_logger = logging.getLogger('topology.collector')

TASK_TIMEOUT = 30

# Global services (called once, not per-region)
GLOBAL_SERVICES = ['s3', 'cloudfront', 'organizations', 'route53']

# All topology-relevant services to collect
SERVICES_ORDER = [
    'vpc', 'subnet', 'igw', 'nat', 'route_table', 'peering',
    'security_group', 'nacl', 'vpc_endpoint', 'eip', 'eni',
    'ec2', 'ecs', 'rds', 'elb', 'lambda',
    'eks', 'api_gateway', 'network_firewall',
    'transit_gateway', 'direct_connect',
    'vpn', 'acm',
    'cloudfront', 's3', 'route53', 'organizations',
]

# View level mapping
VIEW_LEVELS = {
    'basic':    ['vpc', 'subnet', 'igw', 'nat', 'route_table', 'peering'],
    'medium':   ['vpc', 'subnet', 'igw', 'nat', 'route_table', 'peering',
                 'security_group', 'nacl', 'vpc_endpoint', 'eip'],
    'detailed': SERVICES_ORDER,
}


def get_enabled_regions(session):
    """Get list of enabled regions for the account."""
    try:
        ec2 = session.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions(
            Filters=[{'Name': 'opt-in-status', 'Values': ['opt-in-not-required', 'opted-in']}]
        )['Regions']
        return sorted([r['RegionName'] for r in regions])
    except Exception:
        return ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                'eu-west-1', 'eu-west-2', 'eu-central-1',
                'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1']


# ---------------------------------------------------------------------------
# Individual collectors
# ---------------------------------------------------------------------------

def _collect_vpcs(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    vpcs = ec2.describe_vpcs()['Vpcs']
    results = []
    for v in vpcs:
        tags = {t['Key']: t['Value'] for t in v.get('Tags', [])}
        results.append({
            'type': 'vpc',
            'id': v['VpcId'],
            'name': tags.get('Name', v['VpcId']),
            'region': region,
            'cidr': v['CidrBlock'],
            'is_default': v.get('IsDefault', False),
            'state': v.get('State', 'unknown'),
            'cidrs': [a['CidrBlock'] for a in v.get('CidrBlockAssociationSet', [])],
            'ipv6_cidrs': [a['Ipv6CidrBlock'] for a in v.get('Ipv6CidrBlockAssociationSet', []) if 'Ipv6CidrBlock' in a],
            'tags': tags,
        })
    return results


def _collect_subnets(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    subnets = []
    paginator = ec2.get_paginator('describe_subnets')
    for page in paginator.paginate():
        subnets.extend(page.get('Subnets', []))
    results = []
    for s in subnets:
        tags = {t['Key']: t['Value'] for t in s.get('Tags', [])}
        results.append({
            'type': 'subnet',
            'id': s['SubnetId'],
            'name': tags.get('Name', s['SubnetId']),
            'region': region,
            'vpc_id': s['VpcId'],
            'az': s['AvailabilityZone'],
            'cidr': s['CidrBlock'],
            'available_ips': s.get('AvailableIpAddressCount', 0),
            'map_public_ip': s.get('MapPublicIpOnLaunch', False),
            'is_public': False,  # will be determined by route table analysis
            'tags': tags,
        })
    return results


def _collect_igws(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    igws = ec2.describe_internet_gateways()['InternetGateways']
    results = []
    for igw in igws:
        tags = {t['Key']: t['Value'] for t in igw.get('Tags', [])}
        vpc_ids = [a['VpcId'] for a in igw.get('Attachments', []) if a.get('State') == 'available']
        results.append({
            'type': 'igw',
            'id': igw['InternetGatewayId'],
            'name': tags.get('Name', igw['InternetGatewayId']),
            'region': region,
            'vpc_id': vpc_ids[0] if vpc_ids else None,
            'tags': tags,
        })
    return results


def _collect_nat_gateways(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    nats = ec2.describe_nat_gateways(
        Filter=[{'Name': 'state', 'Values': ['available', 'pending']}]
    )['NatGateways']
    results = []
    for n in nats:
        tags = {t['Key']: t['Value'] for t in n.get('Tags', [])}
        public_ip = None
        for addr in n.get('NatGatewayAddresses', []):
            if addr.get('PublicIp'):
                public_ip = addr['PublicIp']
                break
        results.append({
            'type': 'nat',
            'id': n['NatGatewayId'],
            'name': tags.get('Name', n['NatGatewayId']),
            'region': region,
            'vpc_id': n.get('VpcId'),
            'subnet_id': n.get('SubnetId'),
            'state': n.get('State', 'unknown'),
            'connectivity': n.get('ConnectivityType', 'public'),
            'public_ip': public_ip,
            'tags': tags,
        })
    return results


def _collect_route_tables(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    rts = ec2.describe_route_tables()['RouteTables']
    results = []
    for rt in rts:
        tags = {t['Key']: t['Value'] for t in rt.get('Tags', [])}
        associations = []
        for a in rt.get('Associations', []):
            associations.append({
                'id': a.get('RouteTableAssociationId'),
                'subnet_id': a.get('SubnetId'),
                'main': a.get('Main', False),
            })
        routes = []
        has_igw_route = False
        for r in rt.get('Routes', []):
            route = {
                'destination': r.get('DestinationCidrBlock') or r.get('DestinationIpv6CidrBlock', ''),
                'target': r.get('GatewayId') or r.get('NatGatewayId') or r.get('TransitGatewayId') or
                          r.get('VpcPeeringConnectionId') or r.get('NetworkInterfaceId') or
                          r.get('InstanceId') or 'local',
                'state': r.get('State', 'active'),
            }
            if r.get('GatewayId', '').startswith('igw-'):
                has_igw_route = True
            routes.append(route)
        results.append({
            'type': 'route_table',
            'id': rt['RouteTableId'],
            'name': tags.get('Name', rt['RouteTableId']),
            'region': region,
            'vpc_id': rt['VpcId'],
            'associations': associations,
            'routes': routes,
            'has_igw_route': has_igw_route,
            'tags': tags,
        })
    return results


def _collect_peering(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    peerings = ec2.describe_vpc_peering_connections(
        Filters=[{'Name': 'status-code', 'Values': ['active', 'pending-acceptance', 'provisioning']}]
    )['VpcPeeringConnections']
    results = []
    for p in peerings:
        tags = {t['Key']: t['Value'] for t in p.get('Tags', [])}
        req = p.get('RequesterVpcInfo', {})
        acc = p.get('AccepterVpcInfo', {})
        results.append({
            'type': 'peering',
            'id': p['VpcPeeringConnectionId'],
            'name': tags.get('Name', p['VpcPeeringConnectionId']),
            'region': region,
            'status': p.get('Status', {}).get('Code', 'unknown'),
            'requester_vpc_id': req.get('VpcId'),
            'requester_account': req.get('OwnerId'),
            'requester_cidr': req.get('CidrBlock'),
            'requester_region': req.get('Region', region),
            'accepter_vpc_id': acc.get('VpcId'),
            'accepter_account': acc.get('OwnerId'),
            'accepter_cidr': acc.get('CidrBlock'),
            'accepter_region': acc.get('Region'),
            'is_cross_account': req.get('OwnerId') != acc.get('OwnerId'),
            'tags': tags,
        })
    return results


def _collect_security_groups(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    sgs = []
    paginator = ec2.get_paginator('describe_security_groups')
    for page in paginator.paginate():
        sgs.extend(page.get('SecurityGroups', []))
    results = []
    for sg in sgs:
        tags = {t['Key']: t['Value'] for t in sg.get('Tags', [])}
        inbound_rules = []
        for rule in sg.get('IpPermissions', []):
            for cidr in rule.get('IpRanges', []):
                inbound_rules.append({
                    'protocol': rule.get('IpProtocol', '-1'),
                    'from_port': rule.get('FromPort', 0),
                    'to_port': rule.get('ToPort', 0),
                    'source': cidr.get('CidrIp', ''),
                })
            for cidr in rule.get('Ipv6Ranges', []):
                inbound_rules.append({
                    'protocol': rule.get('IpProtocol', '-1'),
                    'from_port': rule.get('FromPort', 0),
                    'to_port': rule.get('ToPort', 0),
                    'source': cidr.get('CidrIpv6', ''),
                })
            for group in rule.get('UserIdGroupPairs', []):
                inbound_rules.append({
                    'protocol': rule.get('IpProtocol', '-1'),
                    'from_port': rule.get('FromPort', 0),
                    'to_port': rule.get('ToPort', 0),
                    'source': group.get('GroupId', ''),
                    'source_group': True,
                })
        results.append({
            'type': 'security_group',
            'id': sg['GroupId'],
            'name': sg.get('GroupName', sg['GroupId']),
            'region': region,
            'vpc_id': sg.get('VpcId'),
            'description': sg.get('Description', ''),
            'inbound_rules_count': len(sg.get('IpPermissions', [])),
            'outbound_rules_count': len(sg.get('IpPermissionsEgress', [])),
            'inbound_rules': inbound_rules[:50],
            'is_default': sg.get('GroupName') == 'default',
            'tags': tags,
        })
    return results


def _collect_nacls(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    nacls = []
    paginator = ec2.get_paginator('describe_network_acls')
    for page in paginator.paginate():
        nacls.extend(page.get('NetworkAcls', []))
    results = []
    for nacl in nacls:
        tags = {t['Key']: t['Value'] for t in nacl.get('Tags', [])}
        subnet_ids = [a['SubnetId'] for a in nacl.get('Associations', []) if 'SubnetId' in a]
        results.append({
            'type': 'nacl',
            'id': nacl['NetworkAclId'],
            'name': tags.get('Name', nacl['NetworkAclId']),
            'region': region,
            'vpc_id': nacl.get('VpcId'),
            'is_default': nacl.get('IsDefault', False),
            'subnet_ids': subnet_ids,
            'entries_count': len(nacl.get('Entries', [])),
            'tags': tags,
        })
    return results


def _collect_vpc_endpoints(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    endpoints = []
    paginator = ec2.get_paginator('describe_vpc_endpoints')
    for page in paginator.paginate():
        endpoints.extend(page.get('VpcEndpoints', []))
    results = []
    for ep in endpoints:
        tags = {t['Key']: t['Value'] for t in ep.get('Tags', [])}
        results.append({
            'type': 'vpc_endpoint',
            'id': ep['VpcEndpointId'],
            'name': tags.get('Name', ep['VpcEndpointId']),
            'region': region,
            'vpc_id': ep.get('VpcId'),
            'service_name': ep.get('ServiceName', ''),
            'endpoint_type': ep.get('VpcEndpointType', 'Gateway'),
            'state': ep.get('State', 'unknown'),
            'subnet_ids': ep.get('SubnetIds', []),
            'route_table_ids': ep.get('RouteTableIds', []),
            'tags': tags,
        })
    return results


def _collect_eips(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    addresses = ec2.describe_addresses()['Addresses']
    results = []
    for addr in addresses:
        tags = {t['Key']: t['Value'] for t in addr.get('Tags', [])}
        results.append({
            'type': 'eip',
            'id': addr.get('AllocationId', addr.get('PublicIp', '')),
            'name': tags.get('Name', addr.get('PublicIp', '')),
            'region': region,
            'public_ip': addr.get('PublicIp'),
            'private_ip': addr.get('PrivateIpAddress'),
            'instance_id': addr.get('InstanceId'),
            'network_interface_id': addr.get('NetworkInterfaceId'),
            'association_id': addr.get('AssociationId'),
            'tags': tags,
        })
    return results


def _collect_ec2(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    reservations = []
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate():
        reservations.extend(page.get('Reservations', []))
    results = []
    for r in reservations:
        for i in r['Instances']:
            tags = {t['Key']: t['Value'] for t in i.get('Tags', [])}
            sgs = [{'id': sg['GroupId'], 'name': sg['GroupName']} for sg in i.get('SecurityGroups', [])]
            results.append({
                'type': 'ec2',
                'id': i['InstanceId'],
                'name': tags.get('Name', i['InstanceId']),
                'region': region,
                'vpc_id': i.get('VpcId'),
                'subnet_id': i.get('SubnetId'),
                'az': i.get('Placement', {}).get('AvailabilityZone'),
                'instance_type': i.get('InstanceType'),
                'state': i.get('State', {}).get('Name', 'unknown'),
                'private_ip': i.get('PrivateIpAddress'),
                'public_ip': i.get('PublicIpAddress'),
                'security_groups': sgs,
                'tags': tags,
            })
    return results


def _collect_rds(session, region, account_id):
    rds = session.client('rds', region_name=region)
    instances = rds.describe_db_instances()['DBInstances']
    results = []
    for db in instances:
        vpc_sgs = [{'id': sg['VpcSecurityGroupId'], 'status': sg['Status']}
                   for sg in db.get('VpcSecurityGroups', [])]
        subnets = []
        subnet_group = db.get('DBSubnetGroup', {})
        if subnet_group:
            subnets = [s['SubnetIdentifier'] for s in subnet_group.get('Subnets', [])]
        result = {
            'type': 'rds',
            'id': db['DBInstanceIdentifier'],
            'name': db['DBInstanceIdentifier'],
            'region': region,
            'vpc_id': subnet_group.get('VpcId'),
            'subnet_ids': subnets,
            'az': db.get('AvailabilityZone'),
            'engine': db.get('Engine'),
            'instance_class': db.get('DBInstanceClass'),
            'state': db.get('DBInstanceStatus', 'unknown'),
            'multi_az': db.get('MultiAZ', False),
            'publicly_accessible': db.get('PubliclyAccessible', False),
            'security_groups': vpc_sgs,
            'endpoint': db.get('Endpoint', {}).get('Address'),
            'port': db.get('Endpoint', {}).get('Port'),
            'tags': {},
        }
        try:
            tag_list = rds.list_tags_for_resource(ResourceName=db['DBInstanceArn'])['TagList']
            result['tags'] = {t['Key']: t['Value'] for t in tag_list}
        except Exception as exc:
            _logger.warning('%s failed: %s', '_collect_rds', exc)
        results.append(result)
    return results


def _collect_elb(session, region, account_id):
    results = []
    # ALB/NLB (ELBv2)
    try:
        elbv2 = session.client('elbv2', region_name=region)
        lbs = []
        paginator = elbv2.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            lbs.extend(page.get('LoadBalancers', []))
        for lb in lbs:
            azs = [{'zone': az['ZoneName'], 'subnet_id': az.get('SubnetId')}
                   for az in lb.get('AvailabilityZones', [])]
            results.append({
                'type': 'elb',
                'id': lb['LoadBalancerArn'].split('/')[-1],
                'arn': lb['LoadBalancerArn'],
                'name': lb.get('LoadBalancerName', ''),
                'region': region,
                'vpc_id': lb.get('VpcId'),
                'lb_type': lb.get('Type', 'application'),
                'scheme': lb.get('Scheme', 'internet-facing'),
                'state': lb.get('State', {}).get('Code', 'unknown'),
                'dns_name': lb.get('DNSName'),
                'availability_zones': azs,
                'subnet_ids': [az.get('SubnetId') for az in lb.get('AvailabilityZones', []) if az.get('SubnetId')],
                'security_groups': lb.get('SecurityGroups', []),
                'tags': {},
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_elb', exc)
    # Classic ELB
    try:
        elb_classic = session.client('elb', region_name=region)
        classic_lbs = []
        paginator = elb_classic.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            classic_lbs.extend(page.get('LoadBalancerDescriptions', []))
        for lb in classic_lbs:
            results.append({
                'type': 'elb',
                'id': lb['LoadBalancerName'],
                'name': lb['LoadBalancerName'],
                'region': region,
                'vpc_id': lb.get('VPCId'),
                'lb_type': 'classic',
                'scheme': lb.get('Scheme', 'internet-facing'),
                'state': 'active',
                'dns_name': lb.get('DNSName'),
                'availability_zones': [{'zone': az} for az in lb.get('AvailabilityZones', [])],
                'subnet_ids': lb.get('Subnets', []),
                'security_groups': lb.get('SecurityGroups', []),
                'tags': {},
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', 'unknown', exc)
    return results


def _collect_lambda(session, region, account_id):
    lam = session.client('lambda', region_name=region)
    functions = []
    paginator = lam.get_paginator('list_functions')
    for page in paginator.paginate():
        functions.extend(page.get('Functions', []))
    results = []
    for fn in functions:
        vpc_config = fn.get('VpcConfig', {})
        if not vpc_config.get('VpcId'):
            continue  # Only collect VPC-attached lambdas for topology
        results.append({
            'type': 'lambda',
            'id': fn['FunctionName'],
            'name': fn['FunctionName'],
            'region': region,
            'vpc_id': vpc_config.get('VpcId'),
            'subnet_ids': vpc_config.get('SubnetIds', []),
            'security_groups': vpc_config.get('SecurityGroupIds', []),
            'runtime': fn.get('Runtime', 'unknown'),
            'memory': fn.get('MemorySize'),
            'tags': {},
        })
    return results


def _collect_transit_gateways(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    results = []
    try:
        tgws = ec2.describe_transit_gateways()['TransitGateways']
        for tgw in tgws:
            tags = {t['Key']: t['Value'] for t in tgw.get('Tags', [])}
            results.append({
                'type': 'transit_gateway',
                'id': tgw['TransitGatewayId'],
                'name': tags.get('Name', tgw['TransitGatewayId']),
                'region': region,
                'state': tgw.get('State', 'unknown'),
                'owner_id': tgw.get('OwnerId'),
                'asn': tgw.get('Options', {}).get('AmazonSideAsn'),
                'tags': tags,
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_transit_gateways', exc)
    # TGW attachments
    try:
        attachments = ec2.describe_transit_gateway_attachments()['TransitGatewayAttachments']
        for att in attachments:
            tags = {t['Key']: t['Value'] for t in att.get('Tags', [])}
            results.append({
                'type': 'tgw_attachment',
                'id': att['TransitGatewayAttachmentId'],
                'name': tags.get('Name', att['TransitGatewayAttachmentId']),
                'region': region,
                'tgw_id': att.get('TransitGatewayId'),
                'resource_type': att.get('ResourceType'),
                'resource_id': att.get('ResourceId'),
                'resource_owner': att.get('ResourceOwnerId'),
                'state': att.get('State', 'unknown'),
                'tags': tags,
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_transit_gateways', exc)
    return results


def _collect_direct_connect(session, region, account_id):
    dx = session.client('directconnect', region_name=region)
    results = []
    try:
        connections = dx.describe_connections()['connections']
        for conn in connections:
            results.append({
                'type': 'direct_connect',
                'id': conn['connectionId'],
                'name': conn.get('connectionName', conn['connectionId']),
                'region': region,
                'state': conn.get('connectionState', 'unknown'),
                'bandwidth': conn.get('bandwidth'),
                'location': conn.get('location'),
                'vlan': conn.get('vlan'),
                'tags': {},
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_direct_connect', exc)
    try:
        vgws = dx.describe_virtual_gateways()['virtualGateways']
        for vgw in vgws:
            results.append({
                'type': 'dx_gateway',
                'id': vgw['virtualGatewayId'],
                'name': vgw['virtualGatewayId'],
                'region': region,
                'state': vgw.get('virtualGatewayState', 'unknown'),
                'tags': {},
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_direct_connect', exc)
    return results


def _collect_acm(session, region, account_id):
    acm = session.client('acm', region_name=region)
    certs = acm.list_certificates()['CertificateSummaryList']
    results = []
    for cert in certs:
        results.append({
            'type': 'acm',
            'id': cert['CertificateArn'].split('/')[-1],
            'arn': cert['CertificateArn'],
            'name': cert.get('DomainName', ''),
            'region': region,
            'domain': cert.get('DomainName'),
            'status': cert.get('Status', 'unknown'),
            'type_': cert.get('Type', 'unknown'),
            'in_use': bool(cert.get('InUse', False)),
            'tags': {},
        })
    return results


def _collect_eks(session, region, account_id):
    eks = session.client('eks', region_name=region)
    results = []
    try:
        clusters = eks.list_clusters()['clusters']
        for name in clusters:
            try:
                detail = eks.describe_cluster(name=name)['cluster']
                vpc_config = detail.get('resourcesVpcConfig', {})
                results.append({
                    'type': 'eks',
                    'id': name,
                    'name': name,
                    'region': region,
                    'vpc_id': vpc_config.get('vpcId'),
                    'subnet_ids': vpc_config.get('subnetIds', []),
                    'security_groups': vpc_config.get('securityGroupIds', []),
                    'cluster_sg': vpc_config.get('clusterSecurityGroupId'),
                    'endpoint_public': vpc_config.get('endpointPublicAccess', True),
                    'endpoint_private': vpc_config.get('endpointPrivateAccess', False),
                    'status': detail.get('status', 'unknown'),
                    'version': detail.get('version'),
                    'tags': detail.get('tags', {}),
                })
            except Exception:
                continue
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_eks', exc)
    return results


def _collect_cloudfront(session, region, account_id):
    """CloudFront is global — region parameter ignored."""
    cf = session.client('cloudfront', region_name='us-east-1')
    results = []
    try:
        paginator = cf.get_paginator('list_distributions')
        for page in paginator.paginate():
            items = page.get('DistributionList', {}).get('Items', [])
            for dist in items:
                origins = []
                for origin in dist.get('Origins', {}).get('Items', []):
                    origins.append({
                        'id': origin.get('Id'),
                        'domain': origin.get('DomainName'),
                    })
                results.append({
                    'type': 'cloudfront',
                    'id': dist['Id'],
                    'name': dist.get('Comment') or dist['Id'],
                    'region': 'global',
                    'domain_name': dist.get('DomainName'),
                    'status': dist.get('Status', 'unknown'),
                    'enabled': dist.get('Enabled', False),
                    'origins': origins,
                    'aliases': dist.get('Aliases', {}).get('Items', []),
                    'tags': {},
                })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_cloudfront', exc)
    return results


def _collect_s3(session, region, account_id):
    """S3 is global — region parameter ignored."""
    s3 = session.client('s3', region_name='us-east-1')
    results = []
    try:
        buckets = s3.list_buckets().get('Buckets', [])
        for b in buckets:
            bucket_region = 'us-east-1'
            try:
                loc = s3.get_bucket_location(Bucket=b['Name'])
                bucket_region = loc.get('LocationConstraint') or 'us-east-1'
            except Exception as exc:
                _logger.warning('%s failed: %s', '_collect_s3', exc)
            results.append({
                'type': 's3',
                'id': b['Name'],
                'name': b['Name'],
                'region': bucket_region,
                'creation_date': b.get('CreationDate', '').isoformat() if hasattr(b.get('CreationDate', ''), 'isoformat') else str(b.get('CreationDate', '')),
                'tags': {},
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_s3', exc)
    return results


def _collect_organizations(session, region, account_id):
    """Organizations is global — region parameter ignored."""
    org = session.client('organizations', region_name='us-east-1')
    results = []
    try:
        org_info = org.describe_organization()['Organization']
        results.append({
            'type': 'organization',
            'id': org_info['Id'],
            'name': org_info.get('MasterAccountEmail', org_info['Id']),
            'region': 'global',
            'master_account_id': org_info.get('MasterAccountId'),
            'master_account_email': org_info.get('MasterAccountEmail'),
            'feature_set': org_info.get('FeatureSet'),
            'tags': {},
        })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_organizations', exc)
    # List accounts
    try:
        paginator = org.get_paginator('list_accounts')
        for page in paginator.paginate():
            for acct in page['Accounts']:
                results.append({
                    'type': 'org_account',
                    'id': acct['Id'],
                    'name': acct.get('Name', acct['Id']),
                    'region': 'global',
                    'email': acct.get('Email'),
                    'status': acct.get('Status', 'unknown'),
                    'joined': acct.get('JoinedTimestamp', '').isoformat() if hasattr(acct.get('JoinedTimestamp', ''), 'isoformat') else str(acct.get('JoinedTimestamp', '')),
                    'tags': {},
                })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_organizations', exc)
    return results



def _collect_ecs(session, region, account_id):
    ecs = session.client('ecs', region_name=region)
    results = []
    try:
        cluster_arns = []
        paginator = ecs.get_paginator('list_clusters')
        for page in paginator.paginate():
            cluster_arns.extend(page.get('clusterArns', []))
        if not cluster_arns:
            return results
        clusters = ecs.describe_clusters(clusters=cluster_arns, include=['SETTINGS', 'STATISTICS'])['clusters']
        for c in clusters:
            results.append({
                'type': 'ecs_cluster',
                'id': c['clusterName'],
                'name': c['clusterName'],
                'arn': c['clusterArn'],
                'region': region,
                'status': c.get('status', 'unknown'),
                'running_tasks': c.get('runningTasksCount', 0),
                'active_services': c.get('activeServicesCount', 0),
                'registered_instances': c.get('registeredContainerInstancesCount', 0),
                'tags': {t['key']: t['value'] for t in c.get('tags', [])},
            })
            # Collect services for each cluster
            try:
                svc_arns = []
                svc_paginator = ecs.get_paginator('list_services')
                for page in svc_paginator.paginate(cluster=c['clusterArn']):
                    svc_arns.extend(page.get('serviceArns', []))
                if svc_arns:
                    for i in range(0, len(svc_arns), 10):
                        batch = svc_arns[i:i+10]
                        svcs = ecs.describe_services(cluster=c['clusterArn'], services=batch)['services']
                        for svc in svcs:
                            net_config = svc.get('networkConfiguration', {}).get('awsvpcConfiguration', {})
                            results.append({
                                'type': 'ecs_service',
                                'id': svc['serviceName'],
                                'name': svc['serviceName'],
                                'arn': svc['serviceArn'],
                                'region': region,
                                'cluster': c['clusterName'],
                                'vpc_id': None,
                                'subnet_ids': net_config.get('subnets', []),
                                'security_groups': net_config.get('securityGroups', []),
                                'launch_type': svc.get('launchType', 'EC2'),
                                'desired_count': svc.get('desiredCount', 0),
                                'running_count': svc.get('runningCount', 0),
                                'status': svc.get('status', 'unknown'),
                                'tags': {},
                            })
            except Exception as exc:
                _logger.warning('%s failed: %s', 'unknown', exc)
    except Exception as exc:
        _logger.warning('%s failed: %s', 'unknown', exc)
    return results


def _collect_vpn(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    results = []
    # VPN Gateways
    try:
        vgws = ec2.describe_vpn_gateways()['VpnGateways']
        for vgw in vgws:
            tags = {t['Key']: t['Value'] for t in vgw.get('Tags', [])}
            vpc_attachments = [a['VpcId'] for a in vgw.get('VpcAttachments', []) if a.get('State') == 'attached']
            results.append({
                'type': 'vpn_gateway',
                'id': vgw['VpnGatewayId'],
                'name': tags.get('Name', vgw['VpnGatewayId']),
                'region': region,
                'state': vgw.get('State', 'unknown'),
                'vpc_id': vpc_attachments[0] if vpc_attachments else None,
                'vpc_ids': vpc_attachments,
                'amazon_side_asn': vgw.get('AmazonSideAsn'),
                'tags': tags,
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_vpn', exc)
    # Site-to-Site VPN Connections
    try:
        vpns = ec2.describe_vpn_connections()['VpnConnections']
        for vpn in vpns:
            if vpn.get('State') in ('deleted',):
                continue
            tags = {t['Key']: t['Value'] for t in vpn.get('Tags', [])}
            results.append({
                'type': 'vpn_connection',
                'id': vpn['VpnConnectionId'],
                'name': tags.get('Name', vpn['VpnConnectionId']),
                'region': region,
                'state': vpn.get('State', 'unknown'),
                'vpn_gateway_id': vpn.get('VpnGatewayId'),
                'transit_gateway_id': vpn.get('TransitGatewayId'),
                'customer_gateway_id': vpn.get('CustomerGatewayId'),
                'category': vpn.get('Category', ''),
                'tags': tags,
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_vpn', exc)
    # Customer Gateways
    try:
        cgws = ec2.describe_customer_gateways()['CustomerGateways']
        for cgw in cgws:
            if cgw.get('State') in ('deleted',):
                continue
            tags = {t['Key']: t['Value'] for t in cgw.get('Tags', [])}
            results.append({
                'type': 'customer_gateway',
                'id': cgw['CustomerGatewayId'],
                'name': tags.get('Name', cgw['CustomerGatewayId']),
                'region': region,
                'state': cgw.get('State', 'unknown'),
                'ip_address': cgw.get('IpAddress'),
                'bgp_asn': cgw.get('BgpAsn'),
                'tags': tags,
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', 'unknown', exc)
    return results


def _collect_network_firewall(session, region, account_id):
    results = []
    try:
        nfw = session.client('network-firewall', region_name=region)
        paginator = nfw.get_paginator('list_firewalls')
        for page in paginator.paginate():
            for fw_meta in page.get('Firewalls', []):
                try:
                    fw = nfw.describe_firewall(FirewallArn=fw_meta['FirewallArn'])['Firewall']
                    results.append({
                        'type': 'network_firewall',
                        'id': fw['FirewallName'],
                        'name': fw['FirewallName'],
                        'arn': fw['FirewallArn'],
                        'region': region,
                        'vpc_id': fw.get('VpcId'),
                        'subnet_ids': [sm['SubnetId'] for sm in fw.get('SubnetMappings', [])],
                        'policy_arn': fw.get('FirewallPolicyArn'),
                        'status': fw.get('FirewallStatus', {}).get('Status', 'unknown') if isinstance(fw.get('FirewallStatus'), dict) else 'unknown',
                        'tags': {t['Key']: t['Value'] for t in fw.get('Tags', [])},
                    })
                except Exception:
                    continue
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_network_firewall', exc)
    return results


def _collect_route53(session, region, account_id):
    """Route53 is global — region parameter ignored."""
    r53 = session.client('route53', region_name='us-east-1')
    results = []
    try:
        paginator = r53.get_paginator('list_hosted_zones')
        for page in paginator.paginate():
            for zone in page['HostedZones']:
                zone_id = zone['Id'].split('/')[-1]
                results.append({
                    'type': 'hosted_zone',
                    'id': zone_id,
                    'name': zone.get('Name', '').rstrip('.'),
                    'region': 'global',
                    'record_count': zone.get('ResourceRecordSetCount', 0),
                    'is_private': zone.get('Config', {}).get('PrivateZone', False),
                    'vpc_ids': [],
                    'tags': {},
                })
                # Get VPC associations for private zones
                if zone.get('Config', {}).get('PrivateZone'):
                    try:
                        assoc = r53.get_hosted_zone(Id=zone['Id'])
                        vpcs = assoc.get('VPCs', [])
                        results[-1]['vpc_ids'] = [v['VPCId'] for v in vpcs]
                        if vpcs:
                            results[-1]['vpc_id'] = vpcs[0]['VPCId']
                    except Exception as exc:
                        _logger.warning('%s failed: %s', '_collect_route53', exc)
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_route53', exc)
    return results


def _collect_api_gateway(session, region, account_id):
    results = []
    # REST APIs
    try:
        apigw = session.client('apigateway', region_name=region)
        apis = apigw.get_rest_apis()['items']
        for api in apis:
            vpc_link = api.get('endpointConfiguration', {}).get('vpcEndpointIds', [])
            results.append({
                'type': 'api_gateway',
                'id': api['id'],
                'name': api.get('name', api['id']),
                'region': region,
                'api_type': 'REST',
                'endpoint_type': ','.join(api.get('endpointConfiguration', {}).get('types', [])),
                'vpc_endpoint_ids': vpc_link,
                'tags': api.get('tags', {}),
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_api_gateway', exc)
    # HTTP APIs (API Gateway v2)
    try:
        apigw2 = session.client('apigatewayv2', region_name=region)
        apis2 = apigw2.get_apis()['Items']
        for api in apis2:
            results.append({
                'type': 'api_gateway',
                'id': api['ApiId'],
                'name': api.get('Name', api['ApiId']),
                'region': region,
                'api_type': api.get('ProtocolType', 'HTTP'),
                'endpoint': api.get('ApiEndpoint', ''),
                'tags': api.get('Tags', {}),
            })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_api_gateway', exc)
    return results


def _collect_eni(session, region, account_id):
    ec2 = session.client('ec2', region_name=region)
    results = []
    try:
        paginator = ec2.get_paginator('describe_network_interfaces')
        for page in paginator.paginate():
            for eni in page['NetworkInterfaces']:
                tags = {t['Key']: t['Value'] for t in eni.get('TagSet', [])}
                attachment = eni.get('Attachment', {})
                results.append({
                    'type': 'eni',
                    'id': eni['NetworkInterfaceId'],
                    'name': tags.get('Name', eni.get('Description', eni['NetworkInterfaceId'])),
                    'region': region,
                    'vpc_id': eni.get('VpcId'),
                    'subnet_id': eni.get('SubnetId'),
                    'az': eni.get('AvailabilityZone'),
                    'private_ip': eni.get('PrivateIpAddress'),
                    'public_ip': eni.get('Association', {}).get('PublicIp'),
                    'status': eni.get('Status', 'unknown'),
                    'interface_type': eni.get('InterfaceType', 'interface'),
                    'attachment_id': attachment.get('AttachmentId'),
                    'instance_id': attachment.get('InstanceId'),
                    'security_groups': [{'id': sg['GroupId'], 'name': sg['GroupName']} for sg in eni.get('Groups', [])],
                    'description': eni.get('Description', ''),
                    'tags': tags,
                })
    except Exception as exc:
        _logger.warning('%s failed: %s', '_collect_eni', exc)
    return results


# Service → collector function mapping
COLLECTOR_MAP = {
    'vpc':             _collect_vpcs,
    'subnet':          _collect_subnets,
    'igw':             _collect_igws,
    'nat':             _collect_nat_gateways,
    'route_table':     _collect_route_tables,
    'peering':         _collect_peering,
    'security_group':  _collect_security_groups,
    'nacl':            _collect_nacls,
    'vpc_endpoint':    _collect_vpc_endpoints,
    'eip':             _collect_eips,
    'ec2':             _collect_ec2,
    'rds':             _collect_rds,
    'elb':             _collect_elb,
    'lambda':          _collect_lambda,
    'transit_gateway': _collect_transit_gateways,
    'direct_connect':  _collect_direct_connect,
    'acm':             _collect_acm,
    'eks':             _collect_eks,
    'cloudfront':      _collect_cloudfront,
    's3':              _collect_s3,
    'organizations':   _collect_organizations,
    'ecs':             _collect_ecs,
    'vpn':             _collect_vpn,
    'network_firewall': _collect_network_firewall,
    'route53':         _collect_route53,
    'api_gateway':     _collect_api_gateway,
    'eni':             _collect_eni,
}


def _determine_public_subnets(resources):
    """Post-process: mark subnets as public if their route table has an IGW route."""
    route_tables = [r for r in resources if r['type'] == 'route_table']
    subnets = [r for r in resources if r['type'] == 'subnet']

    # Build mapping: subnet_id → has IGW route
    subnet_public_map = {}
    main_rt_per_vpc = {}

    for rt in route_tables:
        is_main = any(a.get('main') for a in rt.get('associations', []))
        if is_main:
            main_rt_per_vpc[rt['vpc_id']] = rt

        for assoc in rt.get('associations', []):
            sid = assoc.get('subnet_id')
            if sid:
                subnet_public_map[sid] = rt.get('has_igw_route', False)

    # For subnets not explicitly associated, use main route table
    for s in subnets:
        if s['id'] in subnet_public_map:
            s['is_public'] = subnet_public_map[s['id']]
        else:
            main_rt = main_rt_per_vpc.get(s['vpc_id'])
            if main_rt:
                s['is_public'] = main_rt.get('has_igw_route', False)


def collect_all(session, account_id, regions=None, max_workers=40,
                progress_callback=None, exclude_defaults=True):
    """
    Run all topology collectors in parallel.
    Returns dict with 'metadata', 'resources', and 'topology' keys.
    """
    if regions is None:
        regions = get_enabled_regions(session)

    all_resources = []
    _lock = threading.Lock()
    _completed = [0]
    start_time = time.time()
    _service_errors = {}

    # Build task list
    tasks = []
    for svc in SERVICES_ORDER:
        if svc in GLOBAL_SERVICES:
            tasks.append((svc, None))
        else:
            for region in regions:
                tasks.append((svc, region))

    total_tasks = len(tasks)

    def run_one(svc, region):
        func = COLLECTOR_MAP.get(svc)
        if func is None:
            return [], None
        try:
            resources = func(session, region, account_id)
            return resources or [], None
        except Exception as exc:
            return [], {'region': region or 'global', 'error': str(exc)[:200], 'type': type(exc).__name__}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for svc, region in tasks:
            future = executor.submit(run_one, svc, region)
            future_map[future] = (svc, region)

        for future in concurrent.futures.as_completed(future_map):
            svc, region = future_map[future]
            try:
                resources, error_info = future.result(timeout=TASK_TIMEOUT)
                with _lock:
                    if resources:
                        all_resources.extend(resources)
                    if error_info:
                        _service_errors.setdefault(svc, []).append(error_info)
                    _completed[0] += 1
                    if progress_callback:
                        progress_callback(svc, f'Completed {region or "global"}',
                                          _completed[0], total_tasks)
            except concurrent.futures.TimeoutError:
                with _lock:
                    _service_errors.setdefault(svc, []).append({
                        'region': region or 'global', 'error': f'Timeout after {TASK_TIMEOUT}s', 'type': 'TimeoutError'
                    })
                    _completed[0] += 1
                    if progress_callback:
                        progress_callback(svc, f'Timeout {region or "global"}', _completed[0], total_tasks)
            except Exception:
                with _lock:
                    _completed[0] += 1

    # Post-process: determine public/private subnets
    _determine_public_subnets(all_resources)

    # Filter defaults if requested
    if exclude_defaults:
        all_resources = [r for r in all_resources if not r.get('is_default', False)]

    # Build metadata
    duration = round(time.time() - start_time, 2)
    type_counts = {}
    for r in all_resources:
        t = r.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1

    region_counts = {}
    for r in all_resources:
        reg = r.get('region', 'unknown')
        region_counts[reg] = region_counts.get(reg, 0) + 1

    metadata = {
        'account_id': account_id,
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'scan_duration_seconds': duration,
        'regions_scanned': len(regions),
        'regions_scanned_list': regions,
        'resource_count': len(all_resources),
        'exclude_defaults': exclude_defaults,
        'type_counts': type_counts,
        'region_counts': region_counts,
    }

    return {
        'metadata': metadata,
        'resources': all_resources,
        'scan_errors': _service_errors,
    }
