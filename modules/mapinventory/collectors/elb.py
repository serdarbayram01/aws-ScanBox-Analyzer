"""
Map Inventory — ELB (Classic) Collector
Collects: classic-load-balancer
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_elb_resources(session, region, account_id):
    """Collect Classic ELB resources for a given region."""
    resources = []
    try:
        client = session.client('elb', region_name=region)
    except Exception:
        return resources

    try:
        all_lbs = []
        paginator = client.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            all_lbs.extend(page.get('LoadBalancerDescriptions', []))

        if not all_lbs:
            return resources

        # Fetch tags in batches of 20 (API limit)
        lb_names = [lb.get('LoadBalancerName', '') for lb in all_lbs]
        tags_map = {}
        for i in range(0, len(lb_names), 20):
            batch = lb_names[i:i + 20]
            try:
                tags_resp = client.describe_tags(LoadBalancerNames=batch)
                for td in tags_resp.get('TagDescriptions', []):
                    name = td.get('LoadBalancerName', '')
                    tags_map[name] = tags_to_dict(td.get('Tags', []))
            except Exception:
                pass

        for lb in all_lbs:
            lb_name = lb.get('LoadBalancerName', '')
            dns_name = lb.get('DNSName', '')
            scheme = lb.get('Scheme', '')
            vpc_id = lb.get('VPCId', '')
            azs = lb.get('AvailabilityZones', [])
            subnets = lb.get('Subnets', [])
            sgs = lb.get('SecurityGroups', [])
            instances = lb.get('Instances', [])
            listeners = lb.get('ListenerDescriptions', [])

            lb_arn = f"arn:aws:elasticloadbalancing:{region}:{account_id}:loadbalancer/{lb_name}"

            resources.append(make_resource(
                service='elb',
                resource_type='classic-load-balancer',
                resource_id=lb_name,
                arn=lb_arn,
                name=lb_name,
                region=region,
                details={
                    'dns_name': dns_name,
                    'scheme': scheme,
                    'vpc_id': vpc_id,
                    'availability_zones': azs,
                    'subnets': subnets,
                    'security_groups': sgs,
                    'instances_count': len(instances),
                    'listeners_count': len(listeners),
                },
                tags=tags_map.get(lb_name, {}),
            ))
    except Exception:
        pass

    return resources
