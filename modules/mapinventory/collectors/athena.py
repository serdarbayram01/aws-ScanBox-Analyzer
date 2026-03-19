"""
Map Inventory — Athena Collector
Resource types: workgroup, data-catalog, named-query
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_athena_resources(session, region, account_id):
    """Collect Athena resources for a given region."""
    resources = []
    try:
        client = session.client('athena', region_name=region)
    except Exception:
        return resources

    # ── Workgroups ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_work_groups')
        for page in paginator.paginate():
            for wg in page.get('WorkGroups', []):
                wg_name = wg.get('Name', '')
                state = wg.get('State', '')
                arn = f"arn:aws:athena:{region}:{account_id}:workgroup/{wg_name}"
                is_default = (wg_name == 'primary')

                # Get detailed info + tags
                details_dict = {
                    'state': state,
                    'description': wg.get('Description', ''),
                    'engine_version': wg.get('EngineVersion', {}).get('EffectiveEngineVersion', ''),
                }
                tags = {}
                try:
                    detail_resp = client.get_work_group(WorkGroup=wg_name)
                    wg_detail = detail_resp.get('WorkGroup', {})
                    config = wg_detail.get('Configuration', {})
                    details_dict.update({
                        'enforce_workgroup_configuration': config.get('EnforceWorkGroupConfiguration', False),
                        'publish_cloudwatch_metrics': config.get('PublishCloudWatchMetricsEnabled', False),
                        'bytes_scanned_cutoff': config.get('BytesScannedCutoffPerQuery', 0),
                        'output_location': config.get('ResultConfiguration', {}).get('OutputLocation', ''),
                    })
                except Exception:
                    pass

                try:
                    tag_resp = client.list_tags_for_resource(ResourceARN=arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='athena',
                    resource_type='workgroup',
                    resource_id=wg_name,
                    arn=arn,
                    name=wg_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Data Catalogs ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_data_catalogs')
        for page in paginator.paginate():
            for cat in page.get('DataCatalogsSummary', []):
                cat_name = cat.get('CatalogName', '')
                cat_type = cat.get('Type', '')
                arn = f"arn:aws:athena:{region}:{account_id}:datacatalog/{cat_name}"
                is_default = (cat_name == 'AwsDataCatalog')

                tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(ResourceARN=arn)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='athena',
                    resource_type='data-catalog',
                    resource_id=cat_name,
                    arn=arn,
                    name=cat_name,
                    region=region,
                    details={
                        'type': cat_type,
                    },
                    tags=tags,
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Named Queries ─────────────────────────────────────────────────
    try:
        query_ids = []
        paginator = client.get_paginator('list_named_queries')
        for page in paginator.paginate():
            query_ids.extend(page.get('NamedQueryIds', []))

        # batch_get_named_query accepts up to 50 at a time
        for i in range(0, len(query_ids), 50):
            batch = query_ids[i:i + 50]
            try:
                resp = client.batch_get_named_query(NamedQueryIds=batch)
                for nq in resp.get('NamedQueries', []):
                    nq_id = nq.get('NamedQueryId', '')
                    nq_name = nq.get('Name', nq_id)
                    arn = f"arn:aws:athena:{region}:{account_id}:namedquery/{nq_id}"
                    resources.append(make_resource(
                        service='athena',
                        resource_type='named-query',
                        resource_id=nq_id,
                        arn=arn,
                        name=nq_name,
                        region=region,
                        details={
                            'database': nq.get('Database', ''),
                            'workgroup': nq.get('WorkGroup', ''),
                            'description': nq.get('Description', ''),
                        },
                        tags={},
                    ))
            except Exception:
                pass
    except Exception:
        pass

    return resources
