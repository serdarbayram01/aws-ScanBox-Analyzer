"""
Map Inventory — Amazon Keyspaces (for Apache Cassandra) Collector
Resource types: keyspace, table
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_keyspaces_resources(session, region, account_id):
    """Collect Amazon Keyspaces resources in the given region."""
    resources = []
    try:
        client = session.client('keyspaces', region_name=region)
    except Exception:
        return resources

    # ── Keyspaces ────────────────────────────────────────────────────
    keyspace_names = []
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_keyspaces(**kwargs)
            for ks in resp.get('keyspaces', []):
                ks_name = ks.get('keyspaceName', '')
                ks_arn = ks.get('resourceArn', '')
                keyspace_names.append(ks_name)

                # Get tags
                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=ks_arn)
                    tag_list = tag_resp.get('tags', [])
                    tags = tags_to_dict(tag_list)
                except Exception:
                    pass

                # Determine if system keyspace
                is_system = ks_name.startswith('system')

                resources.append(make_resource(
                    service='keyspaces',
                    resource_type='keyspace',
                    resource_id=ks_name,
                    arn=ks_arn,
                    name=ks_name,
                    region=region,
                    details={
                        'replication_strategy': ks.get('replicationStrategy', ''),
                        'replication_regions': ks.get('replicationRegions', []),
                    },
                    tags=tags,
                    is_default=is_system,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Tables per Keyspace ──────────────────────────────────────────
    for ks_name in keyspace_names:
        # Skip system keyspaces for table enumeration
        if ks_name.startswith('system'):
            continue
        try:
            next_token = None
            while True:
                kwargs = {'keyspaceName': ks_name}
                if next_token:
                    kwargs['nextToken'] = next_token
                resp = client.list_tables(**kwargs)
                for tbl in resp.get('tables', []):
                    tbl_name = tbl.get('tableName', '')
                    tbl_arn = tbl.get('resourceArn', '')

                    # Get table details
                    details = {
                        'keyspace_name': ks_name,
                    }
                    try:
                        tbl_detail = client.get_table(
                            keyspaceName=ks_name,
                            tableName=tbl_name
                        )
                        details.update({
                            'status': tbl_detail.get('status', ''),
                            'creation_timestamp': str(tbl_detail.get('creationTimestamp', '')),
                            'default_time_to_live': tbl_detail.get('defaultTimeToLive', 0),
                            'point_in_time_recovery': tbl_detail.get('pointInTimeRecovery', {}).get('status', ''),
                            'encryption_type': tbl_detail.get('encryptionSpecification', {}).get('type', ''),
                            'kms_key_identifier': tbl_detail.get('encryptionSpecification', {}).get('kmsKeyIdentifier', ''),
                            'capacity_mode': tbl_detail.get('capacitySpecification', {}).get('capacityMode', ''),
                            'throughput_mode': tbl_detail.get('capacitySpecification', {}).get('throughputMode', ''),
                        })
                    except Exception:
                        pass

                    # Get tags
                    tags = {}
                    try:
                        tag_resp = client.list_tags_for_resource(resourceArn=tbl_arn)
                        tag_list = tag_resp.get('tags', [])
                        tags = tags_to_dict(tag_list)
                    except Exception:
                        pass

                    resources.append(make_resource(
                        service='keyspaces',
                        resource_type='table',
                        resource_id=f"{ks_name}/{tbl_name}",
                        arn=tbl_arn,
                        name=tbl_name,
                        region=region,
                        details=details,
                        tags=tags,
                    ))
                next_token = resp.get('nextToken')
                if not next_token:
                    break
        except Exception:
            pass

    return resources
