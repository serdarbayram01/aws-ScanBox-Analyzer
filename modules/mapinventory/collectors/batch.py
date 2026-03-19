"""
Map Inventory — AWS Batch Collector
Resource types: compute-environment, job-queue, job-definition, scheduling-policy
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_batch_resources(session, region, account_id):
    """Collect AWS Batch resources."""
    resources = []
    try:
        client = session.client('batch', region_name=region)
    except Exception:
        return resources

    # ── Compute Environments ─────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.describe_compute_environments(**kwargs)
            for ce in resp.get('computeEnvironments', []):
                ce_name = ce.get('computeEnvironmentName', '')
                ce_arn = ce.get('computeEnvironmentArn', '')
                compute_res = ce.get('computeResources', {})
                tags = ce.get('tags', {})
                resources.append(make_resource(
                    service='batch',
                    resource_type='compute-environment',
                    resource_id=ce_name,
                    arn=ce_arn,
                    name=ce_name,
                    region=region,
                    details={
                        'state': ce.get('state', ''),
                        'status': ce.get('status', ''),
                        'type': ce.get('type', ''),
                        'instance_types': compute_res.get('instanceTypes', []),
                        'min_vcpus': compute_res.get('minvCpus', 0),
                        'max_vcpus': compute_res.get('maxvCpus', 0),
                        'desired_vcpus': compute_res.get('desiredvCpus', 0),
                        'subnets': compute_res.get('subnets', []),
                        'security_group_ids': compute_res.get('securityGroupIds', []),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Job Queues ───────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.describe_job_queues(**kwargs)
            for jq in resp.get('jobQueues', []):
                jq_name = jq.get('jobQueueName', '')
                jq_arn = jq.get('jobQueueArn', '')
                tags = jq.get('tags', {})
                ce_order = jq.get('computeEnvironmentOrder', [])
                resources.append(make_resource(
                    service='batch',
                    resource_type='job-queue',
                    resource_id=jq_name,
                    arn=jq_arn,
                    name=jq_name,
                    region=region,
                    details={
                        'state': jq.get('state', ''),
                        'status': jq.get('status', ''),
                        'priority': jq.get('priority', 0),
                        'scheduling_policy_arn': jq.get('schedulingPolicyArn', ''),
                        'compute_environment_count': len(ce_order),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Job Definitions (ACTIVE only) ────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {'maxResults': 100, 'status': 'ACTIVE'}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = client.describe_job_definitions(**kwargs)
            for jd in resp.get('jobDefinitions', []):
                jd_name = jd.get('jobDefinitionName', '')
                jd_arn = jd.get('jobDefinitionArn', '')
                revision = jd.get('revision', 0)
                tags = jd.get('tags', {})
                display_name = f"{jd_name}:{revision}"
                resources.append(make_resource(
                    service='batch',
                    resource_type='job-definition',
                    resource_id=display_name,
                    arn=jd_arn,
                    name=display_name,
                    region=region,
                    details={
                        'type': jd.get('type', ''),
                        'revision': revision,
                        'status': jd.get('status', ''),
                        'platform_capabilities': jd.get('platformCapabilities', []),
                        'propagate_tags': jd.get('propagateTags', False),
                    },
                    tags=tags,
                ))
            next_token = resp.get('nextToken')
            if not next_token:
                break
    except Exception:
        pass

    # ── Scheduling Policies ──────────────────────────────────────────
    try:
        resp = client.list_scheduling_policies()
        sp_arns = [sp.get('arn', '') for sp in resp.get('schedulingPolicies', []) if sp.get('arn')]
        # describe_scheduling_policies accepts list of ARNs
        if sp_arns:
            desc_resp = client.describe_scheduling_policies(arns=sp_arns)
            for sp in desc_resp.get('schedulingPolicies', []):
                sp_name = sp.get('name', '')
                sp_arn = sp.get('arn', '')
                tags = sp.get('tags', {})
                fairshare = sp.get('fairsharePolicy', {})
                resources.append(make_resource(
                    service='batch',
                    resource_type='scheduling-policy',
                    resource_id=sp_name,
                    arn=sp_arn,
                    name=sp_name,
                    region=region,
                    details={
                        'share_decay_seconds': fairshare.get('shareDecaySeconds', 0),
                        'compute_reservation': fairshare.get('computeReservation', 0),
                        'share_distribution_count': len(fairshare.get('shareDistribution', [])),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
