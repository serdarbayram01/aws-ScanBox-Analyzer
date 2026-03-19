"""
Map Inventory — Step Functions Collector
Resource types: state-machine, activity
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_stepfunctions_resources(session, region, account_id):
    """Collect Step Functions resources for a given region."""
    resources = []
    try:
        client = session.client('stepfunctions', region_name=region)
    except Exception:
        return resources

    # ── State Machines ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_state_machines')
        for page in paginator.paginate():
            for sm in page.get('stateMachines', []):
                sm_name = sm.get('name', '')
                sm_arn = sm.get('stateMachineArn', '')
                creation = str(sm.get('creationDate', ''))
                sm_type = sm.get('type', 'STANDARD')

                # Get details + tags
                details_dict = {
                    'type': sm_type,
                    'creation_date': creation,
                }
                tags = {}
                try:
                    desc = client.describe_state_machine(stateMachineArn=sm_arn)
                    details_dict.update({
                        'status': desc.get('status', ''),
                        'role_arn': desc.get('roleArn', ''),
                        'logging_level': desc.get('loggingConfiguration', {}).get('level', 'OFF'),
                        'tracing_enabled': desc.get('tracingConfiguration', {}).get('enabled', False),
                    })
                except Exception:
                    pass

                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=sm_arn)
                    tags = tags_to_dict(tag_resp.get('tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='stepfunctions',
                    resource_type='state-machine',
                    resource_id=sm_name,
                    arn=sm_arn,
                    name=sm_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Activities ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_activities')
        for page in paginator.paginate():
            for act in page.get('activities', []):
                act_name = act.get('name', '')
                act_arn = act.get('activityArn', '')
                creation = str(act.get('creationDate', ''))

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=act_arn)
                    tags = tags_to_dict(tag_resp.get('tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='stepfunctions',
                    resource_type='activity',
                    resource_id=act_name,
                    arn=act_arn,
                    name=act_name,
                    region=region,
                    details={
                        'creation_date': creation,
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
