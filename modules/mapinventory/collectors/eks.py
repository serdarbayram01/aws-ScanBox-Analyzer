"""
Map Inventory — EKS Collector
Collects: cluster, nodegroup, fargate-profile, addon
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_eks_resources(session, region, account_id):
    """Collect EKS resources for a given region."""
    resources = []
    try:
        client = session.client('eks', region_name=region)
    except Exception:
        return resources

    # --- Clusters ---
    cluster_names = []
    try:
        paginator = client.get_paginator('list_clusters')
        for page in paginator.paginate():
            cluster_names.extend(page.get('clusters', []))
    except Exception:
        return resources

    for cluster_name in cluster_names:
        try:
            resp = client.describe_cluster(name=cluster_name)
            c = resp.get('cluster', {})
            c_arn = c.get('arn', '')
            tags = c.get('tags', {})
            vpc_config = c.get('resourcesVpcConfig', {})
            encryption_config = c.get('encryptionConfig', [])
            encryption_enabled = len(encryption_config) > 0

            resources.append(make_resource(
                service='eks',
                resource_type='cluster',
                resource_id=cluster_name,
                arn=c_arn,
                name=cluster_name,
                region=region,
                details={
                    'status': c.get('status', ''),
                    'version': c.get('version', ''),
                    'platform_version': c.get('platformVersion', ''),
                    'endpoint': c.get('endpoint', ''),
                    'role_arn': c.get('roleArn', ''),
                    'vpc_id': vpc_config.get('vpcId', ''),
                    'endpoint_public_access': vpc_config.get('endpointPublicAccess', False),
                    'endpoint_private_access': vpc_config.get('endpointPrivateAccess', False),
                    'encryption_enabled': encryption_enabled,
                },
                tags=tags if isinstance(tags, dict) else {},
            ))
        except Exception:
            continue

        # --- Nodegroups per cluster ---
        try:
            ng_names = []
            ng_paginator = client.get_paginator('list_nodegroups')
            for page in ng_paginator.paginate(clusterName=cluster_name):
                ng_names.extend(page.get('nodegroups', []))

            for ng_name in ng_names:
                try:
                    ng_resp = client.describe_nodegroup(
                        clusterName=cluster_name,
                        nodegroupName=ng_name,
                    )
                    ng = ng_resp.get('nodegroup', {})
                    ng_arn = ng.get('nodegroupArn', '')
                    ng_tags = ng.get('tags', {})
                    scaling = ng.get('scalingConfig', {})
                    resources.append(make_resource(
                        service='eks',
                        resource_type='nodegroup',
                        resource_id=ng_name,
                        arn=ng_arn,
                        name=ng_name,
                        region=region,
                        details={
                            'cluster': cluster_name,
                            'status': ng.get('status', ''),
                            'capacity_type': ng.get('capacityType', ''),
                            'instance_types': ng.get('instanceTypes', []),
                            'ami_type': ng.get('amiType', ''),
                            'scaling_config': {
                                'min_size': scaling.get('minSize', 0),
                                'max_size': scaling.get('maxSize', 0),
                                'desired_size': scaling.get('desiredSize', 0),
                            },
                            'disk_size': ng.get('diskSize', 0),
                        },
                        tags=ng_tags if isinstance(ng_tags, dict) else {},
                    ))
                except Exception:
                    pass
        except Exception:
            pass

        # --- Fargate Profiles per cluster ---
        try:
            fp_names = []
            fp_paginator = client.get_paginator('list_fargate_profiles')
            for page in fp_paginator.paginate(clusterName=cluster_name):
                fp_names.extend(page.get('fargateProfileNames', []))

            for fp_name in fp_names:
                try:
                    fp_resp = client.describe_fargate_profile(
                        clusterName=cluster_name,
                        fargateProfileName=fp_name,
                    )
                    fp = fp_resp.get('fargateProfile', {})
                    fp_arn = fp.get('fargateProfileArn', '')
                    fp_tags = fp.get('tags', {})
                    selectors = fp.get('selectors', [])
                    resources.append(make_resource(
                        service='eks',
                        resource_type='fargate-profile',
                        resource_id=fp_name,
                        arn=fp_arn,
                        name=fp_name,
                        region=region,
                        details={
                            'cluster': cluster_name,
                            'status': fp.get('status', ''),
                            'pod_execution_role_arn': fp.get('podExecutionRoleArn', ''),
                            'subnets': fp.get('subnets', []),
                            'selectors': selectors,
                        },
                        tags=fp_tags if isinstance(fp_tags, dict) else {},
                    ))
                except Exception:
                    pass
        except Exception:
            pass

        # --- Addons per cluster ---
        try:
            addon_names = []
            addon_paginator = client.get_paginator('list_addons')
            for page in addon_paginator.paginate(clusterName=cluster_name):
                addon_names.extend(page.get('addons', []))

            for addon_name in addon_names:
                try:
                    addon_resp = client.describe_addon(
                        clusterName=cluster_name,
                        addonName=addon_name,
                    )
                    addon = addon_resp.get('addon', {})
                    addon_arn = addon.get('addonArn', '')
                    addon_tags = addon.get('tags', {})
                    resources.append(make_resource(
                        service='eks',
                        resource_type='addon',
                        resource_id=addon_name,
                        arn=addon_arn,
                        name=addon_name,
                        region=region,
                        details={
                            'cluster': cluster_name,
                            'status': addon.get('status', ''),
                            'addon_version': addon.get('addonVersion', ''),
                            'service_account_role_arn': addon.get('serviceAccountRoleArn', ''),
                        },
                        tags=addon_tags if isinstance(addon_tags, dict) else {},
                    ))
                except Exception:
                    pass
        except Exception:
            pass

    return resources
