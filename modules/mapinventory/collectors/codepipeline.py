"""
Map Inventory — CodePipeline Collector
Resource types: pipeline
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_codepipeline_resources(session, region, account_id):
    """Collect CodePipeline resources for a given region."""
    resources = []
    try:
        client = session.client('codepipeline', region_name=region)
    except Exception:
        return resources

    # ── Pipelines ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_pipelines')
        for page in paginator.paginate():
            for p in page.get('pipelines', []):
                p_name = p.get('name', '')
                p_version = p.get('version', 0)
                created = str(p.get('created', ''))
                updated = str(p.get('updated', ''))

                arn = f"arn:aws:codepipeline:{region}:{account_id}:{p_name}"
                details_dict = {
                    'version': p_version,
                    'created': created,
                    'updated': updated,
                    'pipeline_type': p.get('pipelineType', ''),
                    'execution_mode': p.get('executionMode', ''),
                }
                tags = {}

                try:
                    detail_resp = client.get_pipeline(name=p_name)
                    pipeline = detail_resp.get('pipeline', {})
                    metadata = detail_resp.get('metadata', {})
                    arn = metadata.get('pipelineArn', arn)
                    stages = pipeline.get('stages', [])
                    details_dict.update({
                        'stage_count': len(stages),
                        'stages': [s.get('name', '') for s in stages],
                        'role_arn': pipeline.get('roleArn', ''),
                    })
                except Exception:
                    pass

                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=arn)
                    tags = tags_to_dict(tag_resp.get('tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='codepipeline',
                    resource_type='pipeline',
                    resource_id=p_name,
                    arn=arn,
                    name=p_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
