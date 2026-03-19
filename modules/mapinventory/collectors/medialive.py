"""
Map Inventory — MediaLive Collector
Resource types: channel, input, input-security-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_medialive_resources(session, region, account_id):
    """Collect MediaLive resources in the given region."""
    resources = []
    try:
        client = session.client('medialive', region_name=region)
    except Exception:
        return resources

    # ── Channels ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_channels')
        for page in paginator.paginate():
            for ch in page.get('Channels', []):
                cid = ch.get('Id', '')
                arn = ch.get('Arn', '')
                tags_dict = ch.get('Tags', {})
                resources.append(make_resource(
                    service='medialive',
                    resource_type='channel',
                    resource_id=cid,
                    arn=arn,
                    name=ch.get('Name', cid),
                    region=region,
                    details={
                        'state': ch.get('State', ''),
                        'channel_class': ch.get('ChannelClass', ''),
                        'pipelines_running_count': ch.get('PipelinesRunningCount', 0),
                        'input_attachments': len(ch.get('InputAttachments', [])),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Inputs ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_inputs')
        for page in paginator.paginate():
            for inp in page.get('Inputs', []):
                iid = inp.get('Id', '')
                arn = inp.get('Arn', '')
                tags_dict = inp.get('Tags', {})
                resources.append(make_resource(
                    service='medialive',
                    resource_type='input',
                    resource_id=iid,
                    arn=arn,
                    name=inp.get('Name', iid),
                    region=region,
                    details={
                        'type': inp.get('Type', ''),
                        'state': inp.get('State', ''),
                        'input_class': inp.get('InputClass', ''),
                        'attached_channels': inp.get('AttachedChannels', []),
                        'security_groups': inp.get('SecurityGroups', []),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Input Security Groups ───────────────────────────────────────
    try:
        paginator = client.get_paginator('list_input_security_groups')
        for page in paginator.paginate():
            for isg in page.get('InputSecurityGroups', []):
                isg_id = isg.get('Id', '')
                arn = isg.get('Arn', '')
                tags_dict = isg.get('Tags', {})
                resources.append(make_resource(
                    service='medialive',
                    resource_type='input-security-group',
                    resource_id=isg_id,
                    arn=arn,
                    name=isg_id,
                    region=region,
                    details={
                        'state': isg.get('State', ''),
                        'whitelist_rules': [r.get('Cidr', '') for r in isg.get('WhitelistRules', [])],
                        'inputs': isg.get('Inputs', []),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
