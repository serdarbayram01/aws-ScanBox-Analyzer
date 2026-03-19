"""
Map Inventory — AWS App Runner Collector
Resource types: service, connection, auto-scaling-configuration,
                vpc-connector, observability-configuration, vpc-ingress-connection
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_apprunner_resources(session, region, account_id):
    """Collect AWS App Runner resources."""
    resources = []
    try:
        client = session.client('apprunner', region_name=region)
    except Exception:
        return resources

    # ── Services ──────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 20}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_services(**kwargs)
            for svc_summary in resp.get('ServiceSummaryList', []):
                svc_arn = svc_summary.get('ServiceArn', '')
                svc_name = svc_summary.get('ServiceName', '')
                svc_id = svc_summary.get('ServiceId', '')
                try:
                    detail = client.describe_service(ServiceArn=svc_arn)
                    svc = detail.get('Service', {})
                    src_cfg = svc.get('SourceConfiguration', {})
                    inst_cfg = svc.get('InstanceConfiguration', {})
                    tags = {}
                    try:
                        tag_resp = client.list_tags_for_resource(ResourceArn=svc_arn)
                        tags = {t['Key']: t['Value'] for t in tag_resp.get('Tags', []) if 'Key' in t}
                    except Exception:
                        pass
                    resources.append(make_resource(
                        service='apprunner',
                        resource_type='service',
                        resource_id=svc_id,
                        arn=svc_arn,
                        name=svc_name,
                        region=region,
                        details={
                            'status': svc.get('Status', ''),
                            'service_url': svc.get('ServiceUrl', ''),
                            'cpu': inst_cfg.get('Cpu', ''),
                            'memory': inst_cfg.get('Memory', ''),
                            'auto_scaling_config_arn': svc.get('AutoScalingConfigurationSummary', {}).get('AutoScalingConfigurationArn', ''),
                            'created_at': str(svc.get('CreatedAt', '')),
                            'updated_at': str(svc.get('UpdatedAt', '')),
                        },
                        tags=tags,
                    ))
                except Exception:
                    resources.append(make_resource(
                        service='apprunner',
                        resource_type='service',
                        resource_id=svc_id,
                        arn=svc_arn,
                        name=svc_name,
                        region=region,
                        details={'status': svc_summary.get('Status', '')},
                        tags={},
                    ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Connections ───────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 20}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_connections(**kwargs)
            for conn in resp.get('ConnectionSummaryList', []):
                conn_arn = conn.get('ConnectionArn', '')
                conn_name = conn.get('ConnectionName', '')
                resources.append(make_resource(
                    service='apprunner',
                    resource_type='connection',
                    resource_id=conn_name,
                    arn=conn_arn,
                    name=conn_name,
                    region=region,
                    details={
                        'provider_type': conn.get('ProviderType', ''),
                        'status': conn.get('Status', ''),
                        'created_at': str(conn.get('CreatedAt', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Auto Scaling Configurations ──────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 20}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_auto_scaling_configurations(**kwargs)
            for asc in resp.get('AutoScalingConfigurationSummaryList', []):
                asc_arn = asc.get('AutoScalingConfigurationArn', '')
                asc_name = asc.get('AutoScalingConfigurationName', '')
                asc_revision = asc.get('AutoScalingConfigurationRevision', 0)
                resources.append(make_resource(
                    service='apprunner',
                    resource_type='auto-scaling-configuration',
                    resource_id=f"{asc_name}:{asc_revision}",
                    arn=asc_arn,
                    name=asc_name,
                    region=region,
                    details={
                        'revision': asc_revision,
                        'status': asc.get('Status', ''),
                        'created_at': str(asc.get('CreatedAt', '')),
                        'has_associated_service': asc.get('HasAssociatedService', False),
                        'is_default': asc.get('IsDefault', False),
                    },
                    tags={},
                    is_default=asc.get('IsDefault', False),
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── VPC Connectors ───────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 20}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_vpc_connectors(**kwargs)
            for vc in resp.get('VpcConnectors', []):
                vc_arn = vc.get('VpcConnectorArn', '')
                vc_name = vc.get('VpcConnectorName', '')
                resources.append(make_resource(
                    service='apprunner',
                    resource_type='vpc-connector',
                    resource_id=vc_name,
                    arn=vc_arn,
                    name=vc_name,
                    region=region,
                    details={
                        'revision': vc.get('VpcConnectorRevision', 0),
                        'status': vc.get('Status', ''),
                        'subnets': vc.get('Subnets', []),
                        'security_groups': vc.get('SecurityGroups', []),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Observability Configurations ─────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 20}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_observability_configurations(**kwargs)
            for oc in resp.get('ObservabilityConfigurationSummaryList', []):
                oc_arn = oc.get('ObservabilityConfigurationArn', '')
                oc_name = oc.get('ObservabilityConfigurationName', '')
                resources.append(make_resource(
                    service='apprunner',
                    resource_type='observability-configuration',
                    resource_id=oc_name,
                    arn=oc_arn,
                    name=oc_name,
                    region=region,
                    details={
                        'revision': oc.get('ObservabilityConfigurationRevision', 0),
                        'status': oc.get('Status', ''),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── VPC Ingress Connections ──────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'MaxResults': 20}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_vpc_ingress_connections(**kwargs)
            for vic in resp.get('VpcIngressConnectionSummaryList', []):
                vic_arn = vic.get('VpcIngressConnectionArn', '')
                vic_name = vic.get('VpcIngressConnectionName', '')
                resources.append(make_resource(
                    service='apprunner',
                    resource_type='vpc-ingress-connection',
                    resource_id=vic_name,
                    arn=vic_arn,
                    name=vic_name,
                    region=region,
                    details={
                        'service_arn': vic.get('ServiceArn', ''),
                    },
                    tags={},
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
