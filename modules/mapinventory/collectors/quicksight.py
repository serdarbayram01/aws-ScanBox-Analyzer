"""
Map Inventory — QuickSight Collector
Resource types: dashboard, dataset, data-source, analysis
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_quicksight_resources(session, region, account_id):
    """Collect QuickSight resources in the given region."""
    resources = []
    try:
        client = session.client('quicksight', region_name=region)
    except Exception:
        return resources

    # ── Dashboards ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_dashboards')
        for page in paginator.paginate(AwsAccountId=account_id):
            for d in page.get('DashboardSummaryList', []):
                did = d.get('DashboardId', '')
                arn = d.get('Arn', '')
                resources.append(make_resource(
                    service='quicksight',
                    resource_type='dashboard',
                    resource_id=did,
                    arn=arn,
                    name=d.get('Name', did),
                    region=region,
                    details={
                        'published_version': d.get('PublishedVersionNumber', ''),
                        'created_time': str(d.get('CreatedTime', '')),
                        'last_updated_time': str(d.get('LastUpdatedTime', '')),
                        'last_published_time': str(d.get('LastPublishedTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Datasets ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_data_sets')
        for page in paginator.paginate(AwsAccountId=account_id):
            for ds in page.get('DataSetSummaries', []):
                dsid = ds.get('DataSetId', '')
                arn = ds.get('Arn', '')
                resources.append(make_resource(
                    service='quicksight',
                    resource_type='dataset',
                    resource_id=dsid,
                    arn=arn,
                    name=ds.get('Name', dsid),
                    region=region,
                    details={
                        'import_mode': ds.get('ImportMode', ''),
                        'created_time': str(ds.get('CreatedTime', '')),
                        'last_updated_time': str(ds.get('LastUpdatedTime', '')),
                        'row_level_permission_data_set': str(ds.get('RowLevelPermissionDataSet', '')),
                    },
                ))
    except Exception:
        pass

    # ── Data Sources ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_data_sources')
        for page in paginator.paginate(AwsAccountId=account_id):
            for src in page.get('DataSources', []):
                sid = src.get('DataSourceId', '')
                arn = src.get('Arn', '')
                resources.append(make_resource(
                    service='quicksight',
                    resource_type='data-source',
                    resource_id=sid,
                    arn=arn,
                    name=src.get('Name', sid),
                    region=region,
                    details={
                        'type': src.get('Type', ''),
                        'status': src.get('Status', ''),
                        'created_time': str(src.get('CreatedTime', '')),
                        'last_updated_time': str(src.get('LastUpdatedTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Analyses ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_analyses')
        for page in paginator.paginate(AwsAccountId=account_id):
            for a in page.get('AnalysisSummaryList', []):
                aid = a.get('AnalysisId', '')
                arn = a.get('Arn', '')
                resources.append(make_resource(
                    service='quicksight',
                    resource_type='analysis',
                    resource_id=aid,
                    arn=arn,
                    name=a.get('Name', aid),
                    region=region,
                    details={
                        'status': a.get('Status', ''),
                        'created_time': str(a.get('CreatedTime', '')),
                        'last_updated_time': str(a.get('LastUpdatedTime', '')),
                    },
                ))
    except Exception:
        pass

    return resources
