"""
Map Inventory — Route 53 Collector (GLOBAL)
Collects: hosted-zone, health-check, query-logging-config
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_route53_resources(session, region, account_id):
    """Collect Route 53 resources. Route 53 is global; region param is ignored."""
    resources = []
    try:
        client = session.client('route53', region_name='us-east-1')
    except Exception:
        return resources

    # --- Hosted Zones ---
    try:
        paginator = client.get_paginator('list_hosted_zones')
        for page in paginator.paginate():
            for zone in page.get('HostedZones', []):
                zone_id_full = zone.get('Id', '')
                # Id comes as "/hostedzone/ZXXXX" — extract the ID
                zone_id = zone_id_full.split('/')[-1] if '/' in zone_id_full else zone_id_full
                zone_name = zone.get('Name', '')
                config = zone.get('Config', {})
                private_zone = config.get('PrivateZone', False)
                comment = config.get('Comment', '')
                record_count = zone.get('ResourceRecordSetCount', 0)

                zone_arn = f"arn:aws:route53:::hostedzone/{zone_id}"

                # Fetch tags
                tags_dict = {}
                try:
                    tags_resp = client.list_tags_for_resource(
                        ResourceType='hostedzone',
                        ResourceId=zone_id,
                    )
                    resource_tag_set = tags_resp.get('ResourceTagSet', {})
                    tags_dict = tags_to_dict(resource_tag_set.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='route53',
                    resource_type='hosted-zone',
                    resource_id=zone_id,
                    arn=zone_arn,
                    name=zone_name,
                    region='global',
                    details={
                        'zone_name': zone_name,
                        'private_zone': private_zone,
                        'record_count': record_count,
                        'comment': comment,
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # --- Health Checks ---
    try:
        paginator = client.get_paginator('list_health_checks')
        for page in paginator.paginate():
            for hc in page.get('HealthChecks', []):
                hc_id = hc.get('Id', '')
                hc_config = hc.get('HealthCheckConfig', {})
                hc_arn = f"arn:aws:route53:::healthcheck/{hc_id}"

                # Fetch tags
                tags_dict = {}
                try:
                    tags_resp = client.list_tags_for_resource(
                        ResourceType='healthcheck',
                        ResourceId=hc_id,
                    )
                    resource_tag_set = tags_resp.get('ResourceTagSet', {})
                    tags_dict = tags_to_dict(resource_tag_set.get('Tags', []))
                except Exception:
                    pass

                hc_name = tags_dict.get('Name', '') or hc_id

                resources.append(make_resource(
                    service='route53',
                    resource_type='health-check',
                    resource_id=hc_id,
                    arn=hc_arn,
                    name=hc_name,
                    region='global',
                    details={
                        'type': hc_config.get('Type', ''),
                        'fqdn': hc_config.get('FullyQualifiedDomainName', ''),
                        'ip_address': hc_config.get('IPAddress', ''),
                        'port': hc_config.get('Port', 0),
                        'resource_path': hc_config.get('ResourcePath', ''),
                        'request_interval': hc_config.get('RequestInterval', 0),
                        'failure_threshold': hc_config.get('FailureThreshold', 0),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # --- Query Logging Configs ---
    try:
        qlc_resp = client.list_query_logging_configs()
        for qlc in qlc_resp.get('QueryLoggingConfigs', []):
            qlc_id = qlc.get('Id', '')
            hosted_zone_id = qlc.get('HostedZoneId', '')
            log_group_arn = qlc.get('CloudWatchLogsLogGroupArn', '')
            qlc_arn = f"arn:aws:route53:::queryloggingconfig/{qlc_id}"

            resources.append(make_resource(
                service='route53',
                resource_type='query-logging-config',
                resource_id=qlc_id,
                arn=qlc_arn,
                name=f"qlc-{hosted_zone_id}",
                region='global',
                details={
                    'hosted_zone_id': hosted_zone_id,
                    'cloud_watch_logs_log_group_arn': log_group_arn,
                },
                tags={},
            ))
    except Exception:
        pass

    return resources
