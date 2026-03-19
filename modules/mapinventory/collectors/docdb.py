"""
Map Inventory — Amazon DocumentDB Collector
Resource types: cluster, instance
Filters by engine='docdb' to avoid overlap with RDS/Neptune.
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_docdb_resources(session, region, account_id):
    """Collect DocumentDB clusters and instances."""
    resources = []
    try:
        client = session.client('docdb', region_name=region)
    except Exception:
        return resources

    # ── Clusters ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_db_clusters')
        for page in paginator.paginate():
            for cluster in page.get('DBClusters', []):
                if cluster.get('Engine', '') != 'docdb':
                    continue
                cluster_id = cluster.get('DBClusterIdentifier', '')
                cluster_arn = cluster.get('DBClusterArn', '')
                tags_list = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceName=cluster_arn)
                    tags_list = tag_resp.get('TagList', [])
                except Exception:
                    pass
                resources.append(make_resource(
                    service='docdb',
                    resource_type='cluster',
                    resource_id=cluster_id,
                    arn=cluster_arn,
                    name=cluster_id,
                    region=region,
                    details={
                        'engine': cluster.get('Engine', ''),
                        'engine_version': cluster.get('EngineVersion', ''),
                        'status': cluster.get('Status', ''),
                        'multi_az': cluster.get('MultiAZ', False),
                        'storage_encrypted': cluster.get('StorageEncrypted', False),
                        'endpoint': cluster.get('Endpoint', ''),
                        'reader_endpoint': cluster.get('ReaderEndpoint', ''),
                        'port': cluster.get('Port', 0),
                        'db_subnet_group': cluster.get('DBSubnetGroup', ''),
                        'deletion_protection': cluster.get('DeletionProtection', False),
                        'backup_retention_period': cluster.get('BackupRetentionPeriod', 0),
                        'cluster_members': [m.get('DBInstanceIdentifier', '') for m in cluster.get('DBClusterMembers', [])],
                    },
                    tags=tags_to_dict(tags_list),
                ))
    except Exception:
        pass

    # ── Instances ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for inst in page.get('DBInstances', []):
                if inst.get('Engine', '') != 'docdb':
                    continue
                inst_id = inst.get('DBInstanceIdentifier', '')
                inst_arn = inst.get('DBInstanceArn', '')
                tags_list = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceName=inst_arn)
                    tags_list = tag_resp.get('TagList', [])
                except Exception:
                    pass
                resources.append(make_resource(
                    service='docdb',
                    resource_type='instance',
                    resource_id=inst_id,
                    arn=inst_arn,
                    name=inst_id,
                    region=region,
                    details={
                        'engine': inst.get('Engine', ''),
                        'engine_version': inst.get('EngineVersion', ''),
                        'instance_class': inst.get('DBInstanceClass', ''),
                        'status': inst.get('DBInstanceStatus', ''),
                        'cluster_identifier': inst.get('DBClusterIdentifier', ''),
                        'availability_zone': inst.get('AvailabilityZone', ''),
                        'endpoint': inst.get('Endpoint', {}).get('Address', ''),
                        'port': inst.get('Endpoint', {}).get('Port', 0),
                        'auto_minor_version_upgrade': inst.get('AutoMinorVersionUpgrade', False),
                        'publicly_accessible': inst.get('PubliclyAccessible', False),
                        'ca_certificate_identifier': inst.get('CACertificateIdentifier', ''),
                    },
                    tags=tags_to_dict(tags_list),
                ))
    except Exception:
        pass

    return resources
