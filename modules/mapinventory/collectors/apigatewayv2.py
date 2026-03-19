"""
Map Inventory — API Gateway v2 (HTTP / WebSocket) Collector
Resource types: http-api, websocket-api, stage, vpc-link, domain-name
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_apigatewayv2_resources(session, region, account_id):
    """Collect API Gateway v2 (HTTP & WebSocket) resources for a given region."""
    resources = []
    try:
        client = session.client('apigatewayv2', region_name=region)
    except Exception:
        return resources

    # ── APIs (HTTP + WebSocket) ───────────────────────────────────────
    try:
        apis = []
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.get_apis(**kwargs)
            apis.extend(resp.get('Items', []))
            next_token = resp.get('NextToken')
            if not next_token:
                break

        for api in apis:
            api_id = api.get('ApiId', '')
            api_name = api.get('Name', api_id)
            protocol = api.get('ProtocolType', '')  # HTTP or WEBSOCKET
            arn = f"arn:aws:apigateway:{region}::/apis/{api_id}"
            tags = api.get('Tags', {})

            resource_type = 'http-api' if protocol == 'HTTP' else 'websocket-api'

            resources.append(make_resource(
                service='apigatewayv2',
                resource_type=resource_type,
                resource_id=api_id,
                arn=arn,
                name=api_name,
                region=region,
                details={
                    'protocol_type': protocol,
                    'description': api.get('Description', ''),
                    'api_endpoint': api.get('ApiEndpoint', ''),
                    'route_selection_expression': api.get('RouteSelectionExpression', ''),
                    'api_gateway_managed': api.get('ApiGatewayManaged', False),
                    'disable_execute_api_endpoint': api.get('DisableExecuteApiEndpoint', False),
                    'created_date': str(api.get('CreatedDate', '')),
                    'cors_configuration': bool(api.get('CorsConfiguration')),
                },
                tags=tags,
            ))

            # ── Stages per API ────────────────────────────────────────
            try:
                stg_next = None
                while True:
                    stg_kwargs = {'ApiId': api_id}
                    if stg_next:
                        stg_kwargs['NextToken'] = stg_next
                    stg_resp = client.get_stages(**stg_kwargs)
                    for stg in stg_resp.get('Items', []):
                        stg_name = stg.get('StageName', '')
                        stg_arn = f"arn:aws:apigateway:{region}::/apis/{api_id}/stages/{stg_name}"
                        stg_tags = stg.get('Tags', {})

                        resources.append(make_resource(
                            service='apigatewayv2',
                            resource_type='stage',
                            resource_id=f"{api_id}/{stg_name}",
                            arn=stg_arn,
                            name=stg_name,
                            region=region,
                            details={
                                'api_id': api_id,
                                'api_name': api_name,
                                'protocol_type': protocol,
                                'deployment_id': stg.get('DeploymentId', ''),
                                'description': stg.get('Description', ''),
                                'auto_deploy': stg.get('AutoDeploy', False),
                                'api_gateway_managed': stg.get('ApiGatewayManaged', False),
                                'created_date': str(stg.get('CreatedDate', '')),
                                'last_updated_date': str(stg.get('LastUpdatedDate', '')),
                            },
                            tags=stg_tags,
                        ))
                    stg_next = stg_resp.get('NextToken')
                    if not stg_next:
                        break
            except Exception:
                pass
    except Exception:
        pass

    # ── VPC Links ─────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.get_vpc_links(**kwargs)
            for vl in resp.get('Items', []):
                vl_id = vl.get('VpcLinkId', '')
                vl_name = vl.get('Name', vl_id)
                arn = f"arn:aws:apigateway:{region}::/vpclinks/{vl_id}"
                tags = vl.get('Tags', {})

                resources.append(make_resource(
                    service='apigatewayv2',
                    resource_type='vpc-link',
                    resource_id=vl_id,
                    arn=arn,
                    name=vl_name,
                    region=region,
                    details={
                        'vpc_link_status': vl.get('VpcLinkStatus', ''),
                        'vpc_link_status_message': vl.get('VpcLinkStatusMessage', ''),
                        'vpc_link_version': vl.get('VpcLinkVersion', ''),
                        'security_group_ids': vl.get('SecurityGroupIds', []),
                        'subnet_ids': vl.get('SubnetIds', []),
                        'created_date': str(vl.get('CreatedDate', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Domain Names ──────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.get_domain_names(**kwargs)
            for dn in resp.get('Items', []):
                domain = dn.get('DomainName', '')
                arn = f"arn:aws:apigateway:{region}::/domainnames/{domain}"
                tags = dn.get('Tags', {})
                configs = dn.get('DomainNameConfigurations', [])

                endpoint_type = ''
                certificate_arn = ''
                if configs:
                    endpoint_type = configs[0].get('EndpointType', '')
                    certificate_arn = configs[0].get('CertificateArn', '')

                resources.append(make_resource(
                    service='apigatewayv2',
                    resource_type='domain-name',
                    resource_id=domain,
                    arn=arn,
                    name=domain,
                    region=region,
                    details={
                        'endpoint_type': endpoint_type,
                        'certificate_arn': certificate_arn,
                        'mutual_tls_authentication': bool(dn.get('MutualTlsAuthentication')),
                        'api_mapping_selection_expression': dn.get('ApiMappingSelectionExpression', ''),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
