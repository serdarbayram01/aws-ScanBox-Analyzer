"""
Map Inventory — ECS Collector
Collects: cluster, service, task-definition, capacity-provider
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ecs_resources(session, region, account_id):
    """Collect ECS resources for a given region."""
    resources = []
    try:
        client = session.client('ecs', region_name=region)
    except Exception:
        return resources

    # --- Clusters ---
    try:
        cluster_arns = []
        paginator = client.get_paginator('list_clusters')
        for page in paginator.paginate():
            cluster_arns.extend(page.get('clusterArns', []))

        if cluster_arns:
            # describe_clusters accepts max 100 at a time
            for i in range(0, len(cluster_arns), 100):
                batch = cluster_arns[i:i + 100]
                resp = client.describe_clusters(
                    clusters=batch,
                    include=['TAGS', 'SETTINGS', 'STATISTICS']
                )
                for c in resp.get('clusters', []):
                    cluster_name = c.get('clusterName', '')
                    cluster_arn = c.get('clusterArn', '')
                    tags_list = c.get('tags', [])
                    resources.append(make_resource(
                        service='ecs',
                        resource_type='cluster',
                        resource_id=cluster_name,
                        arn=cluster_arn,
                        name=cluster_name,
                        region=region,
                        details={
                            'status': c.get('status', ''),
                            'running_tasks_count': c.get('runningTasksCount', 0),
                            'pending_tasks_count': c.get('pendingTasksCount', 0),
                            'active_services_count': c.get('activeServicesCount', 0),
                            'registered_container_instances_count': c.get('registeredContainerInstancesCount', 0),
                            'capacity_providers': c.get('capacityProviders', []),
                        },
                        tags=tags_to_dict(tags_list),
                    ))

                    # --- Services per cluster ---
                    try:
                        svc_arns = []
                        svc_paginator = client.get_paginator('list_services')
                        for svc_page in svc_paginator.paginate(cluster=cluster_arn):
                            svc_arns.extend(svc_page.get('serviceArns', []))

                        if svc_arns:
                            for j in range(0, len(svc_arns), 10):
                                svc_batch = svc_arns[j:j + 10]
                                svc_resp = client.describe_services(
                                    cluster=cluster_arn,
                                    services=svc_batch,
                                    include=['TAGS']
                                )
                                for svc in svc_resp.get('services', []):
                                    svc_name = svc.get('serviceName', '')
                                    svc_arn = svc.get('serviceArn', '')
                                    svc_tags = svc.get('tags', [])
                                    resources.append(make_resource(
                                        service='ecs',
                                        resource_type='service',
                                        resource_id=svc_name,
                                        arn=svc_arn,
                                        name=svc_name,
                                        region=region,
                                        details={
                                            'cluster': cluster_name,
                                            'status': svc.get('status', ''),
                                            'desired_count': svc.get('desiredCount', 0),
                                            'running_count': svc.get('runningCount', 0),
                                            'launch_type': svc.get('launchType', ''),
                                            'task_definition': svc.get('taskDefinition', ''),
                                        },
                                        tags=tags_to_dict(svc_tags),
                                    ))
                    except Exception:
                        pass
    except Exception:
        pass

    # --- Task Definitions ---
    try:
        families = []
        td_paginator = client.get_paginator('list_task_definition_families')
        for page in td_paginator.paginate(status='ACTIVE'):
            families.extend(page.get('families', []))

        for family in families:
            try:
                td_resp = client.describe_task_definition(
                    taskDefinition=family,
                    include=['TAGS']
                )
                td = td_resp.get('taskDefinition', {})
                td_tags = td_resp.get('tags', [])
                td_arn = td.get('taskDefinitionArn', '')
                containers = td.get('containerDefinitions', [])
                revision = td.get('revision', 0)
                td_name = f"{family}:{revision}"
                resources.append(make_resource(
                    service='ecs',
                    resource_type='task-definition',
                    resource_id=td_name,
                    arn=td_arn,
                    name=td_name,
                    region=region,
                    details={
                        'family': family,
                        'revision': revision,
                        'status': td.get('status', ''),
                        'cpu': td.get('cpu', ''),
                        'memory': td.get('memory', ''),
                        'network_mode': td.get('networkMode', ''),
                        'container_count': len(containers),
                    },
                    tags=tags_to_dict(td_tags),
                ))
            except Exception:
                pass
    except Exception:
        pass

    # --- Capacity Providers ---
    try:
        cp_resp = client.describe_capacity_providers()
        for cp in cp_resp.get('capacityProviders', []):
            cp_name = cp.get('name', '')
            # Skip AWS-managed FARGATE providers
            if cp_name in ('FARGATE', 'FARGATE_SPOT'):
                continue
            cp_arn = cp.get('capacityProviderArn', '')
            cp_tags = cp.get('tags', [])
            asg_provider = cp.get('autoScalingGroupProvider', {})
            resources.append(make_resource(
                service='ecs',
                resource_type='capacity-provider',
                resource_id=cp_name,
                arn=cp_arn,
                name=cp_name,
                region=region,
                details={
                    'status': cp.get('status', ''),
                    'auto_scaling_group_arn': asg_provider.get('autoScalingGroupArn', ''),
                },
                tags=tags_to_dict(cp_tags),
            ))
    except Exception:
        pass

    return resources
