"""
Map Inventory — Amazon DynamoDB Accelerator (DAX) Collector
Resource types: cluster, subnet-group, parameter-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_dax_resources(session, region, account_id):
    """Collect Amazon DAX resources in the given region."""
    resources = []
    try:
        client = session.client('dax', region_name=region)
    except Exception:
        return resources

    # ── Clusters ─────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_clusters(**kwargs)
            for cluster in resp.get('Clusters', []):
                cluster_name = cluster.get('ClusterName', '')
                cluster_arn = cluster.get('ClusterArn', '')
                status = cluster.get('Status', '')

                # Get tags
                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceName=cluster_arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                nodes = cluster.get('Nodes', [])
                endpoint = cluster.get('ClusterDiscoveryEndpoint', {})

                resources.append(make_resource(
                    service='dax',
                    resource_type='cluster',
                    resource_id=cluster_name,
                    arn=cluster_arn,
                    name=cluster_name,
                    region=region,
                    details={
                        'status': status,
                        'node_type': cluster.get('NodeType', ''),
                        'total_nodes': cluster.get('TotalNodes', 0),
                        'active_nodes': cluster.get('ActiveNodes', 0),
                        'node_ids_to_remove': cluster.get('NodeIdsToRemove', []),
                        'iam_role_arn': cluster.get('IamRoleArn', ''),
                        'subnet_group': cluster.get('SubnetGroup', ''),
                        'parameter_group': cluster.get('ParameterGroup', {}).get('ParameterGroupName', ''),
                        'sse_enabled': cluster.get('SSEDescription', {}).get('Status', '') == 'ENABLED',
                        'endpoint_address': endpoint.get('Address', ''),
                        'endpoint_port': endpoint.get('Port', 0),
                        'preferred_maintenance_window': cluster.get('PreferredMaintenanceWindow', ''),
                        'cluster_endpoint_encryption_type': cluster.get('ClusterEndpointEncryptionType', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Subnet Groups ────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_subnet_groups(**kwargs)
            for sg in resp.get('SubnetGroups', []):
                sg_name = sg.get('SubnetGroupName', '')
                subnets = sg.get('Subnets', [])
                subnet_ids = [s.get('SubnetIdentifier', '') for s in subnets]
                sg_arn = f"arn:aws:dax:{region}:{account_id}:subnet-group/{sg_name}"

                resources.append(make_resource(
                    service='dax',
                    resource_type='subnet-group',
                    resource_id=sg_name,
                    arn=sg_arn,
                    name=sg_name,
                    region=region,
                    details={
                        'description': sg.get('Description', ''),
                        'vpc_id': sg.get('VpcId', ''),
                        'subnet_ids': subnet_ids,
                        'subnet_count': len(subnet_ids),
                    },
                    tags={},
                    is_default=(sg_name == 'default'),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Parameter Groups ─────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_parameter_groups(**kwargs)
            for pg in resp.get('ParameterGroups', []):
                pg_name = pg.get('ParameterGroupName', '')
                pg_arn = f"arn:aws:dax:{region}:{account_id}:parameter-group/{pg_name}"

                resources.append(make_resource(
                    service='dax',
                    resource_type='parameter-group',
                    resource_id=pg_name,
                    arn=pg_arn,
                    name=pg_name,
                    region=region,
                    details={
                        'description': pg.get('Description', ''),
                    },
                    tags={},
                    is_default=(pg_name == 'default.dax1.0'),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
