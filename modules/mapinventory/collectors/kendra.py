"""
Map Inventory — Amazon Kendra Collector
Resource types: index, data-source
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_kendra_resources(session, region, account_id):
    """Collect Amazon Kendra resources in the given region."""
    resources = []
    try:
        client = session.client('kendra', region_name=region)
    except Exception:
        return resources

    # ── Indexes ─────────────────────────────────────────────────────
    index_ids = []
    try:
        paginator = client.get_paginator('list_indices')
        for page in paginator.paginate():
            for idx in page.get('IndexConfigurationSummaryItems', []):
                iid = idx.get('Id', '')
                index_ids.append(iid)
                resources.append(make_resource(
                    service='kendra',
                    resource_type='index',
                    resource_id=iid,
                    arn=f'arn:aws:kendra:{region}:{account_id}:index/{iid}',
                    name=idx.get('Name', iid),
                    region=region,
                    details={
                        'edition': idx.get('Edition', ''),
                        'status': idx.get('Status', ''),
                        'created_at': str(idx.get('CreatedAt', '')),
                        'updated_at': str(idx.get('UpdatedAt', '')),
                    },
                ))
    except Exception:
        pass

    # ── Data Sources (per index) ────────────────────────────────────
    for iid in index_ids:
        try:
            paginator = client.get_paginator('list_data_sources')
            for page in paginator.paginate(IndexId=iid):
                for ds in page.get('SummaryItems', []):
                    dsid = ds.get('Id', '')
                    resources.append(make_resource(
                        service='kendra',
                        resource_type='data-source',
                        resource_id=dsid,
                        arn=f'arn:aws:kendra:{region}:{account_id}:index/{iid}/data-source/{dsid}',
                        name=ds.get('Name', dsid),
                        region=region,
                        details={
                            'index_id': iid,
                            'type': ds.get('Type', ''),
                            'status': ds.get('Status', ''),
                            'created_at': str(ds.get('CreatedAt', '')),
                            'updated_at': str(ds.get('UpdatedAt', '')),
                            'language_code': ds.get('LanguageCode', ''),
                        },
                    ))
        except Exception:
            pass

    return resources
