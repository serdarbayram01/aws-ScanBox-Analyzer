"""
Map Inventory — Amazon ECR Public Collector
Resource types: repository
GLOBAL service — only available in us-east-1.
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ecr_public_resources(session, region, account_id):
    """Collect ECR Public repositories. Only runs in us-east-1."""
    resources = []

    # ECR Public API is only available in us-east-1
    if region != 'us-east-1':
        return resources

    try:
        client = session.client('ecr-public', region_name='us-east-1')
    except Exception:
        return resources

    # ── Public Repositories ──────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.describe_repositories(**kwargs)
            for repo in resp.get('repositories', []):
                repo_name = repo.get('repositoryName', '')
                repo_arn = repo.get('repositoryArn', '')
                repo_uri = repo.get('repositoryUri', '')
                registry_id = repo.get('registryId', account_id)

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=repo_arn)
                    tags = {t['Key']: t['Value'] for t in tag_resp.get('tags', []) if 'Key' in t}
                except Exception:
                    pass

                resources.append(make_resource(
                    service='ecr-public',
                    resource_type='repository',
                    resource_id=repo_name,
                    arn=repo_arn,
                    name=repo_name,
                    region='us-east-1',
                    details={
                        'repository_uri': repo_uri,
                        'registry_id': registry_id,
                        'created_at': str(repo.get('createdAt', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
