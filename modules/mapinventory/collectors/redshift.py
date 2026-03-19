"""
Map Inventory — Redshift Collector
Resource types: cluster, serverless-workgroup, serverless-namespace,
                parameter-group, subnet-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_redshift_resources(session, region, account_id):
    """Collect all Redshift resource types in the given region."""
    resources = []
    try:
        rs = session.client('redshift', region_name=region)
    except Exception:
        return resources

    # ── Clusters ─────────────────────────────────────────────────────
    try:
        paginator = rs.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for cluster in page.get('Clusters', []):
                cluster_id = cluster.get('ClusterIdentifier', '')
                # Tags are included in the response
                tags = cluster.get('Tags', [])
                display_name = get_tag_value(tags, 'Name') or cluster_id
                arn = f"arn:aws:redshift:{region}:{account_id}:cluster:{cluster_id}"
                endpoint = cluster.get('Endpoint', {})
                resources.append(make_resource(
                    service='redshift',
                    resource_type='cluster',
                    resource_id=cluster_id,
                    arn=arn,
                    name=display_name,
                    region=region,
                    details={
                        'node_type': cluster.get('NodeType', ''),
                        'cluster_status': cluster.get('ClusterStatus', ''),
                        'number_of_nodes': cluster.get('NumberOfNodes', 0),
                        'db_name': cluster.get('DBName', ''),
                        'master_username': cluster.get('MasterUsername', ''),
                        'endpoint_address': endpoint.get('Address', ''),
                        'endpoint_port': endpoint.get('Port', ''),
                        'vpc_id': cluster.get('VpcId', ''),
                        'availability_zone': cluster.get('AvailabilityZone', ''),
                        'encrypted': cluster.get('Encrypted', False),
                        'kms_key_id': cluster.get('KmsKeyId', ''),
                        'publicly_accessible': cluster.get('PubliclyAccessible', False),
                        'enhanced_vpc_routing': cluster.get('EnhancedVpcRouting', False),
                        'cluster_version': cluster.get('ClusterVersion', ''),
                        'automated_snapshot_retention_period': cluster.get('AutomatedSnapshotRetentionPeriod', 0),
                        'cluster_create_time': str(cluster.get('ClusterCreateTime', '')),
                        'cluster_subnet_group': cluster.get('ClusterSubnetGroupName', ''),
                        'parameter_group': str([
                            pg.get('ParameterGroupName', '')
                            for pg in cluster.get('ClusterParameterGroups', [])
                        ]),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Parameter Groups ─────────────────────────────────────────────
    try:
        paginator = rs.get_paginator('describe_cluster_parameter_groups')
        for page in paginator.paginate():
            for pg in page.get('ParameterGroups', []):
                pg_name = pg.get('ParameterGroupName', '')
                arn = f"arn:aws:redshift:{region}:{account_id}:parametergroup:{pg_name}"
                tags = pg.get('Tags', [])
                is_default = pg_name.startswith('default.')
                resources.append(make_resource(
                    service='redshift',
                    resource_type='parameter-group',
                    resource_id=pg_name,
                    arn=arn,
                    name=pg_name,
                    region=region,
                    details={
                        'family': pg.get('ParameterGroupFamily', ''),
                        'description': pg.get('Description', ''),
                    },
                    tags=tags_to_dict(tags),
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Subnet Groups ────────────────────────────────────────────────
    try:
        paginator = rs.get_paginator('describe_cluster_subnet_groups')
        for page in paginator.paginate():
            for sg in page.get('ClusterSubnetGroups', []):
                sg_name = sg.get('ClusterSubnetGroupName', '')
                arn = f"arn:aws:redshift:{region}:{account_id}:subnetgroup:{sg_name}"
                tags = sg.get('Tags', [])
                resources.append(make_resource(
                    service='redshift',
                    resource_type='subnet-group',
                    resource_id=sg_name,
                    arn=arn,
                    name=sg_name,
                    region=region,
                    details={
                        'vpc_id': sg.get('VpcId', ''),
                        'description': sg.get('Description', ''),
                        'status': sg.get('SubnetGroupStatus', ''),
                        'subnets_count': len(sg.get('Subnets', [])),
                    },
                    tags=tags_to_dict(tags),
                    is_default=(sg_name == 'default'),
                ))
    except Exception:
        pass

    # ── Redshift Serverless: Workgroups ──────────────────────────────
    try:
        rs_serverless = session.client('redshift-serverless', region_name=region)
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = rs_serverless.list_workgroups(**kwargs)
            for wg in resp.get('workgroups', []):
                wg_name = wg.get('workgroupName', '')
                wg_arn = wg.get('workgroupArn', '')
                wg_id = wg.get('workgroupId', '')
                endpoint = wg.get('endpoint', {})
                resources.append(make_resource(
                    service='redshift',
                    resource_type='serverless-workgroup',
                    resource_id=wg_id,
                    arn=wg_arn,
                    name=wg_name,
                    region=region,
                    details={
                        'status': wg.get('status', ''),
                        'namespace_name': wg.get('namespaceName', ''),
                        'base_capacity': wg.get('baseCapacity', ''),
                        'max_capacity': wg.get('maxCapacity', ''),
                        'endpoint_address': endpoint.get('address', ''),
                        'endpoint_port': endpoint.get('port', ''),
                        'publicly_accessible': wg.get('publiclyAccessible', False),
                        'enhanced_vpc_routing': wg.get('enhancedVpcRouting', False),
                        'security_group_ids': wg.get('securityGroupIds', []),
                        'subnet_ids': wg.get('subnetIds', []),
                        'creation_date': str(wg.get('creationDate', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Redshift Serverless: Namespaces ──────────────────────────────
    try:
        if 'rs_serverless' not in dir():
            rs_serverless = session.client('redshift-serverless', region_name=region)
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = rs_serverless.list_namespaces(**kwargs)
            for ns in resp.get('namespaces', []):
                ns_name = ns.get('namespaceName', '')
                ns_arn = ns.get('namespaceArn', '')
                ns_id = ns.get('namespaceId', '')
                resources.append(make_resource(
                    service='redshift',
                    resource_type='serverless-namespace',
                    resource_id=ns_id,
                    arn=ns_arn,
                    name=ns_name,
                    region=region,
                    details={
                        'status': ns.get('status', ''),
                        'admin_username': ns.get('adminUsername', ''),
                        'db_name': ns.get('dbName', ''),
                        'kms_key_id': ns.get('kmsKeyId', ''),
                        'default_iam_role_arn': ns.get('defaultIamRoleArn', ''),
                        'iam_roles': ns.get('iamRoles', []),
                        'log_exports': ns.get('logExports', []),
                        'creation_date': str(ns.get('creationDate', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
