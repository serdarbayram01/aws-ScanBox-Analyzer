"""
Map Inventory — Lambda Collector
Resource types: function, layer, event-source-mapping
Note: filename uses trailing underscore to avoid Python keyword conflict.
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_lambda__resources(session, region, account_id):
    """Collect all Lambda resources in the given region.

    Double underscore in function name due to Python keyword conflict with 'lambda'.
    """
    resources = []
    try:
        lam = session.client('lambda', region_name=region)
    except Exception:
        return resources

    # ── Functions ──────────────────────────────────────────────────────
    try:
        paginator = lam.get_paginator('list_functions')
        for page in paginator.paginate():
            for fn in page.get('Functions', []):
                fn_name = fn['FunctionName']
                fn_arn = fn.get('FunctionArn', f"arn:aws:lambda:{region}:{account_id}:function:{fn_name}")

                # Tags
                tags = {}
                try:
                    tag_resp = lam.list_tags(Resource=fn_arn)
                    tags = tag_resp.get('Tags', {})
                except Exception:
                    pass

                vpc_config = fn.get('VpcConfig', {})
                vpc_id = vpc_config.get('VpcId', '') if vpc_config else ''
                ephemeral = fn.get('EphemeralStorage', {})

                resources.append(make_resource(
                    service='lambda',
                    resource_type='function',
                    resource_id=fn_name,
                    arn=fn_arn,
                    name=fn_name,
                    region=region,
                    details={
                        'runtime': fn.get('Runtime', ''),
                        'handler': fn.get('Handler', ''),
                        'code_size': fn.get('CodeSize', 0),
                        'memory_size': fn.get('MemorySize', 0),
                        'timeout': fn.get('Timeout', 0),
                        'last_modified': fn.get('LastModified', ''),
                        'description': fn.get('Description', ''),
                        'role': fn.get('Role', ''),
                        'vpc_id': vpc_id,
                        'architectures': fn.get('Architectures', []),
                        'package_type': fn.get('PackageType', ''),
                        'ephemeral_storage': ephemeral.get('Size', 512) if ephemeral else 512,
                    },
                    tags=tags,  # Lambda list_tags returns {str: str} dict directly
                ))
    except Exception:
        pass

    # ── Layers ─────────────────────────────────────────────────────────
    try:
        paginator = lam.get_paginator('list_layers')
        for page in paginator.paginate():
            for layer in page.get('Layers', []):
                layer_name = layer['LayerName']
                layer_arn = layer.get('LayerArn', f"arn:aws:lambda:{region}:{account_id}:layer:{layer_name}")
                latest = layer.get('LatestMatchingVersion', {})

                resources.append(make_resource(
                    service='lambda',
                    resource_type='layer',
                    resource_id=layer_name,
                    arn=layer_arn,
                    name=layer_name,
                    region=region,
                    details={
                        'latest_version': latest.get('Version', ''),
                        'description': latest.get('Description', ''),
                        'created_date': latest.get('CreatedDate', ''),
                        'compatible_runtimes': latest.get('CompatibleRuntimes', []),
                    },
                    tags={},
                ))
    except Exception:
        pass

    # ── Event Source Mappings ──────────────────────────────────────────
    try:
        paginator = lam.get_paginator('list_event_source_mappings')
        for page in paginator.paginate():
            for esm in page.get('EventSourceMappings', []):
                esm_uuid = esm['UUID']
                fn_arn_ref = esm.get('FunctionArn', '')
                # Derive a readable name from function ARN
                fn_short = fn_arn_ref.rsplit(':', 1)[-1] if fn_arn_ref else esm_uuid
                esm_name = f"{fn_short}-{esm_uuid[:8]}"

                resources.append(make_resource(
                    service='lambda',
                    resource_type='event-source-mapping',
                    resource_id=esm_uuid,
                    arn=esm.get('EventSourceMappingArn', f"arn:aws:lambda:{region}:{account_id}:event-source-mapping:{esm_uuid}"),
                    name=esm_name,
                    region=region,
                    details={
                        'function_arn': fn_arn_ref,
                        'event_source_arn': esm.get('EventSourceArn', ''),
                        'state': esm.get('State', ''),
                        'batch_size': esm.get('BatchSize', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
