"""
Map Inventory — Amazon Connect Collector
Resource types: instance
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_connect_resources(session, region, account_id):
    """Collect Amazon Connect instances in the given region."""
    resources = []
    try:
        client = session.client('connect', region_name=region)
    except Exception:
        return resources

    # ── Instances ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_instances')
        for page in paginator.paginate():
            for inst in page.get('InstanceSummaryList', []):
                iid = inst.get('Id', '')
                arn = inst.get('Arn', '')
                resources.append(make_resource(
                    service='connect',
                    resource_type='instance',
                    resource_id=iid,
                    arn=arn,
                    name=inst.get('InstanceAlias', iid),
                    region=region,
                    details={
                        'identity_management_type': inst.get('IdentityManagementType', ''),
                        'instance_status': inst.get('InstanceStatus', ''),
                        'service_role': inst.get('ServiceRole', ''),
                        'created_time': str(inst.get('CreatedTime', '')),
                        'inbound_calls_enabled': inst.get('InboundCallsEnabled', False),
                        'outbound_calls_enabled': inst.get('OutboundCallsEnabled', False),
                    },
                ))
    except Exception:
        pass

    return resources
