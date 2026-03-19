"""
Map Inventory — Amazon Textract Collector
Resource types: adapter
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_textract_resources(session, region, account_id):
    """Collect Amazon Textract adapters in the given region."""
    resources = []
    try:
        client = session.client('textract', region_name=region)
    except Exception:
        return resources

    # ── Adapters ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_adapters')
        for page in paginator.paginate():
            for a in page.get('Adapters', []):
                aid = a.get('AdapterId', '')
                arn = f'arn:aws:textract:{region}:{account_id}:adapter/{aid}'
                resources.append(make_resource(
                    service='textract',
                    resource_type='adapter',
                    resource_id=aid,
                    arn=arn,
                    name=a.get('AdapterName', aid),
                    region=region,
                    details={
                        'creation_time': str(a.get('CreationTime', '')),
                        'feature_types': a.get('FeatureTypes', []),
                    },
                ))
    except Exception:
        pass

    return resources
