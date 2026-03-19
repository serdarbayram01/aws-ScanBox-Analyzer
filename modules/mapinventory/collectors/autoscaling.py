"""
Map Inventory — Auto Scaling Collector
Resource types: auto-scaling-group, launch-configuration, scaling-policy, scheduled-action
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_autoscaling_resources(session, region, account_id):
    """Collect all Auto Scaling resource types in the given region."""
    resources = []
    try:
        asg = session.client('autoscaling', region_name=region)
    except Exception:
        return resources

    # ── Auto Scaling Groups ──────────────────────────────────────────
    try:
        paginator = asg.get_paginator('describe_auto_scaling_groups')
        for page in paginator.paginate():
            for group in page.get('AutoScalingGroups', []):
                group_name = group.get('AutoScalingGroupName', '')
                group_arn = group.get('AutoScalingGroupARN', '')
                tags = group.get('Tags', [])
                # ASG tags have a different format: Key, Value, PropagateAtLaunch, etc.
                tags_list = [{'Key': t.get('Key', ''), 'Value': t.get('Value', '')} for t in tags]
                display_name = get_tag_value(tags_list, 'Name') or group_name
                resources.append(make_resource(
                    service='autoscaling',
                    resource_type='auto-scaling-group',
                    resource_id=group_name,
                    arn=group_arn,
                    name=display_name,
                    region=region,
                    details={
                        'min_size': group.get('MinSize', 0),
                        'max_size': group.get('MaxSize', 0),
                        'desired_capacity': group.get('DesiredCapacity', 0),
                        'default_cooldown': group.get('DefaultCooldown', 0),
                        'availability_zones': group.get('AvailabilityZones', []),
                        'health_check_type': group.get('HealthCheckType', ''),
                        'health_check_grace_period': group.get('HealthCheckGracePeriod', 0),
                        'launch_configuration_name': group.get('LaunchConfigurationName', ''),
                        'launch_template': str(group.get('LaunchTemplate', {})),
                        'mixed_instances_policy': bool(group.get('MixedInstancesPolicy')),
                        'instances_count': len(group.get('Instances', [])),
                        'target_group_arns': group.get('TargetGroupARNs', []),
                        'load_balancer_names': group.get('LoadBalancerNames', []),
                        'status': group.get('Status', ''),
                        'created_time': str(group.get('CreatedTime', '')),
                    },
                    tags=tags_to_dict(tags_list),
                ))
    except Exception:
        pass

    # ── Launch Configurations ────────────────────────────────────────
    try:
        paginator = asg.get_paginator('describe_launch_configurations')
        for page in paginator.paginate():
            for lc in page.get('LaunchConfigurations', []):
                lc_name = lc.get('LaunchConfigurationName', '')
                lc_arn = lc.get('LaunchConfigurationARN', '')
                resources.append(make_resource(
                    service='autoscaling',
                    resource_type='launch-configuration',
                    resource_id=lc_name,
                    arn=lc_arn,
                    name=lc_name,
                    region=region,
                    details={
                        'image_id': lc.get('ImageId', ''),
                        'instance_type': lc.get('InstanceType', ''),
                        'key_name': lc.get('KeyName', ''),
                        'security_groups': lc.get('SecurityGroups', []),
                        'instance_monitoring': lc.get('InstanceMonitoring', {}).get('Enabled', False),
                        'ebs_optimized': lc.get('EbsOptimized', False),
                        'created_time': str(lc.get('CreatedTime', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Scaling Policies ─────────────────────────────────────────────
    try:
        paginator = asg.get_paginator('describe_policies')
        for page in paginator.paginate():
            for policy in page.get('ScalingPolicies', []):
                policy_name = policy.get('PolicyName', '')
                policy_arn = policy.get('PolicyARN', '')
                resources.append(make_resource(
                    service='autoscaling',
                    resource_type='scaling-policy',
                    resource_id=policy_name,
                    arn=policy_arn,
                    name=policy_name,
                    region=region,
                    details={
                        'auto_scaling_group_name': policy.get('AutoScalingGroupName', ''),
                        'policy_type': policy.get('PolicyType', ''),
                        'adjustment_type': policy.get('AdjustmentType', ''),
                        'scaling_adjustment': policy.get('ScalingAdjustment', ''),
                        'cooldown': policy.get('Cooldown', ''),
                        'metric_aggregation_type': policy.get('MetricAggregationType', ''),
                        'estimated_instance_warmup': policy.get('EstimatedInstanceWarmup', ''),
                        'enabled': policy.get('Enabled', True),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Scheduled Actions ────────────────────────────────────────────
    try:
        paginator = asg.get_paginator('describe_scheduled_actions')
        for page in paginator.paginate():
            for action in page.get('ScheduledUpdateGroupActions', []):
                action_name = action.get('ScheduledActionName', '')
                action_arn = action.get('ScheduledActionARN', '')
                resources.append(make_resource(
                    service='autoscaling',
                    resource_type='scheduled-action',
                    resource_id=action_name,
                    arn=action_arn,
                    name=action_name,
                    region=region,
                    details={
                        'auto_scaling_group_name': action.get('AutoScalingGroupName', ''),
                        'recurrence': action.get('Recurrence', ''),
                        'min_size': action.get('MinSize', ''),
                        'max_size': action.get('MaxSize', ''),
                        'desired_capacity': action.get('DesiredCapacity', ''),
                        'start_time': str(action.get('StartTime', '')),
                        'end_time': str(action.get('EndTime', '')),
                        'time_zone': action.get('TimeZone', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
