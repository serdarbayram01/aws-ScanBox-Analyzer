"""
Map Inventory — IoT Core Collector
Resource types: thing, thing-type, thing-group, policy, certificate, rule
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_iot_resources(session, region, account_id):
    """Collect IoT Core resources in the given region."""
    resources = []
    try:
        client = session.client('iot', region_name=region)
    except Exception:
        return resources

    # ── Things ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_things')
        for page in paginator.paginate():
            for t in page.get('things', []):
                name = t.get('thingName', '')
                arn = t.get('thingArn', '')
                resources.append(make_resource(
                    service='iot',
                    resource_type='thing',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'thing_type_name': t.get('thingTypeName', ''),
                        'version': t.get('version', 0),
                        'attributes': t.get('attributes', {}),
                    },
                ))
    except Exception:
        pass

    # ── Thing Types ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_thing_types')
        for page in paginator.paginate():
            for tt in page.get('thingTypes', []):
                name = tt.get('thingTypeName', '')
                arn = tt.get('thingTypeArn', '')
                resources.append(make_resource(
                    service='iot',
                    resource_type='thing-type',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'deprecated': tt.get('thingTypeMetadata', {}).get('deprecated', False),
                        'description': tt.get('thingTypeProperties', {}).get('thingTypeDescription', ''),
                        'searchable_attributes': tt.get('thingTypeProperties', {}).get('searchableAttributes', []),
                    },
                ))
    except Exception:
        pass

    # ── Thing Groups ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_thing_groups')
        for page in paginator.paginate():
            for tg in page.get('thingGroups', []):
                name = tg.get('groupName', '')
                arn = tg.get('groupArn', '')
                resources.append(make_resource(
                    service='iot',
                    resource_type='thing-group',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={},
                ))
    except Exception:
        pass

    # ── Policies ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_policies')
        for page in paginator.paginate():
            for p in page.get('policies', []):
                name = p.get('policyName', '')
                arn = p.get('policyArn', '')
                resources.append(make_resource(
                    service='iot',
                    resource_type='policy',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={},
                ))
    except Exception:
        pass

    # ── Certificates ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_certificates')
        for page in paginator.paginate():
            for c in page.get('certificates', []):
                cid = c.get('certificateId', '')
                arn = c.get('certificateArn', '')
                resources.append(make_resource(
                    service='iot',
                    resource_type='certificate',
                    resource_id=cid,
                    arn=arn,
                    name=cid[:16] + '...' if len(cid) > 16 else cid,
                    region=region,
                    details={
                        'status': c.get('status', ''),
                        'creation_date': str(c.get('creationDate', '')),
                    },
                ))
    except Exception:
        pass

    # ── Rules ───────────────────────────────────────────────────────
    try:
        resp = client.list_topic_rules()
        for r in resp.get('rules', []):
            name = r.get('ruleName', '')
            arn = r.get('ruleArn', '')
            resources.append(make_resource(
                service='iot',
                resource_type='rule',
                resource_id=name,
                arn=arn,
                name=name,
                region=region,
                details={
                    'rule_disabled': r.get('ruleDisabled', False),
                    'topic_pattern': r.get('topicPattern', ''),
                    'created_at': str(r.get('createdAt', '')),
                },
            ))
    except Exception:
        pass

    return resources
