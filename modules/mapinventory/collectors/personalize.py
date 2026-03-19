"""
Map Inventory — Amazon Personalize Collector
Resource types: dataset-group, campaign, solution
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_personalize_resources(session, region, account_id):
    """Collect Amazon Personalize resources in the given region."""
    resources = []
    try:
        client = session.client('personalize', region_name=region)
    except Exception:
        return resources

    # ── Dataset Groups ──────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_dataset_groups')
        for page in paginator.paginate():
            for dg in page.get('datasetGroups', []):
                arn = dg.get('datasetGroupArn', '')
                name = dg.get('name', arn.split('/')[-1] if '/' in arn else arn)
                resources.append(make_resource(
                    service='personalize',
                    resource_type='dataset-group',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': dg.get('status', ''),
                        'creation_date_time': str(dg.get('creationDateTime', '')),
                        'last_updated_date_time': str(dg.get('lastUpdatedDateTime', '')),
                        'domain': dg.get('domain', ''),
                    },
                ))
    except Exception:
        pass

    # ── Solutions ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_solutions')
        for page in paginator.paginate():
            for s in page.get('solutions', []):
                arn = s.get('solutionArn', '')
                name = s.get('name', arn.split('/')[-1] if '/' in arn else arn)
                resources.append(make_resource(
                    service='personalize',
                    resource_type='solution',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': s.get('status', ''),
                        'dataset_group_arn': s.get('datasetGroupArn', ''),
                        'recipe_arn': s.get('recipeArn', ''),
                        'creation_date_time': str(s.get('creationDateTime', '')),
                        'last_updated_date_time': str(s.get('lastUpdatedDateTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Campaigns ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_campaigns')
        for page in paginator.paginate():
            for c in page.get('campaigns', []):
                arn = c.get('campaignArn', '')
                name = c.get('name', arn.split('/')[-1] if '/' in arn else arn)
                resources.append(make_resource(
                    service='personalize',
                    resource_type='campaign',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': c.get('status', ''),
                        'creation_date_time': str(c.get('creationDateTime', '')),
                        'last_updated_date_time': str(c.get('lastUpdatedDateTime', '')),
                    },
                ))
    except Exception:
        pass

    return resources
