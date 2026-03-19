"""
Map Inventory — Amazon Inspector v2 Collector
Resource types: enabled (account status), filter, coverage
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_inspector2_resources(session, region, account_id):
    """Collect all Inspector v2 resource types in the given region."""
    resources = []
    try:
        client = session.client('inspector2', region_name=region)
    except Exception:
        return resources

    # ── Enabled (Account Status) ─────────────────────────────────────
    try:
        resp = client.batch_get_account_status(accountIds=[account_id])
        for acct in resp.get('accounts', []):
            acct_id = acct.get('accountId', account_id)
            state = acct.get('state', {})
            status = state.get('status', '')
            resource_state = acct.get('resourceState', {})
            arn = f"arn:aws:inspector2:{region}:{account_id}:account"
            resources.append(make_resource(
                service='inspector2',
                resource_type='enabled',
                resource_id=f"inspector2-{acct_id}-{region}",
                arn=arn,
                name=f"Inspector ({region})",
                region=region,
                details={
                    'status': status,
                    'ec2_status': resource_state.get('ec2', {}).get(
                        'status', ''),
                    'ecr_status': resource_state.get('ecr', {}).get(
                        'status', ''),
                    'lambda_status': resource_state.get('lambda', {}).get(
                        'status', ''),
                    'lambda_code_status': resource_state.get(
                        'lambdaCode', {}).get('status', ''),
                },
                tags={},
            ))
    except Exception:
        # If Inspector is not enabled, service may throw AccessDeniedException
        return resources

    # ── Filters ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_filters')
        for page in paginator.paginate():
            for f in page.get('filters', []):
                f_arn = f.get('arn', '')
                f_name = f.get('name', '')
                f_id = f_arn.split('/')[-1] if '/' in f_arn else f_name
                # Fetch tags
                f_tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=f_arn)
                    f_tags = tag_resp.get('tags', {})
                except Exception:
                    pass
                resources.append(make_resource(
                    service='inspector2',
                    resource_type='filter',
                    resource_id=f_id,
                    arn=f_arn,
                    name=f_name,
                    region=region,
                    details={
                        'description': f.get('description', ''),
                        'action': f.get('action', ''),
                        'reason': f.get('reason', ''),
                        'created_at': str(f.get('createdAt', '')),
                        'updated_at': str(f.get('updatedAt', '')),
                    },
                    tags=f_tags if isinstance(f_tags, dict) else {},
                ))
    except Exception:
        pass

    # ── Coverage (resource-level scan status) ────────────────────────
    try:
        paginator = client.get_paginator('list_coverage')
        for page in paginator.paginate():
            for cov in page.get('coveredResources', []):
                res_id = cov.get('resourceId', '')
                res_type = cov.get('resourceType', '')
                scan_type = cov.get('scanType', '')
                res_metadata = cov.get('resourceMetadata', {})
                # Build a unique ID from resource + scan type
                unique_id = f"{res_id}-{scan_type}" if scan_type else res_id
                arn = cov.get('resourceId', '')
                resources.append(make_resource(
                    service='inspector2',
                    resource_type='coverage',
                    resource_id=unique_id,
                    arn=arn,
                    name=res_id,
                    region=region,
                    details={
                        'resource_type': res_type,
                        'scan_type': scan_type,
                        'scan_status': cov.get('scanStatus', {}).get(
                            'statusCode', ''),
                        'scan_status_reason': cov.get('scanStatus', {}).get(
                            'reason', ''),
                        'last_scanned_at': str(cov.get('lastScannedAt', '')),
                        'ec2_instance_tags': res_metadata.get(
                            'ec2', {}).get('tags', {}),
                        'ecr_repository': res_metadata.get(
                            'ecrRepository', {}).get('name', ''),
                        'ecr_image_tags': res_metadata.get(
                            'ecrImage', {}).get('tags', []),
                        'lambda_function_name': res_metadata.get(
                            'lambdaFunction', {}).get('functionName', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
