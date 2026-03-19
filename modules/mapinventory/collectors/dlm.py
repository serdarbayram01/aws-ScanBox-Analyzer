"""
Map Inventory — DLM (Data Lifecycle Manager) Collector
Resource types: lifecycle-policy
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_dlm_resources(session, region, account_id):
    """Collect all DLM lifecycle policies in the given region."""
    resources = []
    try:
        client = session.client('dlm', region_name=region)
    except Exception:
        return resources

    # ── Lifecycle Policies ───────────────────────────────────────────
    try:
        resp = client.get_lifecycle_policies()
        for summary in resp.get('Policies', []):
            policy_id = summary.get('PolicyId', '')
            # Fetch full policy details
            try:
                detail_resp = client.get_lifecycle_policy(PolicyId=policy_id)
                policy = detail_resp.get('Policy', {})
                policy_details = policy.get('PolicyDetails', {})
                tags = policy.get('Tags', {})
                arn = f"arn:aws:dlm:{region}:{account_id}:policy/{policy_id}"
                resources.append(make_resource(
                    service='dlm',
                    resource_type='lifecycle-policy',
                    resource_id=policy_id,
                    arn=arn,
                    name=policy.get('Description', policy_id),
                    region=region,
                    details={
                        'state': policy.get('State', ''),
                        'status_message': policy.get('StatusMessage', ''),
                        'policy_type': policy_details.get('PolicyType', ''),
                        'resource_types': policy_details.get('ResourceTypes', []),
                        'target_tags': policy_details.get('TargetTags', []),
                        'date_created': str(policy.get('DateCreated', '')),
                        'date_modified': str(policy.get('DateModified', '')),
                    },
                    tags=tags if isinstance(tags, dict) else {},
                ))
            except Exception:
                # If detail fetch fails, record summary only
                arn = f"arn:aws:dlm:{region}:{account_id}:policy/{policy_id}"
                resources.append(make_resource(
                    service='dlm',
                    resource_type='lifecycle-policy',
                    resource_id=policy_id,
                    arn=arn,
                    name=summary.get('Description', policy_id),
                    region=region,
                    details={
                        'state': summary.get('State', ''),
                        'policy_type': summary.get('PolicyType', ''),
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
