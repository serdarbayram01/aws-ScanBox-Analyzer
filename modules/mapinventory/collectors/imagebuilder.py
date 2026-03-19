"""
Map Inventory — EC2 Image Builder Collector
Resource types: image-pipeline, image-recipe, container-recipe,
                infrastructure-configuration, distribution-configuration, component
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_imagebuilder_resources(session, region, account_id):
    """Collect EC2 Image Builder resources in the given region."""
    resources = []
    try:
        client = session.client('imagebuilder', region_name=region)
    except Exception:
        return resources

    # ── Image Pipelines ──────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_image_pipelines(**kwargs)
            for pipeline in resp.get('imagePipelineList', []):
                pipeline_arn = pipeline.get('arn', '')
                pipeline_name = pipeline.get('name', '')
                created = str(pipeline.get('dateCreated', ''))

                tags = pipeline.get('tags', {})

                resources.append(make_resource(
                    service='imagebuilder',
                    resource_type='image-pipeline',
                    resource_id=pipeline_name,
                    arn=pipeline_arn,
                    name=pipeline_name,
                    region=region,
                    details={
                        'description': pipeline.get('description', ''),
                        'platform': pipeline.get('platform', ''),
                        'status': pipeline.get('status', ''),
                        'image_recipe_arn': pipeline.get('imageRecipeArn', ''),
                        'container_recipe_arn': pipeline.get('containerRecipeArn', ''),
                        'infrastructure_configuration_arn': pipeline.get('infrastructureConfigurationArn', ''),
                        'distribution_configuration_arn': pipeline.get('distributionConfigurationArn', ''),
                        'date_created': created,
                        'date_updated': str(pipeline.get('dateUpdated', '')),
                        'date_last_run': str(pipeline.get('dateLastRun', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Image Recipes ────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'owner': 'Self'}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_image_recipes(**kwargs)
            for recipe in resp.get('imageRecipeSummaryList', []):
                recipe_arn = recipe.get('arn', '')
                recipe_name = recipe.get('name', '')

                tags = recipe.get('tags', {})

                resources.append(make_resource(
                    service='imagebuilder',
                    resource_type='image-recipe',
                    resource_id=recipe_name,
                    arn=recipe_arn,
                    name=recipe_name,
                    region=region,
                    details={
                        'platform': recipe.get('platform', ''),
                        'parent_image': recipe.get('parentImage', ''),
                        'date_created': str(recipe.get('dateCreated', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Container Recipes ────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'owner': 'Self'}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_container_recipes(**kwargs)
            for recipe in resp.get('containerRecipeSummaryList', []):
                recipe_arn = recipe.get('arn', '')
                recipe_name = recipe.get('name', '')

                tags = recipe.get('tags', {})

                resources.append(make_resource(
                    service='imagebuilder',
                    resource_type='container-recipe',
                    resource_id=recipe_name,
                    arn=recipe_arn,
                    name=recipe_name,
                    region=region,
                    details={
                        'platform': recipe.get('platform', ''),
                        'container_type': recipe.get('containerType', ''),
                        'parent_image': recipe.get('parentImage', ''),
                        'date_created': str(recipe.get('dateCreated', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Infrastructure Configurations ────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_infrastructure_configurations(**kwargs)
            for infra in resp.get('infrastructureConfigurationSummaryList', []):
                infra_arn = infra.get('arn', '')
                infra_name = infra.get('name', '')

                tags = infra.get('tags', {})

                resources.append(make_resource(
                    service='imagebuilder',
                    resource_type='infrastructure-configuration',
                    resource_id=infra_name,
                    arn=infra_arn,
                    name=infra_name,
                    region=region,
                    details={
                        'description': infra.get('description', ''),
                        'instance_types': infra.get('instanceTypes', []),
                        'instance_profile_name': infra.get('instanceProfileName', ''),
                        'date_created': str(infra.get('dateCreated', '')),
                        'date_updated': str(infra.get('dateUpdated', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Distribution Configurations ──────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_distribution_configurations(**kwargs)
            for dist in resp.get('distributionConfigurationSummaryList', []):
                dist_arn = dist.get('arn', '')
                dist_name = dist.get('name', '')

                tags = dist.get('tags', {})

                resources.append(make_resource(
                    service='imagebuilder',
                    resource_type='distribution-configuration',
                    resource_id=dist_name,
                    arn=dist_arn,
                    name=dist_name,
                    region=region,
                    details={
                        'description': dist.get('description', ''),
                        'regions': dist.get('regions', []),
                        'date_created': str(dist.get('dateCreated', '')),
                        'date_updated': str(dist.get('dateUpdated', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Components ───────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'owner': 'Self'}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_components(**kwargs)
            for comp in resp.get('componentVersionList', []):
                comp_arn = comp.get('arn', '')
                comp_name = comp.get('name', '')
                version = comp.get('version', '')

                resources.append(make_resource(
                    service='imagebuilder',
                    resource_type='component',
                    resource_id=f"{comp_name}/{version}",
                    arn=comp_arn,
                    name=comp_name,
                    region=region,
                    details={
                        'version': version,
                        'platform': comp.get('platform', ''),
                        'type': comp.get('type', ''),
                        'description': comp.get('description', ''),
                        'date_created': str(comp.get('dateCreated', '')),
                    },
                    tags={},
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
