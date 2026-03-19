"""
Map Inventory — CloudWatch Collector
Resource types: metric-alarm, composite-alarm, dashboard, metric-stream
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_cloudwatch_resources(session, region, account_id):
    """Collect all CloudWatch resource types in the given region."""
    resources = []
    try:
        cw = session.client('cloudwatch', region_name=region)
    except Exception:
        return resources

    # ── Metric Alarms & Composite Alarms ─────────────────────────────
    try:
        paginator = cw.get_paginator('describe_alarms')
        for page in paginator.paginate():
            # Metric Alarms
            for alarm in page.get('MetricAlarms', []):
                alarm_name = alarm['AlarmName']
                alarm_arn = alarm.get('AlarmArn', '')
                tags_dict = {}
                try:
                    tag_resp = cw.list_tags_for_resource(ResourceARN=alarm_arn)
                    tags_dict = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass
                resources.append(make_resource(
                    service='cloudwatch',
                    resource_type='metric-alarm',
                    resource_id=alarm_name,
                    arn=alarm_arn,
                    name=alarm_name,
                    region=region,
                    details={
                        'namespace': alarm.get('Namespace', ''),
                        'metric_name': alarm.get('MetricName', ''),
                        'comparison_operator': alarm.get('ComparisonOperator', ''),
                        'threshold': alarm.get('Threshold', ''),
                        'evaluation_periods': alarm.get('EvaluationPeriods', ''),
                        'period': alarm.get('Period', ''),
                        'statistic': alarm.get('Statistic', ''),
                        'state_value': alarm.get('StateValue', ''),
                        'state_reason': alarm.get('StateReason', ''),
                        'actions_enabled': alarm.get('ActionsEnabled', False),
                        'alarm_actions': alarm.get('AlarmActions', []),
                        'dimensions': [
                            {'name': d.get('Name', ''), 'value': d.get('Value', '')}
                            for d in alarm.get('Dimensions', [])
                        ],
                    },
                    tags=tags_dict,
                ))

            # Composite Alarms
            for alarm in page.get('CompositeAlarms', []):
                alarm_name = alarm['AlarmName']
                alarm_arn = alarm.get('AlarmArn', '')
                tags_dict = {}
                try:
                    tag_resp = cw.list_tags_for_resource(ResourceARN=alarm_arn)
                    tags_dict = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass
                resources.append(make_resource(
                    service='cloudwatch',
                    resource_type='composite-alarm',
                    resource_id=alarm_name,
                    arn=alarm_arn,
                    name=alarm_name,
                    region=region,
                    details={
                        'alarm_rule': alarm.get('AlarmRule', ''),
                        'state_value': alarm.get('StateValue', ''),
                        'state_reason': alarm.get('StateReason', ''),
                        'actions_enabled': alarm.get('ActionsEnabled', False),
                        'alarm_actions': alarm.get('AlarmActions', []),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Dashboards ───────────────────────────────────────────────────
    try:
        paginator = cw.get_paginator('list_dashboards')
        for page in paginator.paginate():
            for db in page.get('DashboardEntries', []):
                db_name = db.get('DashboardName', '')
                db_arn = db.get('DashboardArn', '')
                resources.append(make_resource(
                    service='cloudwatch',
                    resource_type='dashboard',
                    resource_id=db_name,
                    arn=db_arn,
                    name=db_name,
                    region=region,
                    details={
                        'size': db.get('Size', 0),
                        'last_modified': str(db.get('LastModified', '')),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Metric Streams ───────────────────────────────────────────────
    try:
        paginator = cw.get_paginator('list_metric_streams')
        for page in paginator.paginate():
            for ms in page.get('Entries', []):
                ms_name = ms.get('Name', '')
                ms_arn = ms.get('Arn', '')
                tags_dict = {}
                try:
                    tag_resp = cw.list_tags_for_resource(ResourceARN=ms_arn)
                    tags_dict = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass
                resources.append(make_resource(
                    service='cloudwatch',
                    resource_type='metric-stream',
                    resource_id=ms_name,
                    arn=ms_arn,
                    name=ms_name,
                    region=region,
                    details={
                        'state': ms.get('State', ''),
                        'firehose_arn': ms.get('FirehoseArn', ''),
                        'output_format': ms.get('OutputFormat', ''),
                        'creation_date': str(ms.get('CreationDate', '')),
                        'last_update_date': str(ms.get('LastUpdateDate', '')),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
