"""
Map Inventory — Amazon Rekognition Collector
Resource types: collection, project, stream-processor
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_rekognition_resources(session, region, account_id):
    """Collect Amazon Rekognition resources in the given region."""
    resources = []
    try:
        client = session.client('rekognition', region_name=region)
    except Exception:
        return resources

    # ── Collections ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_collections')
        for page in paginator.paginate():
            for cid in page.get('CollectionIds', []):
                arn = f'arn:aws:rekognition:{region}:{account_id}:collection/{cid}'
                details = {}
                try:
                    desc = client.describe_collection(CollectionId=cid)
                    details = {
                        'face_count': desc.get('FaceCount', 0),
                        'face_model_version': desc.get('FaceModelVersion', ''),
                        'creation_timestamp': str(desc.get('CreationTimestamp', '')),
                    }
                except Exception:
                    pass
                tags_dict = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceArn=arn)
                    tags_dict = tag_resp.get('Tags', {})
                except Exception:
                    pass
                resources.append(make_resource(
                    service='rekognition',
                    resource_type='collection',
                    resource_id=cid,
                    arn=arn,
                    name=cid,
                    region=region,
                    details=details,
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # ── Projects ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_projects')
        for page in paginator.paginate():
            for p in page.get('ProjectDescriptions', []):
                arn = p.get('ProjectArn', '')
                name = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='rekognition',
                    resource_type='project',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': p.get('Status', ''),
                        'creation_timestamp': str(p.get('CreationTimestamp', '')),
                        'feature': p.get('Feature', ''),
                    },
                ))
    except Exception:
        pass

    # ── Stream Processors ───────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_stream_processors')
        for page in paginator.paginate():
            for sp in page.get('StreamProcessors', []):
                name = sp.get('Name', '')
                resources.append(make_resource(
                    service='rekognition',
                    resource_type='stream-processor',
                    resource_id=name,
                    arn=f'arn:aws:rekognition:{region}:{account_id}:streamprocessor/{name}',
                    name=name,
                    region=region,
                    details={
                        'status': sp.get('Status', ''),
                    },
                ))
    except Exception:
        pass

    return resources
