"""
Map Inventory — Amazon MSK (Managed Streaming for Apache Kafka) Collector
Resource types: cluster, serverless-cluster, configuration
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_kafka_resources(session, region, account_id):
    """Collect Amazon MSK resources in the given region."""
    resources = []
    try:
        client = session.client('kafka', region_name=region)
    except Exception:
        return resources

    # ── Provisioned Clusters ─────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_clusters')
        for page in paginator.paginate():
            for cluster in page.get('ClusterInfoList', []):
                cluster_name = cluster.get('ClusterName', '')
                cluster_arn = cluster.get('ClusterArn', '')
                state = cluster.get('State', '')
                created = str(cluster.get('CreationTime', ''))

                tags = cluster.get('Tags', {})

                broker_info = cluster.get('BrokerNodeGroupInfo', {})
                encryption = cluster.get('EncryptionInfo', {})
                enc_in_transit = encryption.get('EncryptionInTransit', {})

                resources.append(make_resource(
                    service='kafka',
                    resource_type='cluster',
                    resource_id=cluster_name,
                    arn=cluster_arn,
                    name=cluster_name,
                    region=region,
                    details={
                        'state': state,
                        'kafka_version': cluster.get('CurrentBrokerSoftwareInfo', {}).get('KafkaVersion', ''),
                        'number_of_broker_nodes': cluster.get('NumberOfBrokerNodes', 0),
                        'instance_type': broker_info.get('InstanceType', ''),
                        'client_subnets': broker_info.get('ClientSubnets', []),
                        'security_groups': broker_info.get('SecurityGroups', []),
                        'storage_volume_size': broker_info.get('StorageInfo', {}).get('EbsStorageInfo', {}).get('VolumeSize', 0),
                        'encryption_at_rest_kms_key': encryption.get('EncryptionAtRest', {}).get('DataVolumeKMSKeyId', ''),
                        'encryption_in_transit_client': enc_in_transit.get('ClientBroker', ''),
                        'encryption_in_transit_in_cluster': enc_in_transit.get('InCluster', False),
                        'enhanced_monitoring': cluster.get('EnhancedMonitoring', ''),
                        'creation_time': created,
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Serverless Clusters ──────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_clusters_v2')
        for page in paginator.paginate():
            for cluster in page.get('ClusterInfoList', []):
                # Only process serverless clusters here (provisioned handled above)
                if cluster.get('ClusterType', '') != 'SERVERLESS':
                    continue
                cluster_name = cluster.get('ClusterName', '')
                cluster_arn = cluster.get('ClusterArn', '')
                state = cluster.get('State', '')
                created = str(cluster.get('CreationTime', ''))

                tags = cluster.get('Tags', {})

                serverless = cluster.get('Serverless', {})
                vpc_configs = serverless.get('VpcConfigs', [])

                resources.append(make_resource(
                    service='kafka',
                    resource_type='serverless-cluster',
                    resource_id=cluster_name,
                    arn=cluster_arn,
                    name=cluster_name,
                    region=region,
                    details={
                        'state': state,
                        'creation_time': created,
                        'vpc_config_count': len(vpc_configs),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Configurations ───────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_configurations')
        for page in paginator.paginate():
            for config in page.get('Configurations', []):
                config_name = config.get('Name', '')
                config_arn = config.get('Arn', '')
                state = config.get('State', '')
                created = str(config.get('CreationTime', ''))

                latest = config.get('LatestRevision', {})

                resources.append(make_resource(
                    service='kafka',
                    resource_type='configuration',
                    resource_id=config_name,
                    arn=config_arn,
                    name=config_name,
                    region=region,
                    details={
                        'state': state,
                        'description': config.get('Description', ''),
                        'kafka_versions': config.get('KafkaVersions', []),
                        'latest_revision': latest.get('Revision', 0),
                        'latest_revision_description': latest.get('Description', ''),
                        'creation_time': created,
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
