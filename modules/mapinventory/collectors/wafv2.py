"""
Map Inventory — WAFv2 Collector
Resource types: web-acl-regional, web-acl-cloudfront, ip-set, rule-group, regex-pattern-set
"""

from .base import make_resource, tags_to_dict, get_tag_value


def _collect_scope(waf, scope, region, account_id, resources):
    """Collect WAFv2 resources for a given scope (REGIONAL or CLOUDFRONT)."""
    acl_type = 'web-acl-cloudfront' if scope == 'CLOUDFRONT' else 'web-acl-regional'

    # ── Web ACLs ─────────────────────────────────────────────────────
    try:
        next_marker = None
        while True:
            kwargs = {'Scope': scope}
            if next_marker:
                kwargs['NextMarker'] = next_marker
            resp = waf.list_web_acls(**kwargs)
            for acl_summary in resp.get('WebACLs', []):
                acl_name = acl_summary.get('Name', '')
                acl_id = acl_summary.get('Id', '')
                acl_arn = acl_summary.get('ARN', '')
                details = {
                    'scope': scope,
                    'lock_token': acl_summary.get('LockToken', ''),
                }
                tags_dict = {}
                try:
                    acl_detail = waf.get_web_acl(Name=acl_name, Scope=scope, Id=acl_id)
                    wacl = acl_detail.get('WebACL', {})
                    details.update({
                        'capacity': wacl.get('Capacity', 0),
                        'default_action': str(wacl.get('DefaultAction', {})),
                        'rules_count': len(wacl.get('Rules', [])),
                        'managed_by_firewall_manager': wacl.get('ManagedByFirewallManager', False),
                    })
                except Exception:
                    pass
                try:
                    tag_resp = waf.list_tags_for_resource(ResourceARN=acl_arn)
                    tag_info = tag_resp.get('TagInfoForResource', {})
                    tags_dict = tags_to_dict(tag_info.get('TagList', []))
                except Exception:
                    pass
                resources.append(make_resource(
                    service='wafv2',
                    resource_type=acl_type,
                    resource_id=acl_id,
                    arn=acl_arn,
                    name=acl_name,
                    region=region,
                    details=details,
                    tags=tags_dict,
                ))
            next_marker = resp.get('NextMarker')
            if not next_marker:
                break
    except Exception:
        pass

    # ── IP Sets ──────────────────────────────────────────────────────
    suffix = '-cloudfront' if scope == 'CLOUDFRONT' else ''
    try:
        next_marker = None
        while True:
            kwargs = {'Scope': scope}
            if next_marker:
                kwargs['NextMarker'] = next_marker
            resp = waf.list_ip_sets(**kwargs)
            for ip_set in resp.get('IPSets', []):
                ip_name = ip_set.get('Name', '')
                ip_id = ip_set.get('Id', '')
                ip_arn = ip_set.get('ARN', '')
                resources.append(make_resource(
                    service='wafv2',
                    resource_type=f'ip-set{suffix}',
                    resource_id=ip_id,
                    arn=ip_arn,
                    name=ip_name,
                    region=region,
                    details={
                        'scope': scope,
                        'lock_token': ip_set.get('LockToken', ''),
                    },
                    tags={},
                ))
            next_marker = resp.get('NextMarker')
            if not next_marker:
                break
    except Exception:
        pass

    # ── Rule Groups ──────────────────────────────────────────────────
    try:
        next_marker = None
        while True:
            kwargs = {'Scope': scope}
            if next_marker:
                kwargs['NextMarker'] = next_marker
            resp = waf.list_rule_groups(**kwargs)
            for rg in resp.get('RuleGroups', []):
                rg_name = rg.get('Name', '')
                rg_id = rg.get('Id', '')
                rg_arn = rg.get('ARN', '')
                resources.append(make_resource(
                    service='wafv2',
                    resource_type=f'rule-group{suffix}',
                    resource_id=rg_id,
                    arn=rg_arn,
                    name=rg_name,
                    region=region,
                    details={
                        'scope': scope,
                        'lock_token': rg.get('LockToken', ''),
                    },
                    tags={},
                ))
            next_marker = resp.get('NextMarker')
            if not next_marker:
                break
    except Exception:
        pass

    # ── Regex Pattern Sets ───────────────────────────────────────────
    try:
        next_marker = None
        while True:
            kwargs = {'Scope': scope}
            if next_marker:
                kwargs['NextMarker'] = next_marker
            resp = waf.list_regex_pattern_sets(**kwargs)
            for rps in resp.get('RegexPatternSets', []):
                rps_name = rps.get('Name', '')
                rps_id = rps.get('Id', '')
                rps_arn = rps.get('ARN', '')
                resources.append(make_resource(
                    service='wafv2',
                    resource_type=f'regex-pattern-set{suffix}',
                    resource_id=rps_id,
                    arn=rps_arn,
                    name=rps_name,
                    region=region,
                    details={
                        'scope': scope,
                        'lock_token': rps.get('LockToken', ''),
                    },
                    tags={},
                ))
            next_marker = resp.get('NextMarker')
            if not next_marker:
                break
    except Exception:
        pass


def collect_wafv2_resources(session, region, account_id):
    """Collect all WAFv2 resource types in the given region."""
    resources = []
    try:
        waf = session.client('wafv2', region_name=region)
    except Exception:
        return resources

    # Always collect REGIONAL scope
    _collect_scope(waf, 'REGIONAL', region, account_id, resources)

    # CLOUDFRONT scope is only available in us-east-1
    if region == 'us-east-1':
        _collect_scope(waf, 'CLOUDFRONT', region, account_id, resources)

    return resources
