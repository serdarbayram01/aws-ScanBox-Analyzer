"""
Map Inventory — ElastiCache Collector
Resource types: cluster, replication-group, serverless-cache, user-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_elasticache_resources(session, region, account_id):
    """Collect all ElastiCache resource types in the given region."""
    resources = []
    try:
        ec = session.client('elasticache', region_name=region)
    except Exception:
        return resources

    # ── Cache Clusters ───────────────────────────────────────────────
    try:
        paginator = ec.get_paginator('describe_cache_clusters')
        for page in paginator.paginate(ShowCacheNodeInfo=True):
            for cluster in page.get('CacheClusters', []):
                cluster_id = cluster.get('CacheClusterId', '')
                cluster_arn = cluster.get('ARN', '')
                if not cluster_arn:
                    cluster_arn = f"arn:aws:elasticache:{region}:{account_id}:cluster:{cluster_id}"
                tags_dict = {}
                try:
                    tag_resp = ec.list_tags_for_resource(ResourceName=cluster_arn)
                    tags_dict = tags_to_dict(tag_resp.get('TagList', []))
                except Exception:
                    pass
                endpoint = cluster.get('ConfigurationEndpoint') or cluster.get('CacheNodes', [{}])[0].get('Endpoint', {}) if cluster.get('CacheNodes') else {}
                resources.append(make_resource(
                    service='elasticache',
                    resource_type='cluster',
                    resource_id=cluster_id,
                    arn=cluster_arn,
                    name=cluster_id,
                    region=region,
                    details={
                        'engine': cluster.get('Engine', ''),
                        'engine_version': cluster.get('EngineVersion', ''),
                        'cache_node_type': cluster.get('CacheNodeType', ''),
                        'num_cache_nodes': cluster.get('NumCacheNodes', 0),
                        'status': cluster.get('CacheClusterStatus', ''),
                        'preferred_az': cluster.get('PreferredAvailabilityZone', ''),
                        'cache_subnet_group': cluster.get('CacheSubnetGroupName', ''),
                        'replication_group_id': cluster.get('ReplicationGroupId', ''),
                        'auto_minor_version_upgrade': cluster.get('AutoMinorVersionUpgrade', False),
                        'transit_encryption_enabled': cluster.get('TransitEncryptionEnabled', False),
                        'at_rest_encryption_enabled': cluster.get('AtRestEncryptionEnabled', False),
                        'endpoint_address': endpoint.get('Address', '') if isinstance(endpoint, dict) else '',
                        'endpoint_port': endpoint.get('Port', '') if isinstance(endpoint, dict) else '',
                        'snapshot_retention_limit': cluster.get('SnapshotRetentionLimit', 0),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Replication Groups ───────────────────────────────────────────
    try:
        paginator = ec.get_paginator('describe_replication_groups')
        for page in paginator.paginate():
            for rg in page.get('ReplicationGroups', []):
                rg_id = rg.get('ReplicationGroupId', '')
                rg_arn = rg.get('ARN', '')
                if not rg_arn:
                    rg_arn = f"arn:aws:elasticache:{region}:{account_id}:replicationgroup:{rg_id}"
                resources.append(make_resource(
                    service='elasticache',
                    resource_type='replication-group',
                    resource_id=rg_id,
                    arn=rg_arn,
                    name=rg.get('Description', rg_id),
                    region=region,
                    details={
                        'status': rg.get('Status', ''),
                        'description': rg.get('Description', ''),
                        'member_clusters': rg.get('MemberClusters', []),
                        'node_groups_count': len(rg.get('NodeGroups', [])),
                        'automatic_failover': rg.get('AutomaticFailover', ''),
                        'multi_az': rg.get('MultiAZ', ''),
                        'cluster_enabled': rg.get('ClusterEnabled', False),
                        'cache_node_type': rg.get('CacheNodeType', ''),
                        'transit_encryption_enabled': rg.get('TransitEncryptionEnabled', False),
                        'at_rest_encryption_enabled': rg.get('AtRestEncryptionEnabled', False),
                        'auth_token_enabled': rg.get('AuthTokenEnabled', False),
                        'snapshot_retention_limit': rg.get('SnapshotRetentionLimit', 0),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Serverless Caches ────────────────────────────────────────────
    try:
        paginator = ec.get_paginator('describe_serverless_caches')
        for page in paginator.paginate():
            for sc in page.get('ServerlessCaches', []):
                sc_name = sc.get('ServerlessCacheName', '')
                sc_arn = sc.get('ARN', '')
                resources.append(make_resource(
                    service='elasticache',
                    resource_type='serverless-cache',
                    resource_id=sc_name,
                    arn=sc_arn,
                    name=sc_name,
                    region=region,
                    details={
                        'engine': sc.get('Engine', ''),
                        'status': sc.get('Status', ''),
                        'major_engine_version': sc.get('MajorEngineVersion', ''),
                        'full_engine_version': sc.get('FullEngineVersion', ''),
                        'description': sc.get('Description', ''),
                        'create_time': str(sc.get('CreateTime', '')),
                        'daily_snapshot_time': sc.get('DailySnapshotTime', ''),
                        'snapshot_retention_limit': sc.get('SnapshotRetentionLimit', 0),
                        'kms_key_id': sc.get('KmsKeyId', ''),
                        'security_group_ids': sc.get('SecurityGroupIds', []),
                        'subnet_ids': sc.get('SubnetIds', []),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── User Groups ──────────────────────────────────────────────────
    try:
        paginator = ec.get_paginator('describe_user_groups')
        for page in paginator.paginate():
            for ug in page.get('UserGroups', []):
                ug_id = ug.get('UserGroupId', '')
                ug_arn = ug.get('ARN', '')
                resources.append(make_resource(
                    service='elasticache',
                    resource_type='user-group',
                    resource_id=ug_id,
                    arn=ug_arn,
                    name=ug_id,
                    region=region,
                    details={
                        'engine': ug.get('Engine', ''),
                        'status': ug.get('Status', ''),
                        'user_ids': ug.get('UserIds', []),
                        'replication_groups': ug.get('ReplicationGroups', []),
                        'serverless_caches': ug.get('ServerlessCaches', []),
                        'minimum_engine_version': ug.get('MinimumEngineVersion', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
