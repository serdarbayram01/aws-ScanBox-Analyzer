"""
Map Inventory — Service Quotas Collector
Resource types: service-quota (with applied values different from default)
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_servicequotas_resources(session, region, account_id):
    """Collect Service Quotas that have been explicitly adjusted from defaults."""
    resources = []
    try:
        client = session.client('service-quotas', region_name=region)
    except Exception:
        return resources

    # ── Service Quotas with applied (non-default) values ────────────
    try:
        paginator = client.get_paginator('list_requested_service_quota_change_history')
        for page in paginator.paginate():
            for rq in page.get('RequestedQuotas', []):
                qid = rq.get('Id', '')
                resources.append(make_resource(
                    service='servicequotas',
                    resource_type='service-quota',
                    resource_id=qid,
                    arn=f'arn:aws:servicequotas:{region}:{account_id}:request/{qid}',
                    name=rq.get('QuotaName', qid),
                    region=region,
                    details={
                        'service_code': rq.get('ServiceCode', ''),
                        'service_name': rq.get('ServiceName', ''),
                        'quota_code': rq.get('QuotaCode', ''),
                        'desired_value': rq.get('DesiredValue', 0),
                        'status': rq.get('Status', ''),
                        'created': str(rq.get('Created', '')),
                        'last_updated': str(rq.get('LastUpdated', '')),
                    },
                ))
    except Exception:
        pass

    # Also list quotas that have applied values
    try:
        svc_paginator = client.get_paginator('list_services')
        for svc_page in svc_paginator.paginate():
            for svc in svc_page.get('Services', []):
                svc_code = svc.get('ServiceCode', '')
                try:
                    q_paginator = client.get_paginator('list_service_quotas')
                    for q_page in q_paginator.paginate(ServiceCode=svc_code):
                        for q in q_page.get('Quotas', []):
                            # Only include quotas that have been adjusted
                            if q.get('Adjustable', False) and q.get('Value') is not None:
                                default_val = q.get('DefaultValue')
                                current_val = q.get('Value')
                                if default_val is not None and current_val != default_val:
                                    qcode = q.get('QuotaCode', '')
                                    resources.append(make_resource(
                                        service='servicequotas',
                                        resource_type='service-quota',
                                        resource_id=f'{svc_code}/{qcode}',
                                        arn=q.get('QuotaArn', ''),
                                        name=q.get('QuotaName', qcode),
                                        region=region,
                                        details={
                                            'service_code': svc_code,
                                            'service_name': svc.get('ServiceName', ''),
                                            'quota_code': qcode,
                                            'default_value': default_val,
                                            'current_value': current_val,
                                            'unit': q.get('Unit', ''),
                                            'global_quota': q.get('GlobalQuota', False),
                                        },
                                    ))
                except Exception:
                    pass
    except Exception:
        pass

    return resources
