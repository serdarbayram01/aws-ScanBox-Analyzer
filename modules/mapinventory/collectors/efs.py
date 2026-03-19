"""
Map Inventory — EFS Collector
Collects: file-system, access-point, replication-configuration
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_efs_resources(session, region, account_id):
    """Collect EFS resources for a given region."""
    resources = []
    try:
        client = session.client('efs', region_name=region)
    except Exception:
        return resources

    # --- File Systems ---
    try:
        paginator = client.get_paginator('describe_file_systems')
        for page in paginator.paginate():
            for fs in page.get('FileSystems', []):
                fs_id = fs.get('FileSystemId', '')
                fs_arn = fs.get('FileSystemArn', '')
                tags_list = fs.get('Tags', [])
                tags_dict = tags_to_dict(tags_list)
                fs_name = get_tag_value(tags_list, 'Name') or fs_id
                size_info = fs.get('SizeInBytes', {})

                resources.append(make_resource(
                    service='efs',
                    resource_type='file-system',
                    resource_id=fs_id,
                    arn=fs_arn,
                    name=fs_name,
                    region=region,
                    details={
                        'lifecycle_state': fs.get('LifeCycleState', ''),
                        'performance_mode': fs.get('PerformanceMode', ''),
                        'throughput_mode': fs.get('ThroughputMode', ''),
                        'size_in_bytes': size_info.get('Value', 0),
                        'number_of_mount_targets': fs.get('NumberOfMountTargets', 0),
                        'encrypted': fs.get('Encrypted', False),
                    },
                    tags=tags_dict,
                ))

                # --- Replication Configurations per file system ---
                try:
                    rep_resp = client.describe_replication_configurations(
                        FileSystemId=fs_id
                    )
                    for rep in rep_resp.get('Replications', []):
                        source_fs_id = rep.get('SourceFileSystemId', '')
                        source_region = rep.get('SourceFileSystemRegion', '')
                        destinations = rep.get('Destinations', [])
                        for dest in destinations:
                            dest_fs_id = dest.get('FileSystemId', '')
                            dest_region = dest.get('Region', '')
                            rep_id = f"{source_fs_id}-to-{dest_fs_id}"
                            resources.append(make_resource(
                                service='efs',
                                resource_type='replication-configuration',
                                resource_id=rep_id,
                                arn=fs_arn,
                                name=rep_id,
                                region=region,
                                details={
                                    'source_file_system_id': source_fs_id,
                                    'source_region': source_region,
                                    'destination_file_system_id': dest_fs_id,
                                    'destination_region': dest_region,
                                    'destination_status': dest.get('Status', ''),
                                },
                                tags={},
                            ))
                except Exception:
                    pass
    except Exception:
        pass

    # --- Access Points ---
    try:
        paginator = client.get_paginator('describe_access_points')
        for page in paginator.paginate():
            for ap in page.get('AccessPoints', []):
                ap_id = ap.get('AccessPointId', '')
                ap_arn = ap.get('AccessPointArn', '')
                ap_tags = tags_to_dict(ap.get('Tags', []))
                ap_name = get_tag_value(ap.get('Tags', []), 'Name') or ap_id
                posix_user = ap.get('PosixUser', {})
                root_dir = ap.get('RootDirectory', {})

                resources.append(make_resource(
                    service='efs',
                    resource_type='access-point',
                    resource_id=ap_id,
                    arn=ap_arn,
                    name=ap_name,
                    region=region,
                    details={
                        'file_system_id': ap.get('FileSystemId', ''),
                        'lifecycle_state': ap.get('LifeCycleState', ''),
                        'posix_user_uid': posix_user.get('Uid', ''),
                        'posix_user_gid': posix_user.get('Gid', ''),
                        'root_directory_path': root_dir.get('Path', '/'),
                    },
                    tags=ap_tags,
                ))
    except Exception:
        pass

    return resources
