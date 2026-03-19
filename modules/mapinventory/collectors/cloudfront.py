"""
Map Inventory — CloudFront Collector (GLOBAL)
Collects: distribution, function, origin-access-identity, origin-access-control,
          cache-policy (custom only)
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_cloudfront_resources(session, region, account_id):
    """Collect CloudFront resources. CloudFront is global; region param is ignored."""
    resources = []
    try:
        client = session.client('cloudfront', region_name='us-east-1')
    except Exception:
        return resources

    # --- Distributions ---
    try:
        paginator = client.get_paginator('list_distributions')
        for page in paginator.paginate():
            dist_list = page.get('DistributionList', {})
            for dist in dist_list.get('Items', []):
                dist_id = dist.get('Id', '')
                dist_arn = dist.get('ARN', '')
                domain_name = dist.get('DomainName', '')
                aliases = dist.get('Aliases', {})
                alias_items = aliases.get('Items', []) if aliases else []
                origins = dist.get('Origins', {})
                origin_count = origins.get('Quantity', 0) if origins else 0

                # Fetch tags
                tags_dict = {}
                try:
                    tags_resp = client.list_tags_for_resource(Resource=dist_arn)
                    tags_dict = tags_to_dict(
                        tags_resp.get('Tags', {}).get('Items', [])
                    )
                except Exception:
                    pass

                display_name = alias_items[0] if alias_items else domain_name

                resources.append(make_resource(
                    service='cloudfront',
                    resource_type='distribution',
                    resource_id=dist_id,
                    arn=dist_arn,
                    name=display_name,
                    region='global',
                    details={
                        'domain_name': domain_name,
                        'status': dist.get('Status', ''),
                        'enabled': dist.get('Enabled', False),
                        'aliases': alias_items,
                        'origins_count': origin_count,
                        'price_class': dist.get('PriceClass', ''),
                        'web_acl_id': dist.get('WebACLId', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    # --- Functions ---
    try:
        func_resp = client.list_functions()
        for func_item in func_resp.get('FunctionList', {}).get('Items', []):
            func_name = func_item.get('Name', '')
            func_config = func_item.get('FunctionConfig', {})
            func_metadata = func_item.get('FunctionMetadata', {})
            func_arn = func_metadata.get('FunctionARN', '')
            resources.append(make_resource(
                service='cloudfront',
                resource_type='function',
                resource_id=func_name,
                arn=func_arn,
                name=func_name,
                region='global',
                details={
                    'stage': func_metadata.get('Stage', ''),
                    'status': func_item.get('Status', ''),
                    'comment': func_config.get('Comment', ''),
                    'runtime': func_config.get('Runtime', ''),
                },
                tags={},
            ))
    except Exception:
        pass

    # --- Origin Access Identities ---
    try:
        oai_resp = client.list_cloud_front_origin_access_identities()
        oai_list = oai_resp.get('CloudFrontOriginAccessIdentityList', {})
        for oai in oai_list.get('Items', []):
            oai_id = oai.get('Id', '')
            oai_comment = oai.get('Comment', '')
            oai_s3_user = oai.get('S3CanonicalUserId', '')
            resources.append(make_resource(
                service='cloudfront',
                resource_type='origin-access-identity',
                resource_id=oai_id,
                arn=f"arn:aws:cloudfront::{account_id}:origin-access-identity/{oai_id}",
                name=oai_comment or oai_id,
                region='global',
                details={
                    'comment': oai_comment,
                    's3_canonical_user_id': oai_s3_user,
                },
                tags={},
            ))
    except Exception:
        pass

    # --- Origin Access Controls ---
    try:
        oac_resp = client.list_origin_access_controls()
        oac_list = oac_resp.get('OriginAccessControlList', {})
        for oac in oac_list.get('Items', []):
            oac_id = oac.get('Id', '')
            oac_name = oac.get('Name', '')
            resources.append(make_resource(
                service='cloudfront',
                resource_type='origin-access-control',
                resource_id=oac_id,
                arn=f"arn:aws:cloudfront::{account_id}:origin-access-control/{oac_id}",
                name=oac_name or oac_id,
                region='global',
                details={
                    'description': oac.get('Description', ''),
                    'origin_access_control_origin_type': oac.get('OriginAccessControlOriginType', ''),
                    'signing_protocol': oac.get('SigningProtocol', ''),
                    'signing_behavior': oac.get('SigningBehavior', ''),
                },
                tags={},
            ))
    except Exception:
        pass

    # --- Cache Policies (custom only) ---
    try:
        cp_resp = client.list_cache_policies(Type='custom')
        cp_list = cp_resp.get('CachePolicyList', {})
        for cp_item in cp_list.get('Items', []):
            cp = cp_item.get('CachePolicy', {})
            cp_id = cp.get('Id', '')
            cp_config = cp.get('CachePolicyConfig', {})
            cp_name = cp_config.get('Name', '')
            resources.append(make_resource(
                service='cloudfront',
                resource_type='cache-policy',
                resource_id=cp_id,
                arn=f"arn:aws:cloudfront::{account_id}:cache-policy/{cp_id}",
                name=cp_name or cp_id,
                region='global',
                details={
                    'comment': cp_config.get('Comment', ''),
                    'default_ttl': cp_config.get('DefaultTTL', 0),
                    'max_ttl': cp_config.get('MaxTTL', 0),
                    'min_ttl': cp_config.get('MinTTL', 0),
                },
                tags={},
            ))
    except Exception:
        pass

    return resources
