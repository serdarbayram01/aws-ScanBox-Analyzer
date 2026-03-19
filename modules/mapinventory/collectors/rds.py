"""
Map Inventory — RDS Collector
Resource types: db-instance, db-cluster, db-snapshot, db-cluster-snapshot,
                db-subnet-group, db-parameter-group, option-group, db-proxy
"""

from .base import make_resource, tags_to_dict, get_tag_value


def _rds_tags(client, arn):
    """Fetch tags for an RDS resource ARN, returning a dict."""
    try:
        resp = client.list_tags_for_resource(ResourceName=arn)
        return tags_to_dict(resp.get('TagList', []))
    except Exception:
        return {}


def collect_rds_resources(session, region, account_id):
    """Collect all RDS resources in the given region."""
    resources = []
    try:
        rds = session.client('rds', region_name=region)
    except Exception:
        return resources

    # ── DB Instances ───────────────────────────────────────────────────
    try:
        paginator = rds.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for db in page.get('DBInstances', []):
                db_id = db['DBInstanceIdentifier']
                db_arn = db.get('DBInstanceArn', f"arn:aws:rds:{region}:{account_id}:db:{db_id}")
                tags = _rds_tags(rds, db_arn)

                endpoint = db.get('Endpoint', {})
                resources.append(make_resource(
                    service='rds',
                    resource_type='db-instance',
                    resource_id=db_id,
                    arn=db_arn,
                    name=db_id,
                    region=region,
                    details={
                        'engine': db.get('Engine', ''),
                        'engine_version': db.get('EngineVersion', ''),
                        'instance_class': db.get('DBInstanceClass', ''),
                        'status': db.get('DBInstanceStatus', ''),
                        'storage_type': db.get('StorageType', ''),
                        'allocated_storage': db.get('AllocatedStorage', 0),
                        'multi_az': db.get('MultiAZ', False),
                        'publicly_accessible': db.get('PubliclyAccessible', False),
                        'encrypted': db.get('StorageEncrypted', False),
                        'endpoint': endpoint.get('Address', ''),
                        'port': endpoint.get('Port', ''),
                        'vpc_id': db.get('DBSubnetGroup', {}).get('VpcId', ''),
                        'cluster_identifier': db.get('DBClusterIdentifier', ''),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── DB Clusters ────────────────────────────────────────────────────
    try:
        paginator = rds.get_paginator('describe_db_clusters')
        for page in paginator.paginate():
            for cl in page.get('DBClusters', []):
                cl_id = cl['DBClusterIdentifier']
                cl_arn = cl.get('DBClusterArn', f"arn:aws:rds:{region}:{account_id}:cluster:{cl_id}")
                tags = _rds_tags(rds, cl_arn)

                members = [m.get('DBInstanceIdentifier', '') for m in cl.get('DBClusterMembers', [])]
                sv2 = cl.get('ServerlessV2ScalingConfiguration', {})

                resources.append(make_resource(
                    service='rds',
                    resource_type='db-cluster',
                    resource_id=cl_id,
                    arn=cl_arn,
                    name=cl_id,
                    region=region,
                    details={
                        'engine': cl.get('Engine', ''),
                        'engine_version': cl.get('EngineVersion', ''),
                        'engine_mode': cl.get('EngineMode', ''),
                        'status': cl.get('Status', ''),
                        'multi_az': cl.get('MultiAZ', False),
                        'encrypted': cl.get('StorageEncrypted', False),
                        'endpoint': cl.get('Endpoint', ''),
                        'reader_endpoint': cl.get('ReaderEndpoint', ''),
                        'port': cl.get('Port', ''),
                        'members': members,
                        'serverless_v2_scaling': {
                            'min_capacity': sv2.get('MinCapacity', ''),
                            'max_capacity': sv2.get('MaxCapacity', ''),
                        } if sv2 else None,
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── DB Snapshots (manual only) ─────────────────────────────────────
    try:
        paginator = rds.get_paginator('describe_db_snapshots')
        for page in paginator.paginate(SnapshotType='manual'):
            for snap in page.get('DBSnapshots', []):
                snap_id = snap['DBSnapshotIdentifier']
                snap_arn = snap.get('DBSnapshotArn', f"arn:aws:rds:{region}:{account_id}:snapshot:{snap_id}")
                tags = _rds_tags(rds, snap_arn)
                resources.append(make_resource(
                    service='rds',
                    resource_type='db-snapshot',
                    resource_id=snap_id,
                    arn=snap_arn,
                    name=snap_id,
                    region=region,
                    details={
                        'engine': snap.get('Engine', ''),
                        'engine_version': snap.get('EngineVersion', ''),
                        'instance_identifier': snap.get('DBInstanceIdentifier', ''),
                        'status': snap.get('Status', ''),
                        'allocated_storage': snap.get('AllocatedStorage', 0),
                        'encrypted': snap.get('Encrypted', False),
                        'snapshot_create_time': str(snap.get('SnapshotCreateTime', '')),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── DB Cluster Snapshots (manual only) ─────────────────────────────
    try:
        paginator = rds.get_paginator('describe_db_cluster_snapshots')
        for page in paginator.paginate(SnapshotType='manual'):
            for snap in page.get('DBClusterSnapshots', []):
                snap_id = snap['DBClusterSnapshotIdentifier']
                snap_arn = snap.get('DBClusterSnapshotArn', f"arn:aws:rds:{region}:{account_id}:cluster-snapshot:{snap_id}")
                tags = _rds_tags(rds, snap_arn)
                resources.append(make_resource(
                    service='rds',
                    resource_type='db-cluster-snapshot',
                    resource_id=snap_id,
                    arn=snap_arn,
                    name=snap_id,
                    region=region,
                    details={
                        'engine': snap.get('Engine', ''),
                        'engine_version': snap.get('EngineVersion', ''),
                        'cluster_identifier': snap.get('DBClusterIdentifier', ''),
                        'status': snap.get('Status', ''),
                        'allocated_storage': snap.get('AllocatedStorage', 0),
                        'encrypted': snap.get('StorageEncrypted', False),
                        'snapshot_create_time': str(snap.get('SnapshotCreateTime', '')),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── DB Subnet Groups ───────────────────────────────────────────────
    try:
        paginator = rds.get_paginator('describe_db_subnet_groups')
        for page in paginator.paginate():
            for sg in page.get('DBSubnetGroups', []):
                sg_name = sg['DBSubnetGroupName']
                sg_arn = sg.get('DBSubnetGroupArn', f"arn:aws:rds:{region}:{account_id}:subgrp:{sg_name}")
                tags = _rds_tags(rds, sg_arn)
                subnets = [s.get('SubnetIdentifier', '') for s in sg.get('Subnets', [])]
                resources.append(make_resource(
                    service='rds',
                    resource_type='db-subnet-group',
                    resource_id=sg_name,
                    arn=sg_arn,
                    name=sg_name,
                    region=region,
                    details={
                        'vpc_id': sg.get('VpcId', ''),
                        'description': sg.get('DBSubnetGroupDescription', ''),
                        'status': sg.get('SubnetGroupStatus', ''),
                        'subnets': subnets,
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── DB Parameter Groups ────────────────────────────────────────────
    try:
        paginator = rds.get_paginator('describe_db_parameter_groups')
        for page in paginator.paginate():
            for pg in page.get('DBParameterGroups', []):
                pg_name = pg['DBParameterGroupName']
                pg_arn = pg.get('DBParameterGroupArn', f"arn:aws:rds:{region}:{account_id}:pg:{pg_name}")
                is_default = pg_name.startswith('default.')
                tags = _rds_tags(rds, pg_arn)
                resources.append(make_resource(
                    service='rds',
                    resource_type='db-parameter-group',
                    resource_id=pg_name,
                    arn=pg_arn,
                    name=pg_name,
                    region=region,
                    details={
                        'family': pg.get('DBParameterGroupFamily', ''),
                        'description': pg.get('Description', ''),
                    },
                    tags=tags,
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Option Groups ──────────────────────────────────────────────────
    try:
        paginator = rds.get_paginator('describe_option_groups')
        for page in paginator.paginate():
            for og in page.get('OptionGroupsList', []):
                og_name = og['OptionGroupName']
                og_arn = og.get('OptionGroupArn', f"arn:aws:rds:{region}:{account_id}:og:{og_name}")
                is_default = og_name.startswith('default:')
                tags = _rds_tags(rds, og_arn)
                resources.append(make_resource(
                    service='rds',
                    resource_type='option-group',
                    resource_id=og_name,
                    arn=og_arn,
                    name=og_name,
                    region=region,
                    details={
                        'engine_name': og.get('EngineName', ''),
                        'major_engine_version': og.get('MajorEngineVersion', ''),
                        'description': og.get('OptionGroupDescription', ''),
                        'options_count': len(og.get('Options', [])),
                    },
                    tags=tags,
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── DB Proxies ─────────────────────────────────────────────────────
    try:
        paginator = rds.get_paginator('describe_db_proxies')
        for page in paginator.paginate():
            for proxy in page.get('DBProxies', []):
                proxy_name = proxy['DBProxyName']
                proxy_arn = proxy.get('DBProxyArn', f"arn:aws:rds:{region}:{account_id}:db-proxy:{proxy_name}")
                tags = _rds_tags(rds, proxy_arn)
                resources.append(make_resource(
                    service='rds',
                    resource_type='db-proxy',
                    resource_id=proxy_name,
                    arn=proxy_arn,
                    name=proxy_name,
                    region=region,
                    details={
                        'engine_family': proxy.get('EngineFamily', ''),
                        'status': proxy.get('Status', ''),
                        'vpc_id': proxy.get('VpcId', ''),
                        'endpoint': proxy.get('Endpoint', ''),
                        'role_arn': proxy.get('RoleArn', ''),
                        'require_tls': proxy.get('RequireTLS', False),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
