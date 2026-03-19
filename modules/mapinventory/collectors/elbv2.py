"""
Map Inventory — ELBv2 Collector
Collects: application-load-balancer, network-load-balancer, gateway-load-balancer,
          target-group, listener
"""

from .base import make_resource, tags_to_dict, get_tag_value


# Map ELBv2 Type to resource_type
_LB_TYPE_MAP = {
    'application': 'application-load-balancer',
    'network': 'network-load-balancer',
    'gateway': 'gateway-load-balancer',
}


def collect_elbv2_resources(session, region, account_id):
    """Collect ELBv2 resources for a given region."""
    resources = []
    try:
        client = session.client('elbv2', region_name=region)
    except Exception:
        return resources

    # --- Load Balancers ---
    all_lbs = []
    try:
        paginator = client.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            all_lbs.extend(page.get('LoadBalancers', []))

        if all_lbs:
            # Fetch tags in batches of 20
            lb_arns = [lb.get('LoadBalancerArn', '') for lb in all_lbs]
            tags_map = {}
            for i in range(0, len(lb_arns), 20):
                batch = lb_arns[i:i + 20]
                try:
                    tags_resp = client.describe_tags(ResourceArns=batch)
                    for td in tags_resp.get('TagDescriptions', []):
                        arn = td.get('ResourceArn', '')
                        tags_map[arn] = tags_to_dict(td.get('Tags', []))
                except Exception:
                    pass

            for lb in all_lbs:
                lb_arn = lb.get('LoadBalancerArn', '')
                lb_name = lb.get('LoadBalancerName', '')
                lb_type = lb.get('Type', 'application').lower()
                resource_type = _LB_TYPE_MAP.get(lb_type, 'application-load-balancer')
                azs = lb.get('AvailabilityZones', [])

                resources.append(make_resource(
                    service='elbv2',
                    resource_type=resource_type,
                    resource_id=lb_name,
                    arn=lb_arn,
                    name=lb_name,
                    region=region,
                    details={
                        'dns_name': lb.get('DNSName', ''),
                        'scheme': lb.get('Scheme', ''),
                        'vpc_id': lb.get('VpcId', ''),
                        'state': lb.get('State', {}).get('Code', ''),
                        'type': lb_type,
                        'ip_address_type': lb.get('IpAddressType', ''),
                        'availability_zones': [az.get('ZoneName', '') for az in azs],
                        'security_groups': lb.get('SecurityGroups', []),
                    },
                    tags=tags_map.get(lb_arn, {}),
                ))

                # --- Listeners per LB ---
                try:
                    listener_paginator = client.get_paginator('describe_listeners')
                    for lpage in listener_paginator.paginate(LoadBalancerArn=lb_arn):
                        for listener in lpage.get('Listeners', []):
                            l_arn = listener.get('ListenerArn', '')
                            port = listener.get('Port', 0)
                            protocol = listener.get('Protocol', '')
                            l_name = f"{lb_name}:{port}/{protocol}"

                            resources.append(make_resource(
                                service='elbv2',
                                resource_type='listener',
                                resource_id=l_arn,
                                arn=l_arn,
                                name=l_name,
                                region=region,
                                details={
                                    'load_balancer_arn': lb_arn,
                                    'load_balancer_name': lb_name,
                                    'port': port,
                                    'protocol': protocol,
                                    'ssl_policy': listener.get('SslPolicy', ''),
                                },
                                tags={},
                            ))
                except Exception:
                    pass
    except Exception:
        pass

    # --- Target Groups ---
    try:
        tg_paginator = client.get_paginator('describe_target_groups')
        all_tgs = []
        for page in tg_paginator.paginate():
            all_tgs.extend(page.get('TargetGroups', []))

        # Fetch tags for target groups
        tg_arns = [tg.get('TargetGroupArn', '') for tg in all_tgs]
        tg_tags_map = {}
        for i in range(0, len(tg_arns), 20):
            batch = tg_arns[i:i + 20]
            try:
                tags_resp = client.describe_tags(ResourceArns=batch)
                for td in tags_resp.get('TagDescriptions', []):
                    arn = td.get('ResourceArn', '')
                    tg_tags_map[arn] = tags_to_dict(td.get('Tags', []))
            except Exception:
                pass

        for tg in all_tgs:
            tg_arn = tg.get('TargetGroupArn', '')
            tg_name = tg.get('TargetGroupName', '')

            # Get target health for count
            healthy_count = 0
            total_targets = 0
            try:
                th_resp = client.describe_target_health(TargetGroupArn=tg_arn)
                targets = th_resp.get('TargetHealthDescriptions', [])
                total_targets = len(targets)
                healthy_count = sum(
                    1 for t in targets
                    if t.get('TargetHealth', {}).get('State') == 'healthy'
                )
            except Exception:
                pass

            resources.append(make_resource(
                service='elbv2',
                resource_type='target-group',
                resource_id=tg_name,
                arn=tg_arn,
                name=tg_name,
                region=region,
                details={
                    'protocol': tg.get('Protocol', ''),
                    'port': tg.get('Port', 0),
                    'vpc_id': tg.get('VpcId', ''),
                    'target_type': tg.get('TargetType', ''),
                    'health_check_protocol': tg.get('HealthCheckProtocol', ''),
                    'health_check_path': tg.get('HealthCheckPath', ''),
                    'load_balancer_arns': tg.get('LoadBalancerArns', []),
                    'total_targets': total_targets,
                    'healthy_targets': healthy_count,
                },
                tags=tg_tags_map.get(tg_arn, {}),
            ))
    except Exception:
        pass

    return resources
