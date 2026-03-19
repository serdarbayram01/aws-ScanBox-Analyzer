"""
Map Inventory — Amazon MemoryDB Collector
Resource types: cluster, snapshot, acl, user, parameter-group, subnet-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_memorydb_resources(session, region, account_id):
    """Collect Amazon MemoryDB resources in the given region."""
    resources = []
    try:
        client = session.client('memorydb', region_name=region)
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
                cluster_name = cluster.get('Name', '')
                cluster_arn = cluster.get('ARN', '')
                status = cluster.get('Status', '')

                # Get tags
                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=cluster_arn)
                    tags = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass

                shards = cluster.get('Shards', [])
                total_nodes = sum(len(s.get('Nodes', [])) for s in shards)

                resources.append(make_resource(
                    service='memorydb',
                    resource_type='cluster',
                    resource_id=cluster_name,
                    arn=cluster_arn,
                    name=cluster_name,
                    region=region,
                    details={
                        'status': status,
                        'node_type': cluster.get('NodeType', ''),
                        'engine_version': cluster.get('EngineVersion', ''),
                        'engine_patch_version': cluster.get('EnginePatchVersion', ''),
                        'number_of_shards': len(shards),
                        'total_nodes': total_nodes,
                        'acl_name': cluster.get('ACLName', ''),
                        'parameter_group_name': cluster.get('ParameterGroupName', ''),
                        'subnet_group_name': cluster.get('SubnetGroupName', ''),
                        'sns_topic_arn': cluster.get('SnsTopicArn', ''),
                        'tls_enabled': cluster.get('TLSEnabled', False),
                        'data_tiering': cluster.get('DataTiering', ''),
                        'auto_minor_version_upgrade': cluster.get('AutoMinorVersionUpgrade', False),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Snapshots ────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_snapshots(**kwargs)
            for snap in resp.get('Snapshots', []):
                snap_name = snap.get('Name', '')
                snap_arn = snap.get('ARN', '')
                status = snap.get('Status', '')
                source = snap.get('Source', '')

                resources.append(make_resource(
                    service='memorydb',
                    resource_type='snapshot',
                    resource_id=snap_name,
                    arn=snap_arn,
                    name=snap_name,
                    region=region,
                    details={
                        'status': status,
                        'source': source,
                        'cluster_name': snap.get('ClusterConfiguration', {}).get('Name', ''),
                        'node_type': snap.get('ClusterConfiguration', {}).get('NodeType', ''),
                        'engine_version': snap.get('ClusterConfiguration', {}).get('EngineVersion', ''),
                        'num_shards': snap.get('ClusterConfiguration', {}).get('NumShards', 0),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── ACLs ─────────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_acls(**kwargs)
            for acl in resp.get('ACLs', []):
                acl_name = acl.get('Name', '')
                acl_arn = acl.get('ARN', '')
                status = acl.get('Status', '')

                resources.append(make_resource(
                    service='memorydb',
                    resource_type='acl',
                    resource_id=acl_name,
                    arn=acl_arn,
                    name=acl_name,
                    region=region,
                    details={
                        'status': status,
                        'user_names': acl.get('UserNames', []),
                        'minimum_engine_version': acl.get('MinimumEngineVersion', ''),
                        'clusters': acl.get('Clusters', []),
                    },
                    tags={},
                    is_default=(acl_name == 'open-access'),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Users ────────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_users(**kwargs)
            for user in resp.get('Users', []):
                user_name = user.get('Name', '')
                user_arn = user.get('ARN', '')
                status = user.get('Status', '')

                resources.append(make_resource(
                    service='memorydb',
                    resource_type='user',
                    resource_id=user_name,
                    arn=user_arn,
                    name=user_name,
                    region=region,
                    details={
                        'status': status,
                        'access_string': user.get('AccessString', ''),
                        'acl_names': user.get('ACLNames', []),
                        'minimum_engine_version': user.get('MinimumEngineVersion', ''),
                        'authentication_type': user.get('Authentication', {}).get('Type', ''),
                    },
                    tags={},
                    is_default=(user_name == 'default'),
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
                pg_name = pg.get('Name', '')
                pg_arn = pg.get('ARN', '')

                resources.append(make_resource(
                    service='memorydb',
                    resource_type='parameter-group',
                    resource_id=pg_name,
                    arn=pg_arn,
                    name=pg_name,
                    region=region,
                    details={
                        'family': pg.get('Family', ''),
                        'description': pg.get('Description', ''),
                    },
                    tags={},
                    is_default=pg_name.startswith('default.'),
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
                sg_name = sg.get('Name', '')
                sg_arn = sg.get('ARN', '')

                subnets = sg.get('Subnets', [])
                subnet_ids = [s.get('Identifier', '') for s in subnets]

                resources.append(make_resource(
                    service='memorydb',
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
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
