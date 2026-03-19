"""
Map Inventory — Security Lake Collector
Resource types: data-lake, subscriber
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_securitylake_resources(session, region, account_id):
    """Collect all Security Lake resource types in the given region."""
    resources = []
    try:
        client = session.client('securitylake', region_name=region)
    except Exception:
        return resources

    # ── Data Lakes ───────────────────────────────────────────────────
    try:
        resp = client.list_data_lakes()
        for dl in resp.get('dataLakes', []):
            dl_arn = dl.get('dataLakeArn', '')
            dl_region = dl.get('region', region)
            dl_id = dl_arn.split('/')[-1] if '/' in dl_arn else f"data-lake-{dl_region}"
            lifecycle = dl.get('lifecycleConfiguration', {})
            encryption = dl.get('encryptionConfiguration', {})
            replication = dl.get('replicationConfiguration', {})
            # Fetch tags
            dl_tags = {}
            try:
                tag_resp = client.list_tags_for_resource(resourceArn=dl_arn)
                dl_tags = tag_resp.get('tags', {})
            except Exception:
                pass
            resources.append(make_resource(
                service='securitylake',
                resource_type='data-lake',
                resource_id=dl_id,
                arn=dl_arn,
                name=f"Security Lake ({dl_region})",
                region=dl_region,
                details={
                    'status': dl.get('createStatus', ''),
                    's3_bucket_arn': dl.get('s3BucketArn', ''),
                    'encryption_key': encryption.get('kmsKeyId', ''),
                    'lifecycle_expiration_days': lifecycle.get(
                        'expiration', {}).get('days', ''),
                    'lifecycle_transitions': lifecycle.get('transitions', []),
                    'replication_role_arn': replication.get('roleArn', ''),
                    'replication_regions': replication.get('regions', []),
                    'update_status': str(dl.get('updateStatus', '')),
                },
                tags=dl_tags if isinstance(dl_tags, dict) else {},
            ))
    except Exception:
        pass

    # ── Subscribers ──────────────────────────────────────────────────
    try:
        resp = client.list_subscribers()
        for sub in resp.get('subscribers', []):
            sub_id = sub.get('subscriberId', '')
            sub_arn = sub.get('subscriberArn', '')
            sub_name = sub.get('subscriberName', sub_id)
            # Fetch tags
            sub_tags = {}
            try:
                tag_resp = client.list_tags_for_resource(resourceArn=sub_arn)
                sub_tags = tag_resp.get('tags', {})
            except Exception:
                pass
            sources = sub.get('sources', [])
            identity = sub.get('subscriberIdentity', {})
            resources.append(make_resource(
                service='securitylake',
                resource_type='subscriber',
                resource_id=sub_id,
                arn=sub_arn,
                name=sub_name,
                region=region,
                details={
                    'status': sub.get('subscriberStatus', ''),
                    'subscriber_description': sub.get('subscriberDescription', ''),
                    'access_types': sub.get('accessTypes', []),
                    'subscriber_endpoint': sub.get('subscriberEndpoint', ''),
                    'external_id': identity.get('externalId', ''),
                    'principal': identity.get('principal', ''),
                    'role_arn': sub.get('roleArn', ''),
                    's3_bucket_arn': sub.get('s3BucketArn', ''),
                    'source_count': len(sources),
                    'created_at': str(sub.get('createdAt', '')),
                    'updated_at': str(sub.get('updatedAt', '')),
                },
                tags=sub_tags if isinstance(sub_tags, dict) else {},
            ))
    except Exception:
        pass

    return resources
