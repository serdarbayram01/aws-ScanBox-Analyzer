"""
Map Inventory — AWS CloudFormation Collector
Resource types: stack, stack-set, export
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_cloudformation_resources(session, region, account_id):
    """Collect CloudFormation stacks, stack sets, and exports."""
    resources = []
    try:
        client = session.client('cloudformation', region_name=region)
    except Exception:
        return resources

    # ── Stacks ────────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_stacks')
        for page in paginator.paginate():
            for stack in page.get('Stacks', []):
                stack_name = stack.get('StackName', '')
                stack_id = stack.get('StackId', '')
                tags_list = stack.get('Tags', [])
                resources.append(make_resource(
                    service='cloudformation',
                    resource_type='stack',
                    resource_id=stack_name,
                    arn=stack_id,  # StackId is the full ARN
                    name=stack_name,
                    region=region,
                    details={
                        'status': stack.get('StackStatus', ''),
                        'status_reason': stack.get('StackStatusReason', ''),
                        'creation_time': str(stack.get('CreationTime', '')),
                        'last_updated_time': str(stack.get('LastUpdatedTime', '')),
                        'description': stack.get('Description', ''),
                        'drift_status': stack.get('DriftInformation', {}).get('StackDriftStatus', ''),
                        'enable_termination_protection': stack.get('EnableTerminationProtection', False),
                        'parent_id': stack.get('ParentId', ''),
                        'root_id': stack.get('RootId', ''),
                        'role_arn': stack.get('RoleARN', ''),
                        'outputs_count': len(stack.get('Outputs', [])),
                        'parameters_count': len(stack.get('Parameters', [])),
                    },
                    tags=tags_to_dict(tags_list),
                ))
    except Exception:
        pass

    # ── Stack Sets ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_stack_sets')
        for page in paginator.paginate(Status='ACTIVE'):
            for ss in page.get('Summaries', []):
                ss_name = ss.get('StackSetName', '')
                ss_id = ss.get('StackSetId', '')
                # Construct ARN since summary doesn't include it
                ss_arn = f"arn:aws:cloudformation:{region}:{account_id}:stackset/{ss_name}:{ss_id}"
                resources.append(make_resource(
                    service='cloudformation',
                    resource_type='stack-set',
                    resource_id=ss_name,
                    arn=ss_arn,
                    name=ss_name,
                    region=region,
                    details={
                        'status': ss.get('Status', ''),
                        'description': ss.get('Description', ''),
                        'drift_status': ss.get('DriftStatus', ''),
                        'permission_model': ss.get('PermissionModel', ''),
                        'auto_deployment': ss.get('AutoDeployment', {}).get('Enabled', False),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Exports ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_exports')
        for page in paginator.paginate():
            for exp in page.get('Exports', []):
                exp_name = exp.get('Name', '')
                exporting_stack_id = exp.get('ExportingStackId', '')
                # Exports don't have their own ARN; use stack ARN as reference
                resources.append(make_resource(
                    service='cloudformation',
                    resource_type='export',
                    resource_id=exp_name,
                    arn=exporting_stack_id,
                    name=exp_name,
                    region=region,
                    details={
                        'value': exp.get('Value', ''),
                        'exporting_stack_id': exporting_stack_id,
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
