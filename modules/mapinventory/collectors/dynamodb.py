"""
Map Inventory — DynamoDB Collector
Collects: table, global-table, backup, stream
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_dynamodb_resources(session, region, account_id):
    """Collect DynamoDB resources for a given region."""
    resources = []
    try:
        client = session.client('dynamodb', region_name=region)
    except Exception:
        return resources

    # --- Tables ---
    try:
        table_names = []
        paginator = client.get_paginator('list_tables')
        for page in paginator.paginate():
            table_names.extend(page.get('TableNames', []))

        for table_name in table_names:
            try:
                resp = client.describe_table(TableName=table_name)
                t = resp.get('Table', {})
                t_arn = t.get('TableArn', '')
                stream_spec = t.get('StreamSpecification', {})
                billing = t.get('BillingModeSummary', {})
                billing_mode = billing.get('BillingMode', 'PROVISIONED')
                gsis = t.get('GlobalSecondaryIndexes', [])
                deletion_protection = t.get('DeletionProtectionEnabled', False)

                # Fetch tags
                tags_dict = {}
                try:
                    tags_resp = client.list_tags_of_resource(ResourceArn=t_arn)
                    tags_dict = tags_to_dict(tags_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='dynamodb',
                    resource_type='table',
                    resource_id=table_name,
                    arn=t_arn,
                    name=table_name,
                    region=region,
                    details={
                        'status': t.get('TableStatus', ''),
                        'billing_mode': billing_mode,
                        'item_count': t.get('ItemCount', 0),
                        'size_bytes': t.get('TableSizeBytes', 0),
                        'gsi_count': len(gsis),
                        'stream_enabled': stream_spec.get('StreamEnabled', False),
                        'table_class': t.get('TableClassSummary', {}).get('TableClass', 'STANDARD'),
                        'deletion_protection': deletion_protection,
                    },
                    tags=tags_dict,
                ))
            except Exception:
                pass
    except Exception:
        pass

    # --- Global Tables ---
    try:
        gt_resp = client.list_global_tables()
        for gt in gt_resp.get('GlobalTables', []):
            gt_name = gt.get('GlobalTableName', '')
            replicas = gt.get('ReplicationGroup', [])
            replica_regions = [r.get('RegionName', '') for r in replicas]
            gt_arn = f"arn:aws:dynamodb::{account_id}:global-table/{gt_name}"
            resources.append(make_resource(
                service='dynamodb',
                resource_type='global-table',
                resource_id=gt_name,
                arn=gt_arn,
                name=gt_name,
                region=region,
                details={
                    'replica_regions': replica_regions,
                },
                tags={},
            ))
    except Exception:
        pass

    # --- Backups ---
    try:
        paginator = client.get_paginator('list_backups')
        for page in paginator.paginate():
            for b in page.get('BackupSummaries', []):
                b_name = b.get('BackupName', '')
                b_arn = b.get('BackupArn', '')
                resources.append(make_resource(
                    service='dynamodb',
                    resource_type='backup',
                    resource_id=b_name,
                    arn=b_arn,
                    name=b_name,
                    region=region,
                    details={
                        'table_name': b.get('TableName', ''),
                        'backup_status': b.get('BackupStatus', ''),
                        'backup_type': b.get('BackupType', ''),
                        'backup_size_bytes': b.get('BackupSizeBytes', 0),
                        'backup_creation_datetime': str(b.get('BackupCreationDateTime', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # --- Streams ---
    try:
        streams_client = session.client('dynamodbstreams', region_name=region)
        streams_resp = streams_client.list_streams()
        for s in streams_resp.get('Streams', []):
            stream_arn = s.get('StreamArn', '')
            stream_label = s.get('StreamLabel', '')
            table_name = s.get('TableName', '')
            stream_id = f"{table_name}/{stream_label}"

            try:
                desc_resp = streams_client.describe_stream(StreamArn=stream_arn)
                desc = desc_resp.get('StreamDescription', {})
                resources.append(make_resource(
                    service='dynamodb',
                    resource_type='stream',
                    resource_id=stream_id,
                    arn=stream_arn,
                    name=stream_id,
                    region=region,
                    details={
                        'table_name': table_name,
                        'stream_label': stream_label,
                        'stream_status': desc.get('StreamStatus', ''),
                        'stream_view_type': desc.get('StreamViewType', ''),
                    },
                    tags={},
                ))
            except Exception:
                resources.append(make_resource(
                    service='dynamodb',
                    resource_type='stream',
                    resource_id=stream_id,
                    arn=stream_arn,
                    name=stream_id,
                    region=region,
                    details={
                        'table_name': table_name,
                        'stream_label': stream_label,
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
