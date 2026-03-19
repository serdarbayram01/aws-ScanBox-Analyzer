"""
Map Inventory — AWS Network Firewall Collector
Resource types: firewall, firewall-policy, rule-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_network_firewall_resources(session, region, account_id):
    """Collect all Network Firewall resource types in the given region."""
    resources = []
    try:
        client = session.client('network-firewall', region_name=region)
    except Exception:
        return resources

    # ── Firewalls ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_firewalls')
        for page in paginator.paginate():
            for fw_meta in page.get('Firewalls', []):
                fw_name = fw_meta.get('FirewallName', '')
                fw_arn = fw_meta.get('FirewallArn', '')
                # Fetch full details
                try:
                    detail = client.describe_firewall(FirewallArn=fw_arn)
                    fw = detail.get('Firewall', {})
                    fw_status = detail.get('FirewallStatus', {})
                    fw_id = fw.get('FirewallId', fw_name)
                    tags = fw.get('Tags', [])
                    resources.append(make_resource(
                        service='network-firewall',
                        resource_type='firewall',
                        resource_id=fw_id,
                        arn=fw_arn,
                        name=fw_name,
                        region=region,
                        details={
                            'status': fw_status.get('Status', ''),
                            'vpc_id': fw.get('VpcId', ''),
                            'firewall_policy_arn': fw.get('FirewallPolicyArn', ''),
                            'subnet_mappings': [
                                sm.get('SubnetId', '')
                                for sm in fw.get('SubnetMappings', [])
                            ],
                            'delete_protection': fw.get('DeleteProtection', False),
                            'description': fw.get('Description', ''),
                            'encryption_configuration': fw.get('EncryptionConfiguration', {}),
                        },
                        tags=tags_to_dict(tags),
                    ))
                except Exception:
                    resources.append(make_resource(
                        service='network-firewall',
                        resource_type='firewall',
                        resource_id=fw_name,
                        arn=fw_arn,
                        name=fw_name,
                        region=region,
                        details={},
                        tags={},
                    ))
    except Exception:
        pass

    # ── Firewall Policies ────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_firewall_policies')
        for page in paginator.paginate():
            for pol_meta in page.get('FirewallPolicies', []):
                pol_name = pol_meta.get('Name', '')
                pol_arn = pol_meta.get('Arn', '')
                # Fetch full details
                try:
                    detail = client.describe_firewall_policy(FirewallPolicyArn=pol_arn)
                    resp = detail.get('FirewallPolicyResponse', {})
                    pol_id = resp.get('FirewallPolicyId', pol_name)
                    tags = resp.get('Tags', [])
                    policy = detail.get('FirewallPolicy', {})
                    resources.append(make_resource(
                        service='network-firewall',
                        resource_type='firewall-policy',
                        resource_id=pol_id,
                        arn=pol_arn,
                        name=pol_name,
                        region=region,
                        details={
                            'status': resp.get('FirewallPolicyStatus', ''),
                            'description': resp.get('Description', ''),
                            'number_of_associations': resp.get('NumberOfAssociations', 0),
                            'stateless_default_actions': policy.get('StatelessDefaultActions', []),
                            'stateless_fragment_default_actions': policy.get(
                                'StatelessFragmentDefaultActions', []),
                            'stateful_rule_group_count': len(
                                policy.get('StatefulRuleGroupReferences', [])),
                            'stateless_rule_group_count': len(
                                policy.get('StatelessRuleGroupReferences', [])),
                            'encryption_configuration': resp.get('EncryptionConfiguration', {}),
                        },
                        tags=tags_to_dict(tags),
                    ))
                except Exception:
                    resources.append(make_resource(
                        service='network-firewall',
                        resource_type='firewall-policy',
                        resource_id=pol_name,
                        arn=pol_arn,
                        name=pol_name,
                        region=region,
                        details={},
                        tags={},
                    ))
    except Exception:
        pass

    # ── Rule Groups ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_rule_groups')
        for page in paginator.paginate():
            for rg_meta in page.get('RuleGroups', []):
                rg_name = rg_meta.get('Name', '')
                rg_arn = rg_meta.get('Arn', '')
                # Fetch full details
                try:
                    detail = client.describe_rule_group(RuleGroupArn=rg_arn)
                    resp = detail.get('RuleGroupResponse', {})
                    rg_id = resp.get('RuleGroupId', rg_name)
                    tags = resp.get('Tags', [])
                    resources.append(make_resource(
                        service='network-firewall',
                        resource_type='rule-group',
                        resource_id=rg_id,
                        arn=rg_arn,
                        name=rg_name,
                        region=region,
                        details={
                            'type': resp.get('Type', ''),
                            'status': resp.get('RuleGroupStatus', ''),
                            'capacity': resp.get('Capacity', 0),
                            'description': resp.get('Description', ''),
                            'number_of_associations': resp.get('NumberOfAssociations', 0),
                            'consumed_capacity': resp.get('ConsumedCapacity', 0),
                            'encryption_configuration': resp.get('EncryptionConfiguration', {}),
                        },
                        tags=tags_to_dict(tags),
                    ))
                except Exception:
                    resources.append(make_resource(
                        service='network-firewall',
                        resource_type='rule-group',
                        resource_id=rg_name,
                        arn=rg_arn,
                        name=rg_name,
                        region=region,
                        details={},
                        tags={},
                    ))
    except Exception:
        pass

    return resources
