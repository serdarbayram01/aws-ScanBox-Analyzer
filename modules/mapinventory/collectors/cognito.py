"""
Map Inventory — Cognito Collector
Resource types: user-pool, user-pool-client, identity-pool
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_cognito_resources(session, region, account_id):
    """Collect Cognito resources for a given region."""
    resources = []

    # ── User Pools + Clients ──────────────────────────────────────────
    try:
        idp_client = session.client('cognito-idp', region_name=region)

        pool_ids = []
        paginator = idp_client.get_paginator('list_user_pools')
        for page in paginator.paginate(MaxResults=60):
            for pool in page.get('UserPools', []):
                pool_id = pool.get('Id', '')
                pool_name = pool.get('Name', pool_id)
                pool_ids.append((pool_id, pool_name))

                arn = f"arn:aws:cognito-idp:{region}:{account_id}:userpool/{pool_id}"

                # Get detail + tags
                details_dict = {
                    'status': pool.get('Status', ''),
                    'creation_date': str(pool.get('CreationDate', '')),
                    'last_modified_date': str(pool.get('LastModifiedDate', '')),
                    'lambda_config': bool(pool.get('LambdaConfig')),
                }
                tags = {}
                try:
                    desc = idp_client.describe_user_pool(UserPoolId=pool_id)
                    up = desc.get('UserPool', {})
                    details_dict.update({
                        'estimated_number_of_users': up.get('EstimatedNumberOfUsers', 0),
                        'mfa_configuration': up.get('MfaConfiguration', 'OFF'),
                        'deletion_protection': up.get('DeletionProtection', 'INACTIVE'),
                        'schema_attributes': len(up.get('SchemaAttributes', [])),
                        'auto_verified_attributes': up.get('AutoVerifiedAttributes', []),
                        'username_attributes': up.get('UsernameAttributes', []),
                    })
                    tags = up.get('UserPoolTags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='cognito',
                    resource_type='user-pool',
                    resource_id=pool_id,
                    arn=arn,
                    name=pool_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                ))

        # ── User Pool Clients per pool ────────────────────────────────
        for pool_id, pool_name in pool_ids:
            try:
                client_paginator = idp_client.get_paginator('list_user_pool_clients')
                for cpage in client_paginator.paginate(UserPoolId=pool_id, MaxResults=60):
                    for upc in cpage.get('UserPoolClients', []):
                        client_id = upc.get('ClientId', '')
                        client_name = upc.get('ClientName', client_id)

                        # Get full client details
                        client_details = {
                            'user_pool_id': pool_id,
                            'user_pool_name': pool_name,
                        }
                        try:
                            cd = idp_client.describe_user_pool_client(
                                UserPoolId=pool_id, ClientId=client_id
                            )
                            c = cd.get('UserPoolClient', {})
                            client_details.update({
                                'explicit_auth_flows': c.get('ExplicitAuthFlows', []),
                                'allowed_oauth_flows': c.get('AllowedOAuthFlows', []),
                                'allowed_oauth_scopes': c.get('AllowedOAuthScopes', []),
                                'callback_urls': c.get('CallbackURLs', []),
                                'logout_urls': c.get('LogoutURLs', []),
                                'token_validity_units': c.get('TokenValidityUnits', {}),
                                'prevent_user_existence_errors': c.get('PreventUserExistenceErrors', ''),
                                'enable_token_revocation': c.get('EnableTokenRevocation', False),
                            })
                        except Exception:
                            pass

                        arn = f"arn:aws:cognito-idp:{region}:{account_id}:userpool/{pool_id}/client/{client_id}"
                        resources.append(make_resource(
                            service='cognito',
                            resource_type='user-pool-client',
                            resource_id=client_id,
                            arn=arn,
                            name=client_name,
                            region=region,
                            details=client_details,
                            tags={},
                        ))
            except Exception:
                pass

    except Exception:
        pass

    # ── Identity Pools ────────────────────────────────────────────────
    try:
        identity_client = session.client('cognito-identity', region_name=region)
        paginator = identity_client.get_paginator('list_identity_pools')
        for page in paginator.paginate(MaxResults=60):
            for ip in page.get('IdentityPools', []):
                ip_id = ip.get('IdentityPoolId', '')
                ip_name = ip.get('IdentityPoolName', ip_id)
                arn = f"arn:aws:cognito-identity:{region}:{account_id}:identitypool/{ip_id}"

                details_dict = {}
                tags = {}
                try:
                    desc = identity_client.describe_identity_pool(IdentityPoolId=ip_id)
                    details_dict = {
                        'allow_unauthenticated': desc.get('AllowUnauthenticatedIdentities', False),
                        'allow_classic_flow': desc.get('AllowClassicFlow', False),
                        'cognito_identity_providers': [
                            {
                                'provider_name': p.get('ProviderName', ''),
                                'client_id': p.get('ClientId', ''),
                                'server_side_token_check': p.get('ServerSideTokenCheck', False),
                            }
                            for p in desc.get('CognitoIdentityProviders', [])
                        ],
                        'saml_provider_arns': desc.get('SamlProviderARNs', []),
                        'open_id_connect_provider_arns': desc.get('OpenIdConnectProviderARNs', []),
                        'supported_login_providers': desc.get('SupportedLoginProviders', {}),
                    }
                    tags = desc.get('IdentityPoolTags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='cognito',
                    resource_type='identity-pool',
                    resource_id=ip_id,
                    arn=arn,
                    name=ip_name,
                    region=region,
                    details=details_dict,
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
