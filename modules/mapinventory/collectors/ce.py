"""
Map Inventory — AWS Cost Explorer Collector
Resource types: anomaly-monitor, anomaly-subscription, cost-category
GLOBAL — uses us-east-1.
"""

from .base import make_resource, tags_to_dict


def collect_ce_resources(session, region, account_id):
    """Collect Cost Explorer configuration resources (global, us-east-1)."""
    resources = []
    try:
        client = session.client('ce', region_name='us-east-1')
    except Exception:
        return resources

    # ── Cost Allocation Tags (informational, no individual resources) ─
    # list_cost_allocation_tags returns tag keys; we skip resource creation
    # since they are config metadata, not discrete resources.

    # ── Anomaly Monitors ─────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextPageToken'] = next_token
            resp = client.get_anomaly_monitors(**kwargs)
            for m in resp.get('AnomalyMonitors', []):
                arn = m.get('MonitorArn', '')
                name = m.get('MonitorName', '')
                mid = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='ce',
                    resource_type='anomaly-monitor',
                    resource_id=mid,
                    arn=arn,
                    name=name,
                    region='global',
                    details={
                        'monitor_type': m.get('MonitorType', ''),
                        'monitor_dimension': m.get('MonitorDimension', ''),
                        'creation_date': str(m.get('CreationDate', '')),
                        'last_updated_date': str(m.get('LastUpdatedDate', '')),
                        'last_evaluated_date': str(m.get('LastEvaluatedDate', '')),
                        'dimensional_value_count': m.get('DimensionalValueCount', 0),
                    },
                ))
            next_token = resp.get('NextPageToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Anomaly Subscriptions ────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextPageToken'] = next_token
            resp = client.get_anomaly_subscriptions(**kwargs)
            for s in resp.get('AnomalySubscriptions', []):
                arn = s.get('SubscriptionArn', '')
                name = s.get('SubscriptionName', '')
                sid = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='ce',
                    resource_type='anomaly-subscription',
                    resource_id=sid,
                    arn=arn,
                    name=name,
                    region='global',
                    details={
                        'frequency': s.get('Frequency', ''),
                        'threshold': s.get('Threshold', 0),
                        'threshold_expression': str(s.get('ThresholdExpression', {})),
                        'monitor_arn_list': s.get('MonitorArnList', []),
                        'subscribers': str(s.get('Subscribers', [])),
                    },
                ))
            next_token = resp.get('NextPageToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Cost Category Definitions ────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_cost_category_definitions(**kwargs)
            for cc in resp.get('CostCategoryReferences', []):
                arn = cc.get('CostCategoryArn', '')
                name = cc.get('Name', '')
                cid = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='ce',
                    resource_type='cost-category',
                    resource_id=cid,
                    arn=arn,
                    name=name,
                    region='global',
                    details={
                        'effective_start': cc.get('EffectiveStart', ''),
                        'effective_end': cc.get('EffectiveEnd', ''),
                        'number_of_rules': cc.get('NumberOfRules', 0),
                        'default_value': cc.get('DefaultValue', ''),
                    },
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
