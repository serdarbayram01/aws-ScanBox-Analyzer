"""
Map Inventory — Amazon CloudWatch Logs Collector
Resource types: log-group, metric-filter, subscription-filter
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_logs_resources(session, region, account_id):
    """Collect CloudWatch Logs resources."""
    resources = []
    try:
        client = session.client('logs', region_name=region)
    except Exception:
        return resources

    # ── Log Groups ────────────────────────────────────────────────────
    log_group_names = []
    try:
        paginator = client.get_paginator('describe_log_groups')
        for page in paginator.paginate():
            for lg in page.get('logGroups', []):
                lg_name = lg.get('logGroupName', '')
                lg_arn = lg.get('arn', '')
                log_group_names.append(lg_name)

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=lg_arn)
                    tags = tag_resp.get('tags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='logs',
                    resource_type='log-group',
                    resource_id=lg_name,
                    arn=lg_arn,
                    name=lg_name,
                    region=region,
                    details={
                        'retention_days': lg.get('retentionInDays', 'Never expire'),
                        'stored_bytes': lg.get('storedBytes', 0),
                        'metric_filter_count': lg.get('metricFilterCount', 0),
                        'kms_key_id': lg.get('kmsKeyId', ''),
                        'creation_time': lg.get('creationTime', 0),
                        'log_group_class': lg.get('logGroupClass', ''),
                        'data_protection_status': lg.get('dataProtectionStatus', ''),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Metric Filters ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_metric_filters')
        for page in paginator.paginate():
            for mf in page.get('metricFilters', []):
                mf_name = mf.get('filterName', '')
                lg_name = mf.get('logGroupName', '')
                mf_id = f"{lg_name}/{mf_name}"
                transformations = mf.get('metricTransformations', [])
                resources.append(make_resource(
                    service='logs',
                    resource_type='metric-filter',
                    resource_id=mf_id,
                    arn=f"arn:aws:logs:{region}:{account_id}:log-group:{lg_name}:metric-filter:{mf_name}",
                    name=mf_name,
                    region=region,
                    details={
                        'log_group_name': lg_name,
                        'filter_pattern': mf.get('filterPattern', ''),
                        'creation_time': mf.get('creationTime', 0),
                        'metric_transformations': [
                            {
                                'metric_name': t.get('metricName', ''),
                                'metric_namespace': t.get('metricNamespace', ''),
                                'metric_value': t.get('metricValue', ''),
                            }
                            for t in transformations
                        ],
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Subscription Filters ─────────────────────────────────────────
    for lg_name in log_group_names:
        try:
            paginator = client.get_paginator('describe_subscription_filters')
            for page in paginator.paginate(logGroupName=lg_name):
                for sf in page.get('subscriptionFilters', []):
                    sf_name = sf.get('filterName', '')
                    sf_id = f"{lg_name}/{sf_name}"
                    resources.append(make_resource(
                        service='logs',
                        resource_type='subscription-filter',
                        resource_id=sf_id,
                        arn=f"arn:aws:logs:{region}:{account_id}:log-group:{lg_name}:subscription-filter:{sf_name}",
                        name=sf_name,
                        region=region,
                        details={
                            'log_group_name': lg_name,
                            'filter_pattern': sf.get('filterPattern', ''),
                            'destination_arn': sf.get('destinationArn', ''),
                            'role_arn': sf.get('roleArn', ''),
                            'distribution': sf.get('distribution', ''),
                            'creation_time': sf.get('creationTime', 0),
                        },
                        tags={},
                    ))
        except Exception:
            pass

    return resources
