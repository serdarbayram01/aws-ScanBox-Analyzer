"""
Map Inventory — AWS AppSync Collector
Resource types: graphql-api
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_appsync_resources(session, region, account_id):
    """Collect AWS AppSync GraphQL API resources in the given region."""
    resources = []
    try:
        client = session.client('appsync', region_name=region)
    except Exception:
        return resources

    # ── GraphQL APIs ─────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.list_graphql_apis(**kwargs)
            for api in resp.get('graphqlApis', []):
                api_id = api.get('apiId', '')
                api_name = api.get('name', api_id)
                api_arn = api.get('arn', '')
                auth_type = api.get('authenticationType', '')

                tags = api.get('tags', {})

                uris = api.get('uris', {})
                additional_auth = api.get('additionalAuthenticationProviders', [])
                auth_providers = [auth_type] + [
                    p.get('authenticationType', '') for p in additional_auth
                ]

                resources.append(make_resource(
                    service='appsync',
                    resource_type='graphql-api',
                    resource_id=api_id,
                    arn=api_arn,
                    name=api_name,
                    region=region,
                    details={
                        'authentication_type': auth_type,
                        'all_auth_providers': auth_providers,
                        'api_type': api.get('apiType', ''),
                        'graphql_uri': uris.get('GRAPHQL', ''),
                        'realtime_uri': uris.get('REALTIME', ''),
                        'log_config': bool(api.get('logConfig')),
                        'xray_enabled': api.get('xrayEnabled', False),
                        'waf_web_acl_arn': api.get('wafWebAclArn', ''),
                        'visibility': api.get('visibility', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
