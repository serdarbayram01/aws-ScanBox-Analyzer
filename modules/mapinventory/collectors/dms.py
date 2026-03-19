"""
Map Inventory — DMS (Database Migration Service) Collector
Resource types: replication-instance, replication-task, endpoint, replication-subnet-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_dms_resources(session, region, account_id):
    """Collect all DMS resource types in the given region."""
    resources = []
    try:
        client = session.client('dms', region_name=region)
    except Exception:
        return resources

    # ── Replication Instances ────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_replication_instances')
        for page in paginator.paginate():
            for ri in page.get('ReplicationInstances', []):
                ri_id = ri.get('ReplicationInstanceIdentifier', '')
                ri_arn = ri.get('ReplicationInstanceArn', '')
                # Fetch tags
                ri_tags = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=ri_arn)
                    ri_tags = tag_resp.get('TagList', [])
                except Exception:
                    pass
                resources.append(make_resource(
                    service='dms',
                    resource_type='replication-instance',
                    resource_id=ri_id,
                    arn=ri_arn,
                    name=ri_id,
                    region=region,
                    details={
                        'instance_class': ri.get('ReplicationInstanceClass', ''),
                        'engine_version': ri.get('EngineVersion', ''),
                        'status': ri.get('ReplicationInstanceStatus', ''),
                        'allocated_storage': ri.get('AllocatedStorage', 0),
                        'multi_az': ri.get('MultiAZ', False),
                        'publicly_accessible': ri.get('PubliclyAccessible', False),
                        'availability_zone': ri.get('AvailabilityZone', ''),
                        'vpc_security_groups': [
                            sg.get('VpcSecurityGroupId', '')
                            for sg in ri.get('VpcSecurityGroups', [])
                        ],
                    },
                    tags=tags_to_dict(ri_tags),
                ))
    except Exception:
        pass

    # ── Replication Tasks ────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_replication_tasks')
        for page in paginator.paginate():
            for task in page.get('ReplicationTasks', []):
                task_id = task.get('ReplicationTaskIdentifier', '')
                task_arn = task.get('ReplicationTaskArn', '')
                # Fetch tags
                task_tags = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=task_arn)
                    task_tags = tag_resp.get('TagList', [])
                except Exception:
                    pass
                resources.append(make_resource(
                    service='dms',
                    resource_type='replication-task',
                    resource_id=task_id,
                    arn=task_arn,
                    name=task_id,
                    region=region,
                    details={
                        'status': task.get('Status', ''),
                        'migration_type': task.get('MigrationType', ''),
                        'source_endpoint_arn': task.get('SourceEndpointArn', ''),
                        'target_endpoint_arn': task.get('TargetEndpointArn', ''),
                        'replication_instance_arn': task.get('ReplicationInstanceArn', ''),
                        'table_mappings': task.get('TableMappings', ''),
                        'last_failure_message': task.get('LastFailureMessage', ''),
                    },
                    tags=tags_to_dict(task_tags),
                ))
    except Exception:
        pass

    # ── Endpoints ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_endpoints')
        for page in paginator.paginate():
            for ep in page.get('Endpoints', []):
                ep_id = ep.get('EndpointIdentifier', '')
                ep_arn = ep.get('EndpointArn', '')
                # Fetch tags
                ep_tags = []
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=ep_arn)
                    ep_tags = tag_resp.get('TagList', [])
                except Exception:
                    pass
                resources.append(make_resource(
                    service='dms',
                    resource_type='endpoint',
                    resource_id=ep_id,
                    arn=ep_arn,
                    name=ep_id,
                    region=region,
                    details={
                        'endpoint_type': ep.get('EndpointType', ''),
                        'engine_name': ep.get('EngineName', ''),
                        'server_name': ep.get('ServerName', ''),
                        'port': ep.get('Port', 0),
                        'database_name': ep.get('DatabaseName', ''),
                        'status': ep.get('Status', ''),
                        'ssl_mode': ep.get('SslMode', ''),
                        'kms_key_id': ep.get('KmsKeyId', ''),
                    },
                    tags=tags_to_dict(ep_tags),
                ))
    except Exception:
        pass

    # ── Replication Subnet Groups ────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_replication_subnet_groups')
        for page in paginator.paginate():
            for sg in page.get('ReplicationSubnetGroups', []):
                sg_id = sg.get('ReplicationSubnetGroupIdentifier', '')
                # DMS subnet groups don't have a direct ARN field; construct one
                sg_arn = f"arn:aws:dms:{region}:{account_id}:subgrp:{sg_id}"
                resources.append(make_resource(
                    service='dms',
                    resource_type='replication-subnet-group',
                    resource_id=sg_id,
                    arn=sg_arn,
                    name=sg_id,
                    region=region,
                    details={
                        'description': sg.get('ReplicationSubnetGroupDescription', ''),
                        'vpc_id': sg.get('VpcId', ''),
                        'subnet_group_status': sg.get('SubnetGroupStatus', ''),
                        'subnets': [
                            s.get('SubnetIdentifier', '')
                            for s in sg.get('Subnets', [])
                        ],
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
