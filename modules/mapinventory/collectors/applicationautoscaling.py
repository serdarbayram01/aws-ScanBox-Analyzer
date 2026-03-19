"""
Map Inventory — Application Auto Scaling Collector
Resource types: scalable-target, scaling-policy
"""

from .base import make_resource, tags_to_dict, get_tag_value

# All supported service namespaces for Application Auto Scaling
SERVICE_NAMESPACES = [
    'ecs', 'elasticmapreduce', 'ec2', 'appstream', 'dynamodb',
    'rds', 'sagemaker', 'custom-resource', 'comprehend', 'lambda',
    'cassandra', 'kafka', 'elasticache', 'neptune',
]


def collect_applicationautoscaling_resources(session, region, account_id):
    """Collect Application Auto Scaling resources in the given region."""
    resources = []
    try:
        client = session.client('application-autoscaling', region_name=region)
    except Exception:
        return resources

    for namespace in SERVICE_NAMESPACES:
        # ── Scalable Targets ─────────────────────────────────────────
        try:
            paginator = client.get_paginator('describe_scalable_targets')
            for page in paginator.paginate(ServiceNamespace=namespace):
                for target in page.get('ScalableTargets', []):
                    resource_id_val = target.get('ResourceId', '')
                    scalable_dim = target.get('ScalableDimension', '')
                    target_id = f"{namespace}/{resource_id_val}/{scalable_dim}"
                    creation = str(target.get('CreationTime', ''))
                    arn = f"arn:aws:application-autoscaling:{region}:{account_id}:scalable-target/{target_id}"

                    resources.append(make_resource(
                        service='applicationautoscaling',
                        resource_type='scalable-target',
                        resource_id=target_id,
                        arn=arn,
                        name=resource_id_val,
                        region=region,
                        details={
                            'service_namespace': namespace,
                            'resource_id': resource_id_val,
                            'scalable_dimension': scalable_dim,
                            'min_capacity': target.get('MinCapacity', 0),
                            'max_capacity': target.get('MaxCapacity', 0),
                            'role_arn': target.get('RoleARN', ''),
                            'creation_time': creation,
                            'suspended_state': target.get('SuspendedState', {}),
                        },
                        tags={},
                    ))
        except Exception:
            pass

        # ── Scaling Policies ─────────────────────────────────────────
        try:
            paginator = client.get_paginator('describe_scaling_policies')
            for page in paginator.paginate(ServiceNamespace=namespace):
                for policy in page.get('ScalingPolicies', []):
                    policy_name = policy.get('PolicyName', '')
                    policy_arn = policy.get('PolicyARN', '')
                    resource_id_val = policy.get('ResourceId', '')
                    scalable_dim = policy.get('ScalableDimension', '')
                    policy_type = policy.get('PolicyType', '')
                    creation = str(policy.get('CreationTime', ''))

                    details = {
                        'service_namespace': namespace,
                        'resource_id': resource_id_val,
                        'scalable_dimension': scalable_dim,
                        'policy_type': policy_type,
                        'creation_time': creation,
                    }

                    # Add type-specific configuration
                    if policy_type == 'TargetTrackingScaling':
                        ttc = policy.get('TargetTrackingScalingPolicyConfiguration', {})
                        details['target_value'] = ttc.get('TargetValue', 0)
                        details['predefined_metric'] = ttc.get('PredefinedMetricSpecification', {}).get('PredefinedMetricType', '')
                    elif policy_type == 'StepScaling':
                        ssc = policy.get('StepScalingPolicyConfiguration', {})
                        details['adjustment_type'] = ssc.get('AdjustmentType', '')

                    resources.append(make_resource(
                        service='applicationautoscaling',
                        resource_type='scaling-policy',
                        resource_id=policy_name,
                        arn=policy_arn,
                        name=policy_name,
                        region=region,
                        details=details,
                        tags={},
                    ))
        except Exception:
            pass

    return resources
