"""
Map Inventory — ECR Collector
Collects: repository
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ecr_resources(session, region, account_id):
    """Collect ECR resources for a given region."""
    resources = []
    try:
        client = session.client('ecr', region_name=region)
    except Exception:
        return resources

    try:
        paginator = client.get_paginator('describe_repositories')
        for page in paginator.paginate():
            for repo in page.get('repositories', []):
                repo_name = repo.get('repositoryName', '')
                repo_arn = repo.get('repositoryArn', '')
                repo_uri = repo.get('repositoryUri', '')
                created_at = str(repo.get('createdAt', ''))
                image_tag_mutability = repo.get('imageTagMutability', '')
                scan_config = repo.get('imageScanningConfiguration', {})
                scan_on_push = scan_config.get('scanOnPush', False)
                encryption_config = repo.get('encryptionConfiguration', {})
                encryption_type = encryption_config.get('encryptionType', 'AES256')

                # Fetch tags
                tags_dict = {}
                try:
                    tags_resp = client.list_tags_for_resource(resourceArn=repo_arn)
                    tags_dict = tags_to_dict(tags_resp.get('tags', []))
                except Exception:
                    pass

                # Count images
                image_count = 0
                try:
                    img_paginator = client.get_paginator('list_images')
                    for img_page in img_paginator.paginate(
                        repositoryName=repo_name,
                        filter={'tagStatus': 'ANY'}
                    ):
                        image_count += len(img_page.get('imageIds', []))
                except Exception:
                    pass

                # Check lifecycle policy existence
                has_lifecycle_policy = False
                try:
                    client.get_lifecycle_policy(repositoryName=repo_name)
                    has_lifecycle_policy = True
                except client.exceptions.LifecyclePolicyNotFoundException:
                    has_lifecycle_policy = False
                except Exception:
                    pass

                resources.append(make_resource(
                    service='ecr',
                    resource_type='repository',
                    resource_id=repo_name,
                    arn=repo_arn,
                    name=repo_name,
                    region=region,
                    details={
                        'repository_uri': repo_uri,
                        'created_at': created_at,
                        'image_tag_mutability': image_tag_mutability,
                        'scan_on_push': scan_on_push,
                        'encryption_type': encryption_type,
                        'image_count': image_count,
                        'has_lifecycle_policy': has_lifecycle_policy,
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
