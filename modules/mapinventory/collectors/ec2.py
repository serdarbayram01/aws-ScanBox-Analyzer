"""
Map Inventory — EC2 Collector
Resource types: instance, volume, snapshot, ami, security-group,
                key-pair, elastic-ip, network-interface, placement-group
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ec2_resources(session, region, account_id):
    """Collect all EC2 resource types in the given region."""
    resources = []
    try:
        ec2 = session.client('ec2', region_name=region)
    except Exception:
        return resources

    # ── Instances (with attached EBS disk info) ─────────────────────
    try:
        # First pass: collect all instances and volume IDs
        _instances_raw = []
        _all_vol_ids = []
        paginator = ec2.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page.get('Reservations', []):
                for inst in reservation.get('Instances', []):
                    _instances_raw.append(inst)
                    for bdm in inst.get('BlockDeviceMappings', []):
                        vid = bdm.get('Ebs', {}).get('VolumeId')
                        if vid:
                            _all_vol_ids.append(vid)

        # Batch fetch volume details (single API call)
        _vol_info = {}
        if _all_vol_ids:
            try:
                for i in range(0, len(_all_vol_ids), 200):  # describe_volumes max 200
                    batch = _all_vol_ids[i:i+200]
                    vr = ec2.describe_volumes(VolumeIds=batch)
                    for v in vr.get('Volumes', []):
                        _vol_info[v['VolumeId']] = {
                            'size_gb': v.get('Size', 0),
                            'type': v.get('VolumeType', ''),
                            'encrypted': v.get('Encrypted', False),
                        }
            except Exception:
                pass

        # Batch fetch instance type specs (vCPU, RAM)
        _type_specs = {}
        _unique_types = list({inst['InstanceType'] for inst in _instances_raw if inst.get('InstanceType')})
        if _unique_types:
            try:
                for i in range(0, len(_unique_types), 100):
                    batch = _unique_types[i:i+100]
                    it_resp = ec2.describe_instance_types(InstanceTypes=batch)
                    for it in it_resp.get('InstanceTypes', []):
                        _type_specs[it['InstanceType']] = {
                            'vcpu': it.get('VCpuInfo', {}).get('DefaultVCpus', 0),
                            'ram_gb': round(it.get('MemoryInfo', {}).get('SizeInMiB', 0) / 1024, 1),
                        }
            except Exception:
                pass

        for inst in _instances_raw:
            inst_id = inst['InstanceId']
            tags = inst.get('Tags', [])
            name = get_tag_value(tags, 'Name') or inst_id
            arn = f"arn:aws:ec2:{region}:{account_id}:instance/{inst_id}"

            # Build disk list from BlockDeviceMappings
            disks = []
            total_disk_gb = 0
            for bdm in inst.get('BlockDeviceMappings', []):
                vid = bdm.get('Ebs', {}).get('VolumeId')
                if not vid:
                    continue
                vi = _vol_info.get(vid, {})
                sz = vi.get('size_gb', 0)
                total_disk_gb += sz
                disks.append({
                    'volume_id': vid,
                    'device': bdm.get('DeviceName', ''),
                    'size_gb': sz,
                    'type': vi.get('type', ''),
                    'encrypted': vi.get('encrypted', False),
                })

            specs = _type_specs.get(inst.get('InstanceType', ''), {})
            resources.append(make_resource(
                service='ec2',
                resource_type='instance',
                resource_id=inst_id,
                arn=arn,
                name=name,
                region=region,
                details={
                    'instance_type': inst.get('InstanceType', ''),
                    'state': inst.get('State', {}).get('Name', ''),
                    'vcpu': specs.get('vcpu', 0),
                    'ram_gb': specs.get('ram_gb', 0),
                    'private_ip': inst.get('PrivateIpAddress', ''),
                    'public_ip': inst.get('PublicIpAddress', ''),
                    'vpc_id': inst.get('VpcId', ''),
                    'subnet_id': inst.get('SubnetId', ''),
                    'launch_time': str(inst.get('LaunchTime', '')),
                    'platform': inst.get('PlatformDetails', inst.get('Platform', '')),
                    'architecture': inst.get('Architecture', ''),
                    'disk_count': len(disks),
                    'total_disk_gb': total_disk_gb,
                    'disks': disks,
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Volumes ────────────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_volumes')
        for page in paginator.paginate():
            for vol in page.get('Volumes', []):
                vol_id = vol['VolumeId']
                tags = vol.get('Tags', [])
                name = get_tag_value(tags, 'Name') or vol_id
                arn = f"arn:aws:ec2:{region}:{account_id}:volume/{vol_id}"
                attachments = []
                for att in vol.get('Attachments', []):
                    attachments.append({
                        'instance_id': att.get('InstanceId', ''),
                        'device': att.get('Device', ''),
                        'state': att.get('State', ''),
                    })
                resources.append(make_resource(
                    service='ec2',
                    resource_type='volume',
                    resource_id=vol_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'size_gb': vol.get('Size', 0),
                        'volume_type': vol.get('VolumeType', ''),
                        'state': vol.get('State', ''),
                        'iops': vol.get('Iops', ''),
                        'encrypted': vol.get('Encrypted', False),
                        'availability_zone': vol.get('AvailabilityZone', ''),
                        'attachments': attachments,
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Snapshots ──────────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_snapshots')
        for page in paginator.paginate(OwnerIds=[account_id]):
            for snap in page.get('Snapshots', []):
                snap_id = snap['SnapshotId']
                tags = snap.get('Tags', [])
                name = get_tag_value(tags, 'Name') or snap_id
                arn = f"arn:aws:ec2:{region}:{account_id}:snapshot/{snap_id}"
                resources.append(make_resource(
                    service='ec2',
                    resource_type='snapshot',
                    resource_id=snap_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'volume_size': snap.get('VolumeSize', 0),
                        'state': snap.get('State', ''),
                        'encrypted': snap.get('Encrypted', False),
                        'start_time': str(snap.get('StartTime', '')),
                        'description': snap.get('Description', ''),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── AMIs ───────────────────────────────────────────────────────────
    try:
        resp = ec2.describe_images(Owners=[account_id])
        for img in resp.get('Images', []):
            img_id = img['ImageId']
            tags = img.get('Tags', [])
            name = get_tag_value(tags, 'Name') or img.get('Name', img_id)
            arn = f"arn:aws:ec2:{region}::image/{img_id}"
            resources.append(make_resource(
                service='ec2',
                resource_type='ami',
                resource_id=img_id,
                arn=arn,
                name=name,
                region=region,
                details={
                    'state': img.get('State', ''),
                    'image_type': img.get('ImageType', ''),
                    'architecture': img.get('Architecture', ''),
                    'platform': img.get('PlatformDetails', img.get('Platform', '')),
                    'creation_date': img.get('CreationDate', ''),
                    'public': img.get('Public', False),
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Security Groups ────────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_security_groups')
        for page in paginator.paginate():
            for sg in page.get('SecurityGroups', []):
                sg_id = sg['GroupId']
                tags = sg.get('Tags', [])
                sg_name = sg.get('GroupName', sg_id)
                display_name = get_tag_value(tags, 'Name') or sg_name
                arn = f"arn:aws:ec2:{region}:{account_id}:security-group/{sg_id}"
                resources.append(make_resource(
                    service='ec2',
                    resource_type='security-group',
                    resource_id=sg_id,
                    arn=arn,
                    name=display_name,
                    region=region,
                    details={
                        'vpc_id': sg.get('VpcId', ''),
                        'description': sg.get('Description', ''),
                        'ingress_rules': len(sg.get('IpPermissions', [])),
                        'egress_rules': len(sg.get('IpPermissionsEgress', [])),
                    },
                    tags=tags_to_dict(tags),
                    is_default=(sg_name == 'default'),
                ))
    except Exception:
        pass

    # ── Key Pairs ──────────────────────────────────────────────────────
    try:
        resp = ec2.describe_key_pairs()
        for kp in resp.get('KeyPairs', []):
            kp_id = kp.get('KeyPairId', kp.get('KeyName', ''))
            kp_name = kp.get('KeyName', kp_id)
            tags = kp.get('Tags', [])
            arn = f"arn:aws:ec2:{region}:{account_id}:key-pair/{kp_id}"
            resources.append(make_resource(
                service='ec2',
                resource_type='key-pair',
                resource_id=kp_id,
                arn=arn,
                name=kp_name,
                region=region,
                details={
                    'key_type': kp.get('KeyType', ''),
                    'fingerprint': kp.get('KeyFingerprint', ''),
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Elastic IPs ────────────────────────────────────────────────────
    try:
        resp = ec2.describe_addresses()
        for addr in resp.get('Addresses', []):
            alloc_id = addr.get('AllocationId', addr.get('PublicIp', ''))
            tags = addr.get('Tags', [])
            name = get_tag_value(tags, 'Name') or addr.get('PublicIp', alloc_id)
            arn = f"arn:aws:ec2:{region}:{account_id}:elastic-ip/{alloc_id}"
            resources.append(make_resource(
                service='ec2',
                resource_type='elastic-ip',
                resource_id=alloc_id,
                arn=arn,
                name=name,
                region=region,
                details={
                    'instance_id': addr.get('InstanceId', ''),
                    'association_id': addr.get('AssociationId', ''),
                    'domain': addr.get('Domain', ''),
                    'public_ip': addr.get('PublicIp', ''),
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Network Interfaces ─────────────────────────────────────────────
    try:
        paginator = ec2.get_paginator('describe_network_interfaces')
        for page in paginator.paginate():
            for eni in page.get('NetworkInterfaces', []):
                eni_id = eni['NetworkInterfaceId']
                tags = eni.get('TagSet', [])
                name = get_tag_value(tags, 'Name') or eni.get('Description', eni_id)
                arn = f"arn:aws:ec2:{region}:{account_id}:network-interface/{eni_id}"
                resources.append(make_resource(
                    service='ec2',
                    resource_type='network-interface',
                    resource_id=eni_id,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'vpc_id': eni.get('VpcId', ''),
                        'subnet_id': eni.get('SubnetId', ''),
                        'private_ip': eni.get('PrivateIpAddress', ''),
                        'status': eni.get('Status', ''),
                        'type': eni.get('InterfaceType', ''),
                    },
                    tags=tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Placement Groups ───────────────────────────────────────────────
    try:
        resp = ec2.describe_placement_groups()
        for pg in resp.get('PlacementGroups', []):
            pg_name = pg.get('GroupName', '')
            pg_id = pg.get('GroupId', pg_name)
            tags = pg.get('Tags', [])
            arn = f"arn:aws:ec2:{region}:{account_id}:placement-group/{pg_name}"
            resources.append(make_resource(
                service='ec2',
                resource_type='placement-group',
                resource_id=pg_id,
                arn=arn,
                name=pg_name,
                region=region,
                details={
                    'strategy': pg.get('Strategy', ''),
                    'state': pg.get('State', ''),
                },
                tags=tags_to_dict(tags),
            ))
    except Exception:
        pass

    return resources
