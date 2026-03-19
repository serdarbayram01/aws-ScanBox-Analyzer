"""
Map Inventory — Amazon FSx Collector
Resource types: file-system, backup, volume
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_fsx_resources(session, region, account_id):
    """Collect Amazon FSx file systems, backups, and volumes."""
    resources = []
    try:
        client = session.client('fsx', region_name=region)
    except Exception:
        return resources

    # ── File Systems ──────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_file_systems(**kwargs)
            for fs in resp.get('FileSystems', []):
                fs_id = fs.get('FileSystemId', '')
                fs_arn = fs.get('ResourceARN', f"arn:aws:fsx:{region}:{account_id}:file-system/{fs_id}")
                tags_list = fs.get('Tags', [])
                name = get_tag_value(tags_list, 'Name') or fs_id
                fs_type = fs.get('FileSystemType', '')

                details = {
                    'file_system_type': fs_type,
                    'lifecycle': fs.get('Lifecycle', ''),
                    'storage_capacity_gb': fs.get('StorageCapacity', 0),
                    'storage_type': fs.get('StorageType', ''),
                    'vpc_id': fs.get('VpcId', ''),
                    'subnet_ids': fs.get('SubnetIds', []),
                    'dns_name': fs.get('DNSName', ''),
                    'kms_key_id': fs.get('KmsKeyId', ''),
                    'creation_time': str(fs.get('CreationTime', '')),
                }

                # Add type-specific details
                if fs_type == 'LUSTRE':
                    lustre = fs.get('LustreConfiguration', {})
                    details['lustre_deployment_type'] = lustre.get('DeploymentType', '')
                    details['lustre_data_compression'] = lustre.get('DataCompressionType', '')
                elif fs_type == 'WINDOWS':
                    windows = fs.get('WindowsConfiguration', {})
                    details['windows_deployment_type'] = windows.get('DeploymentType', '')
                    details['windows_throughput_capacity'] = windows.get('ThroughputCapacity', 0)
                elif fs_type == 'ONTAP':
                    ontap = fs.get('OntapConfiguration', {})
                    details['ontap_deployment_type'] = ontap.get('DeploymentType', '')
                    details['ontap_throughput_capacity'] = ontap.get('ThroughputCapacity', 0)
                    details['ontap_endpoint_ip_range'] = ontap.get('EndpointIpAddressRange', '')
                elif fs_type == 'OPENZFS':
                    zfs = fs.get('OpenZFSConfiguration', {})
                    details['openzfs_deployment_type'] = zfs.get('DeploymentType', '')
                    details['openzfs_throughput_capacity'] = zfs.get('ThroughputCapacity', 0)

                resources.append(make_resource(
                    service='fsx',
                    resource_type='file-system',
                    resource_id=fs_id,
                    arn=fs_arn,
                    name=name,
                    region=region,
                    details=details,
                    tags=tags_to_dict(tags_list),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Backups ───────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_backups(**kwargs)
            for bk in resp.get('Backups', []):
                bk_id = bk.get('BackupId', '')
                bk_arn = bk.get('ResourceARN', f"arn:aws:fsx:{region}:{account_id}:backup/{bk_id}")
                tags_list = bk.get('Tags', [])
                name = get_tag_value(tags_list, 'Name') or bk_id
                fs_info = bk.get('FileSystem', {})

                resources.append(make_resource(
                    service='fsx',
                    resource_type='backup',
                    resource_id=bk_id,
                    arn=bk_arn,
                    name=name,
                    region=region,
                    details={
                        'lifecycle': bk.get('Lifecycle', ''),
                        'type': bk.get('Type', ''),
                        'creation_time': str(bk.get('CreationTime', '')),
                        'file_system_id': fs_info.get('FileSystemId', ''),
                        'file_system_type': fs_info.get('FileSystemType', ''),
                        'progress_percent': bk.get('ProgressPercent', 0),
                        'volume_id': bk.get('Volume', {}).get('VolumeId', ''),
                    },
                    tags=tags_to_dict(tags_list),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Volumes ───────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.describe_volumes(**kwargs)
            for vol in resp.get('Volumes', []):
                vol_id = vol.get('VolumeId', '')
                vol_arn = vol.get('ResourceARN', f"arn:aws:fsx:{region}:{account_id}:volume/{vol_id}")
                tags_list = vol.get('Tags', [])
                vol_name = vol.get('Name', get_tag_value(tags_list, 'Name') or vol_id)
                vol_type = vol.get('VolumeType', '')

                details = {
                    'volume_type': vol_type,
                    'lifecycle': vol.get('Lifecycle', ''),
                    'file_system_id': vol.get('FileSystemId', ''),
                    'creation_time': str(vol.get('CreationTime', '')),
                }

                if vol_type == 'ONTAP':
                    ontap = vol.get('OntapConfiguration', {})
                    details['ontap_junction_path'] = ontap.get('JunctionPath', '')
                    details['ontap_size_in_megabytes'] = ontap.get('SizeInMegabytes', 0)
                    details['ontap_storage_efficiency'] = ontap.get('StorageEfficiencyEnabled', False)
                    details['ontap_storage_virtual_machine_id'] = ontap.get('StorageVirtualMachineId', '')
                    details['ontap_tiering_policy'] = ontap.get('TieringPolicy', {}).get('Name', '')
                elif vol_type == 'OPENZFS':
                    zfs = vol.get('OpenZFSConfiguration', {})
                    details['openzfs_parent_volume_id'] = zfs.get('ParentVolumeId', '')
                    details['openzfs_storage_capacity_quota_gib'] = zfs.get('StorageCapacityQuotaGiB', 0)
                    details['openzfs_storage_capacity_reservation_gib'] = zfs.get('StorageCapacityReservationGiB', 0)
                    details['openzfs_data_compression'] = zfs.get('DataCompressionType', '')
                    details['openzfs_read_only'] = zfs.get('ReadOnly', False)

                resources.append(make_resource(
                    service='fsx',
                    resource_type='volume',
                    resource_id=vol_id,
                    arn=vol_arn,
                    name=vol_name,
                    region=region,
                    details=details,
                    tags=tags_to_dict(tags_list),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
