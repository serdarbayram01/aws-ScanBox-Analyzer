"""
Map Inventory — Lightsail Collector
Resource types: instance, disk, load-balancer, database, distribution,
                bucket, container-service, static-ip, domain, certificate,
                key-pair
"""

from .base import make_resource, tags_to_dict, get_tag_value


def _ls_tags_to_dict(tags_list):
    """Lightsail tags use {'key': k, 'value': v} (lowercase) instead of {'Key': k, 'Value': v}."""
    if not tags_list:
        return {}
    result = {}
    for t in tags_list:
        if isinstance(t, dict):
            k = t.get('key', '')
            v = t.get('value', '')
            if k:
                result[k] = v
    return result


def collect_lightsail_resources(session, region, account_id):
    """Collect Lightsail resources for a given region."""
    resources = []
    try:
        client = session.client('lightsail', region_name=region)
    except Exception:
        return resources

    # ── Instances ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_instances')
        for page in paginator.paginate():
            for inst in page.get('instances', []):
                inst_name = inst.get('name', '')
                inst_arn = inst.get('arn', '')
                tags = inst.get('tags', [])
                resources.append(make_resource(
                    service='lightsail',
                    resource_type='instance',
                    resource_id=inst_name,
                    arn=inst_arn,
                    name=inst_name,
                    region=region,
                    details={
                        'state': inst.get('state', {}).get('name', ''),
                        'blueprint_id': inst.get('blueprintId', ''),
                        'blueprint_name': inst.get('blueprintName', ''),
                        'bundle_id': inst.get('bundleId', ''),
                        'public_ip': inst.get('publicIpAddress', ''),
                        'private_ip': inst.get('privateIpAddress', ''),
                        'ipv6_addresses': inst.get('ipv6Addresses', []),
                        'is_static_ip': inst.get('isStaticIp', False),
                        'created_at': str(inst.get('createdAt', '')),
                        'hardware': {
                            'cpus': inst.get('hardware', {}).get('cpuCount', 0),
                            'ram_gb': inst.get('hardware', {}).get('ramSizeInGb', 0),
                            'disks': len(inst.get('hardware', {}).get('disks', [])),
                        },
                    },
                    tags=_ls_tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Disks ─────────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_disks')
        for page in paginator.paginate():
            for disk in page.get('disks', []):
                disk_name = disk.get('name', '')
                disk_arn = disk.get('arn', '')
                tags = disk.get('tags', [])
                resources.append(make_resource(
                    service='lightsail',
                    resource_type='disk',
                    resource_id=disk_name,
                    arn=disk_arn,
                    name=disk_name,
                    region=region,
                    details={
                        'size_gb': disk.get('sizeInGb', 0),
                        'state': disk.get('state', ''),
                        'is_attached': disk.get('isAttached', False),
                        'attached_to': disk.get('attachedTo', ''),
                        'path': disk.get('path', ''),
                        'is_system_disk': disk.get('isSystemDisk', False),
                        'created_at': str(disk.get('createdAt', '')),
                    },
                    tags=_ls_tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Load Balancers ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_load_balancers')
        for page in paginator.paginate():
            for lb in page.get('loadBalancers', []):
                lb_name = lb.get('name', '')
                lb_arn = lb.get('arn', '')
                tags = lb.get('tags', [])
                resources.append(make_resource(
                    service='lightsail',
                    resource_type='load-balancer',
                    resource_id=lb_name,
                    arn=lb_arn,
                    name=lb_name,
                    region=region,
                    details={
                        'state': lb.get('state', ''),
                        'dns_name': lb.get('dnsName', ''),
                        'protocol': lb.get('protocol', ''),
                        'public_ports': lb.get('publicPorts', []),
                        'health_check_path': lb.get('healthCheckPath', ''),
                        'instance_port': lb.get('instancePort', 0),
                        'instance_count': len(lb.get('instanceHealthSummary', [])),
                        'created_at': str(lb.get('createdAt', '')),
                    },
                    tags=_ls_tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Relational Databases ──────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_relational_databases')
        for page in paginator.paginate():
            for db in page.get('relationalDatabases', []):
                db_name = db.get('name', '')
                db_arn = db.get('arn', '')
                tags = db.get('tags', [])
                resources.append(make_resource(
                    service='lightsail',
                    resource_type='database',
                    resource_id=db_name,
                    arn=db_arn,
                    name=db_name,
                    region=region,
                    details={
                        'state': db.get('state', ''),
                        'engine': db.get('engine', ''),
                        'engine_version': db.get('engineVersion', ''),
                        'bundle_id': db.get('relationalDatabaseBundleId', ''),
                        'master_username': db.get('masterUsername', ''),
                        'master_database_name': db.get('masterDatabaseName', ''),
                        'publicly_accessible': db.get('publiclyAccessible', False),
                        'backup_retention_enabled': db.get('backupRetentionEnabled', False),
                        'created_at': str(db.get('createdAt', '')),
                    },
                    tags=_ls_tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Distributions ─────────────────────────────────────────────────
    try:
        resp = client.get_distributions()
        for dist in resp.get('distributions', []):
            dist_name = dist.get('name', '')
            dist_arn = dist.get('arn', '')
            tags = dist.get('tags', [])
            resources.append(make_resource(
                service='lightsail',
                resource_type='distribution',
                resource_id=dist_name,
                arn=dist_arn,
                name=dist_name,
                region=region,
                details={
                    'status': dist.get('status', ''),
                    'domain_name': dist.get('domainName', ''),
                    'bundle_id': dist.get('bundleId', ''),
                    'origin': dist.get('origin', {}).get('name', ''),
                    'origin_protocol_policy': dist.get('origin', {}).get('protocolPolicy', ''),
                    'is_enabled': dist.get('isEnabled', False),
                    'certificate_name': dist.get('certificateName', ''),
                    'created_at': str(dist.get('createdAt', '')),
                },
                tags=_ls_tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Buckets ───────────────────────────────────────────────────────
    try:
        resp = client.get_buckets()
        for bkt in resp.get('buckets', []):
            bkt_name = bkt.get('name', '')
            bkt_arn = bkt.get('arn', '')
            tags = bkt.get('tags', [])
            access = bkt.get('accessRules', {})
            resources.append(make_resource(
                service='lightsail',
                resource_type='bucket',
                resource_id=bkt_name,
                arn=bkt_arn,
                name=bkt_name,
                region=region,
                details={
                    'state': bkt.get('state', {}).get('code', ''),
                    'url': bkt.get('url', ''),
                    'bundle_id': bkt.get('bundleId', ''),
                    'access_public': access.get('getObject', ''),
                    'allow_public_overrides': access.get('allowPublicOverrides', False),
                    'object_versioning': bkt.get('objectVersioning', ''),
                    'able_to_update_bundle': bkt.get('ableToUpdateBundle', False),
                    'created_at': str(bkt.get('createdAt', '')),
                },
                tags=_ls_tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Container Services ────────────────────────────────────────────
    try:
        resp = client.get_container_services()
        for cs in resp.get('containerServices', []):
            cs_name = cs.get('containerServiceName', '')
            cs_arn = cs.get('arn', '')
            tags = cs.get('tags', [])
            resources.append(make_resource(
                service='lightsail',
                resource_type='container-service',
                resource_id=cs_name,
                arn=cs_arn,
                name=cs_name,
                region=region,
                details={
                    'state': cs.get('state', ''),
                    'power': cs.get('power', ''),
                    'scale': cs.get('scale', 0),
                    'is_disabled': cs.get('isDisabled', False),
                    'url': cs.get('url', ''),
                    'principal_arn': cs.get('principalArn', ''),
                    'created_at': str(cs.get('createdAt', '')),
                },
                tags=_ls_tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Static IPs ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_static_ips')
        for page in paginator.paginate():
            for sip in page.get('staticIps', []):
                sip_name = sip.get('name', '')
                sip_arn = sip.get('arn', '')
                resources.append(make_resource(
                    service='lightsail',
                    resource_type='static-ip',
                    resource_id=sip_name,
                    arn=sip_arn,
                    name=sip_name,
                    region=region,
                    details={
                        'ip_address': sip.get('ipAddress', ''),
                        'attached_to': sip.get('attachedTo', ''),
                        'is_attached': sip.get('isAttached', False),
                        'created_at': str(sip.get('createdAt', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Domains ───────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_domains')
        for page in paginator.paginate():
            for dom in page.get('domains', []):
                dom_name = dom.get('name', '')
                dom_arn = dom.get('arn', '')
                tags = dom.get('tags', [])
                resources.append(make_resource(
                    service='lightsail',
                    resource_type='domain',
                    resource_id=dom_name,
                    arn=dom_arn,
                    name=dom_name,
                    region=region,
                    details={
                        'domain_entries': len(dom.get('domainEntries', [])),
                        'registered_domain_delegation_info': bool(
                            dom.get('registeredDomainDelegationInfo', {})
                        ),
                        'created_at': str(dom.get('createdAt', '')),
                    },
                    tags=_ls_tags_to_dict(tags),
                ))
    except Exception:
        pass

    # ── Certificates ──────────────────────────────────────────────────
    try:
        resp = client.get_certificates()
        for cert_summary in resp.get('certificates', []):
            cert = cert_summary.get('certificateDetail', cert_summary)
            cert_name = cert.get('name', cert_summary.get('certificateName', ''))
            cert_arn = cert.get('arn', cert_summary.get('certificateArn', ''))
            tags = cert.get('tags', [])
            resources.append(make_resource(
                service='lightsail',
                resource_type='certificate',
                resource_id=cert_name,
                arn=cert_arn,
                name=cert_name,
                region=region,
                details={
                    'domain_name': cert.get('domainName', ''),
                    'status': cert.get('status', ''),
                    'subject_alternative_names': cert.get('subjectAlternativeNames', []),
                    'not_before': str(cert.get('notBefore', '')),
                    'not_after': str(cert.get('notAfter', '')),
                    'in_use': cert.get('inUseResourceCount', 0),
                    'created_at': str(cert.get('createdAt', '')),
                },
                tags=_ls_tags_to_dict(tags),
            ))
    except Exception:
        pass

    # ── Key Pairs ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_key_pairs')
        for page in paginator.paginate():
            for kp in page.get('keyPairs', []):
                kp_name = kp.get('name', '')
                kp_arn = kp.get('arn', '')
                tags = kp.get('tags', [])
                resources.append(make_resource(
                    service='lightsail',
                    resource_type='key-pair',
                    resource_id=kp_name,
                    arn=kp_arn,
                    name=kp_name,
                    region=region,
                    details={
                        'fingerprint': kp.get('fingerprint', ''),
                        'created_at': str(kp.get('createdAt', '')),
                    },
                    tags=_ls_tags_to_dict(tags),
                ))
    except Exception:
        pass

    return resources
