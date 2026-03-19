"""
Map Inventory — Amazon MQ Collector
Resource types: broker, configuration
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_mq_resources(session, region, account_id):
    """Collect Amazon MQ brokers and configurations."""
    resources = []
    try:
        client = session.client('mq', region_name=region)
    except Exception:
        return resources

    # ── Brokers ───────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_brokers(**kwargs)
            for summary in resp.get('BrokerSummaries', []):
                broker_id = summary.get('BrokerId', '')
                broker_name = summary.get('BrokerName', broker_id)
                broker_arn = summary.get('BrokerArn', '')
                # Get full details for tags and metadata
                try:
                    detail = client.describe_broker(BrokerId=broker_id)
                    tags = detail.get('Tags', {})
                    resources.append(make_resource(
                        service='mq',
                        resource_type='broker',
                        resource_id=broker_id,
                        arn=broker_arn,
                        name=broker_name,
                        region=region,
                        details={
                            'engine_type': detail.get('EngineType', ''),
                            'engine_version': detail.get('EngineVersion', ''),
                            'host_instance_type': detail.get('HostInstanceType', ''),
                            'deployment_mode': detail.get('DeploymentMode', ''),
                            'broker_state': detail.get('BrokerState', ''),
                            'auto_minor_version_upgrade': detail.get('AutoMinorVersionUpgrade', False),
                            'publicly_accessible': detail.get('PubliclyAccessible', False),
                            'storage_type': detail.get('StorageType', ''),
                        },
                        tags=tags,
                    ))
                except Exception:
                    # Fallback with summary data only
                    resources.append(make_resource(
                        service='mq',
                        resource_type='broker',
                        resource_id=broker_id,
                        arn=broker_arn,
                        name=broker_name,
                        region=region,
                        details={
                            'engine_type': summary.get('EngineType', ''),
                            'deployment_mode': summary.get('DeploymentMode', ''),
                            'broker_state': summary.get('BrokerState', ''),
                        },
                        tags={},
                    ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Configurations ────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 100}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_configurations(**kwargs)
            for cfg in resp.get('Configurations', []):
                cfg_id = cfg.get('Id', '')
                cfg_name = cfg.get('Name', cfg_id)
                cfg_arn = cfg.get('Arn', '')
                tags = cfg.get('Tags', {})
                latest_rev = cfg.get('LatestRevision', {})
                resources.append(make_resource(
                    service='mq',
                    resource_type='configuration',
                    resource_id=cfg_id,
                    arn=cfg_arn,
                    name=cfg_name,
                    region=region,
                    details={
                        'engine_type': cfg.get('EngineType', ''),
                        'engine_version': cfg.get('EngineVersion', ''),
                        'latest_revision': latest_rev.get('Revision', 0),
                        'description': latest_rev.get('Description', ''),
                        'created': str(cfg.get('Created', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
