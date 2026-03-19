"""
Map Inventory — AWS CloudHSM v2 Collector
Resource types: cluster, hsm
"""

from .base import make_resource, tags_to_dict


def collect_cloudhsmv2_resources(session, region, account_id):
    """Collect CloudHSM v2 clusters and HSMs in the given region."""
    resources = []
    try:
        client = session.client('cloudhsmv2', region_name=region)
    except Exception:
        return resources

    # ── Clusters & HSMs ──────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for c in page.get('Clusters', []):
                cluster_id = c.get('ClusterId', '')
                tags_dict = tags_to_dict(c.get('TagList', []))
                resources.append(make_resource(
                    service='cloudhsmv2',
                    resource_type='cluster',
                    resource_id=cluster_id,
                    arn=f'arn:aws:cloudhsmv2:{region}:{account_id}:cluster/{cluster_id}',
                    name=tags_dict.get('Name', cluster_id),
                    region=region,
                    details={
                        'state': c.get('State', ''),
                        'state_message': c.get('StateMessage', ''),
                        'hsm_type': c.get('HsmType', ''),
                        'vpc_id': c.get('VpcId', ''),
                        'subnet_mapping': str(c.get('SubnetMapping', {})),
                        'security_group': c.get('SecurityGroup', ''),
                        'backup_policy': c.get('BackupPolicy', ''),
                        'backup_retention': str(c.get('BackupRetentionPolicy', {})),
                        'create_timestamp': str(c.get('CreateTimestamp', '')),
                    },
                    tags=tags_dict,
                ))

                # ── HSMs within this cluster ─────────────────────────
                for hsm in c.get('Hsms', []):
                    hsm_id = hsm.get('HsmId', '')
                    resources.append(make_resource(
                        service='cloudhsmv2',
                        resource_type='hsm',
                        resource_id=hsm_id,
                        arn=hsm.get('EniId', ''),
                        name=hsm_id,
                        region=region,
                        details={
                            'cluster_id': cluster_id,
                            'availability_zone': hsm.get('AvailabilityZone', ''),
                            'subnet_id': hsm.get('SubnetId', ''),
                            'eni_id': hsm.get('EniId', ''),
                            'eni_ip': hsm.get('EniIp', ''),
                            'state': hsm.get('State', ''),
                            'state_message': hsm.get('StateMessage', ''),
                        },
                    ))
    except Exception:
        pass

    return resources
