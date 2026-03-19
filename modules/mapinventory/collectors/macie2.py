"""
Map Inventory — Amazon Macie Collector
Resource types: session (enabled check), classification-job, custom-data-identifier
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_macie2_resources(session, region, account_id):
    """Collect all Macie resource types in the given region."""
    resources = []
    try:
        client = session.client('macie2', region_name=region)
    except Exception:
        return resources

    # ── Session (Macie enabled check) ────────────────────────────────
    try:
        resp = client.get_macie_session()
        status = resp.get('status', '')
        service_role = resp.get('serviceRole', '')
        arn = f"arn:aws:macie2:{region}:{account_id}:session"
        resources.append(make_resource(
            service='macie2',
            resource_type='session',
            resource_id=f"macie-session-{region}",
            arn=arn,
            name=f"Macie Session ({region})",
            region=region,
            details={
                'status': status,
                'service_role': service_role,
                'created_at': str(resp.get('createdAt', '')),
                'updated_at': str(resp.get('updatedAt', '')),
                'finding_publishing_frequency': resp.get(
                    'findingPublishingFrequency', ''),
            },
            tags={},
        ))
    except Exception:
        # Macie2Exception / AccessDeniedException means Macie is not enabled
        return resources

    # ── Classification Jobs ──────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_classification_jobs')
        for page in paginator.paginate():
            for job in page.get('items', []):
                job_id = job.get('jobId', '')
                job_name = job.get('name', job_id)
                arn = f"arn:aws:macie2:{region}:{account_id}:classification-job/{job_id}"
                # Fetch tags
                job_tags = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=arn)
                    job_tags = tag_resp.get('tags', {})
                except Exception:
                    pass
                resources.append(make_resource(
                    service='macie2',
                    resource_type='classification-job',
                    resource_id=job_id,
                    arn=arn,
                    name=job_name,
                    region=region,
                    details={
                        'job_type': job.get('jobType', ''),
                        'job_status': job.get('jobStatus', ''),
                        'created_at': str(job.get('createdAt', '')),
                        'last_run_time': str(job.get('lastRunTime', '')),
                        'bucket_count': job.get('bucketCriteria', {}).get(
                            'includes', {}).get('and', []),
                    },
                    tags=job_tags if isinstance(job_tags, dict) else {},
                ))
    except Exception:
        pass

    # ── Custom Data Identifiers ──────────────────────────────────────
    try:
        paginator = client.get_paginator('list_custom_data_identifiers')
        for page in paginator.paginate():
            for cdi in page.get('items', []):
                cdi_id = cdi.get('id', '')
                cdi_name = cdi.get('name', cdi_id)
                cdi_arn = cdi.get('arn', '')
                if not cdi_arn:
                    cdi_arn = f"arn:aws:macie2:{region}:{account_id}:custom-data-identifier/{cdi_id}"
                # Fetch full details
                try:
                    detail = client.get_custom_data_identifier(id=cdi_id)
                    # Fetch tags
                    cdi_tags = {}
                    try:
                        tag_resp = client.list_tags_for_resource(resourceArn=cdi_arn)
                        cdi_tags = tag_resp.get('tags', {})
                    except Exception:
                        pass
                    resources.append(make_resource(
                        service='macie2',
                        resource_type='custom-data-identifier',
                        resource_id=cdi_id,
                        arn=cdi_arn,
                        name=cdi_name,
                        region=region,
                        details={
                            'description': detail.get('description', ''),
                            'regex': detail.get('regex', ''),
                            'keywords': detail.get('keywords', []),
                            'ignore_words': detail.get('ignoreWords', []),
                            'maximum_match_distance': detail.get(
                                'maximumMatchDistance', 0),
                            'severity_levels': detail.get('severityLevels', []),
                            'created_at': str(detail.get('createdAt', '')),
                            'deleted': detail.get('deleted', False),
                        },
                        tags=cdi_tags if isinstance(cdi_tags, dict) else {},
                    ))
                except Exception:
                    resources.append(make_resource(
                        service='macie2',
                        resource_type='custom-data-identifier',
                        resource_id=cdi_id,
                        arn=cdi_arn,
                        name=cdi_name,
                        region=region,
                        details={
                            'description': cdi.get('description', ''),
                            'created_at': str(cdi.get('createdAt', '')),
                        },
                        tags={},
                    ))
    except Exception:
        pass

    return resources
