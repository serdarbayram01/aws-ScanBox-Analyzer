"""
Map Inventory — Amazon Route 53 Resolver Collector
Resource types: resolver-endpoint, resolver-rule, firewall-rule-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_route53resolver_resources(session, region, account_id):
    """Collect Route 53 Resolver endpoints, rules, and firewall rule groups."""
    resources = []
    try:
        client = session.client('route53resolver', region_name=region)
    except Exception:
        return resources

    # ── Resolver Endpoints ────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_resolver_endpoints(**kwargs)
            for ep in resp.get('ResolverEndpoints', []):
                ep_id = ep.get('Id', '')
                ep_name = ep.get('Name', ep_id)
                ep_arn = ep.get('Arn', f"arn:aws:route53resolver:{region}:{account_id}:resolver-endpoint/{ep_id}")

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=ep_arn)
                    tags = {t['Key']: t['Value'] for t in tag_resp.get('Tags', []) if 'Key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='route53resolver',
                    resource_type='resolver-endpoint',
                    resource_id=ep_id,
                    arn=ep_arn,
                    name=ep_name,
                    region=region,
                    details={
                        'direction': ep.get('Direction', ''),
                        'status': ep.get('Status', ''),
                        'status_message': ep.get('StatusMessage', ''),
                        'ip_address_count': ep.get('IpAddressCount', 0),
                        'host_vpc_id': ep.get('HostVPCId', ''),
                        'security_group_ids': ep.get('SecurityGroupIds', []),
                        'creation_time': ep.get('CreationTime', ''),
                        'modification_time': ep.get('ModificationTime', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Resolver Rules ────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_resolver_rules(**kwargs)
            for rule in resp.get('ResolverRules', []):
                rule_id = rule.get('Id', '')
                rule_name = rule.get('Name', rule_id)
                rule_arn = rule.get('Arn', f"arn:aws:route53resolver:{region}:{account_id}:resolver-rule/{rule_id}")
                owner_id = rule.get('OwnerId', '')
                is_shared = (owner_id != account_id) if owner_id else False

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=rule_arn)
                    tags = {t['Key']: t['Value'] for t in tag_resp.get('Tags', []) if 'Key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='route53resolver',
                    resource_type='resolver-rule',
                    resource_id=rule_id,
                    arn=rule_arn,
                    name=rule_name,
                    region=region,
                    details={
                        'domain_name': rule.get('DomainName', ''),
                        'status': rule.get('Status', ''),
                        'rule_type': rule.get('RuleType', ''),
                        'resolver_endpoint_id': rule.get('ResolverEndpointId', ''),
                        'owner_id': owner_id,
                        'share_status': rule.get('ShareStatus', ''),
                        'target_ips': [
                            {'ip': t.get('Ip', ''), 'port': t.get('Port', 53)}
                            for t in rule.get('TargetIps', [])
                        ],
                        'creation_time': rule.get('CreationTime', ''),
                    },
                    tags=tags,
                    is_default=(rule.get('RuleType', '') == 'RECURSIVE'),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Firewall Rule Groups ─────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_firewall_rule_groups(**kwargs)
            for fg in resp.get('FirewallRuleGroups', []):
                fg_id = fg.get('Id', '')
                fg_name = fg.get('Name', fg_id)
                fg_arn = fg.get('Arn', f"arn:aws:route53resolver:{region}:{account_id}:firewall-rule-group/{fg_id}")
                owner_id = fg.get('OwnerId', '')

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=fg_arn)
                    tags = {t['Key']: t['Value'] for t in tag_resp.get('Tags', []) if 'Key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='route53resolver',
                    resource_type='firewall-rule-group',
                    resource_id=fg_id,
                    arn=fg_arn,
                    name=fg_name,
                    region=region,
                    details={
                        'status': fg.get('Status', ''),
                        'share_status': fg.get('ShareStatus', ''),
                        'owner_id': owner_id,
                        'creator_request_id': fg.get('CreatorRequestId', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
