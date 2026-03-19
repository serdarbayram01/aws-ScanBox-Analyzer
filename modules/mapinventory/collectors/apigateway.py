"""
Map Inventory — API Gateway (v1 REST) Collector
Resource types: rest-api, stage, api-key, usage-plan, vpc-link
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_apigateway_resources(session, region, account_id):
    """Collect API Gateway v1 (REST) resources for a given region."""
    resources = []
    try:
        client = session.client('apigateway', region_name=region)
    except Exception:
        return resources

    # ── REST APIs ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_rest_apis')
        for page in paginator.paginate():
            for api in page.get('items', []):
                api_id = api.get('id', '')
                api_name = api.get('name', api_id)
                arn = f"arn:aws:apigateway:{region}::/restapis/{api_id}"
                tags = api.get('tags', {})

                resources.append(make_resource(
                    service='apigateway',
                    resource_type='rest-api',
                    resource_id=api_id,
                    arn=arn,
                    name=api_name,
                    region=region,
                    details={
                        'description': api.get('description', ''),
                        'endpoint_configuration': api.get('endpointConfiguration', {}).get('types', []),
                        'api_key_source': api.get('apiKeySource', ''),
                        'disable_execute_api_endpoint': api.get('disableExecuteApiEndpoint', False),
                        'created_date': str(api.get('createdDate', '')),
                        'version': api.get('version', ''),
                        'policy': bool(api.get('policy', '')),
                    },
                    tags=tags,  # apigateway returns tags as dict already
                ))

                # ── Stages per REST API ───────────────────────────────
                try:
                    stage_resp = client.get_stages(restApiId=api_id)
                    for stg in stage_resp.get('item', []):
                        stg_name = stg.get('stageName', '')
                        stg_arn = f"arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{stg_name}"
                        stg_tags = stg.get('tags', {})

                        resources.append(make_resource(
                            service='apigateway',
                            resource_type='stage',
                            resource_id=f"{api_id}/{stg_name}",
                            arn=stg_arn,
                            name=stg_name,
                            region=region,
                            details={
                                'rest_api_id': api_id,
                                'rest_api_name': api_name,
                                'deployment_id': stg.get('deploymentId', ''),
                                'description': stg.get('description', ''),
                                'cache_cluster_enabled': stg.get('cacheClusterEnabled', False),
                                'cache_cluster_size': stg.get('cacheClusterSize', ''),
                                'tracing_enabled': stg.get('tracingEnabled', False),
                                'created_date': str(stg.get('createdDate', '')),
                                'last_updated_date': str(stg.get('lastUpdatedDate', '')),
                            },
                            tags=stg_tags,
                        ))
                except Exception:
                    pass
    except Exception:
        pass

    # ── API Keys ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_api_keys')
        for page in paginator.paginate():
            for key in page.get('items', []):
                key_id = key.get('id', '')
                key_name = key.get('name', key_id)
                arn = f"arn:aws:apigateway:{region}::/apikeys/{key_id}"
                tags = key.get('tags', {})

                resources.append(make_resource(
                    service='apigateway',
                    resource_type='api-key',
                    resource_id=key_id,
                    arn=arn,
                    name=key_name,
                    region=region,
                    details={
                        'description': key.get('description', ''),
                        'enabled': key.get('enabled', False),
                        'created_date': str(key.get('createdDate', '')),
                        'last_updated_date': str(key.get('lastUpdatedDate', '')),
                        'stage_keys': key.get('stageKeys', []),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Usage Plans ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_usage_plans')
        for page in paginator.paginate():
            for up in page.get('items', []):
                up_id = up.get('id', '')
                up_name = up.get('name', up_id)
                arn = f"arn:aws:apigateway:{region}::/usageplans/{up_id}"
                tags = up.get('tags', {})
                throttle = up.get('throttle', {})
                quota = up.get('quota', {})

                resources.append(make_resource(
                    service='apigateway',
                    resource_type='usage-plan',
                    resource_id=up_id,
                    arn=arn,
                    name=up_name,
                    region=region,
                    details={
                        'description': up.get('description', ''),
                        'throttle_burst_limit': throttle.get('burstLimit', 0),
                        'throttle_rate_limit': throttle.get('rateLimit', 0),
                        'quota_limit': quota.get('limit', 0),
                        'quota_period': quota.get('period', ''),
                        'api_stages': [
                            {'api_id': a.get('apiId', ''), 'stage': a.get('stage', '')}
                            for a in up.get('apiStages', [])
                        ],
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── VPC Links ─────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('get_vpc_links')
        for page in paginator.paginate():
            for vl in page.get('items', []):
                vl_id = vl.get('id', '')
                vl_name = vl.get('name', vl_id)
                arn = f"arn:aws:apigateway:{region}::/vpclinks/{vl_id}"
                tags = vl.get('tags', {})

                resources.append(make_resource(
                    service='apigateway',
                    resource_type='vpc-link',
                    resource_id=vl_id,
                    arn=arn,
                    name=vl_name,
                    region=region,
                    details={
                        'description': vl.get('description', ''),
                        'status': vl.get('status', ''),
                        'status_message': vl.get('statusMessage', ''),
                        'target_arns': vl.get('targetArns', []),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
