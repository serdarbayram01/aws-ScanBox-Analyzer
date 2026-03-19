"""
Map Inventory — S3 Collector
S3 is a GLOBAL service. The region parameter is ignored; all buckets are collected.
"""

from datetime import datetime, timedelta

from .base import make_resource, tags_to_dict, get_tag_value


def collect_s3_resources(session, region, account_id):
    """Collect all S3 buckets and their metadata."""
    resources = []
    try:
        s3 = session.client('s3')
    except Exception:
        return resources

    try:
        buckets = s3.list_buckets().get('Buckets', [])
    except Exception:
        return resources

    for bucket in buckets:
        bucket_name = bucket['Name']
        creation_date = str(bucket.get('CreationDate', ''))

        # ── Determine bucket region ────────────────────────────────
        bucket_region = 'us-east-1'  # default when LocationConstraint is None
        try:
            loc = s3.get_bucket_location(Bucket=bucket_name)
            constraint = loc.get('LocationConstraint')
            if constraint:
                bucket_region = constraint
        except Exception:
            pass

        # ── Versioning ─────────────────────────────────────────────
        versioning = None
        try:
            v = s3.get_bucket_versioning(Bucket=bucket_name)
            versioning = v.get('Status')  # 'Enabled', 'Suspended', or None
        except Exception:
            pass

        # ── Encryption ─────────────────────────────────────────────
        encryption = None
        try:
            enc = s3.get_bucket_encryption(Bucket=bucket_name)
            rules = enc.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            if rules:
                encryption = rules[0].get('ApplyServerSideEncryptionByDefault', {}).get('SSEAlgorithm', '')
        except Exception:
            pass

        # ── Public Access Block ────────────────────────────────────
        public_access_blocked = False
        try:
            pab = s3.get_public_access_block(Bucket=bucket_name)
            cfg = pab.get('PublicAccessBlockConfiguration', {})
            public_access_blocked = all([
                cfg.get('BlockPublicAcls', False),
                cfg.get('IgnorePublicAcls', False),
                cfg.get('BlockPublicPolicy', False),
                cfg.get('RestrictPublicBuckets', False),
            ])
        except Exception:
            # NoSuchPublicAccessBlockConfiguration → not set
            pass

        # ── Bucket Policy ──────────────────────────────────────────
        has_policy = False
        try:
            s3.get_bucket_policy(Bucket=bucket_name)
            has_policy = True
        except s3.exceptions.from_code('NoSuchBucketPolicy') if hasattr(s3, 'exceptions') else Exception:
            pass
        except Exception:
            pass

        # ── Logging ────────────────────────────────────────────────
        logging_target = None
        try:
            log_resp = s3.get_bucket_logging(Bucket=bucket_name)
            le = log_resp.get('LoggingEnabled')
            if le:
                logging_target = le.get('TargetBucket', '')
        except Exception:
            pass

        # ── CloudWatch Metrics (size + object count) ───────────────
        size_bytes = None
        object_count = None
        try:
            cw = session.client('cloudwatch', region_name=bucket_region)
            now = datetime.utcnow()
            start = now - timedelta(days=3)

            # BucketSizeBytes
            size_resp = cw.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='BucketSizeBytes',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'},
                ],
                StartTime=start,
                EndTime=now,
                Period=86400,
                Statistics=['Average'],
            )
            dps = size_resp.get('Datapoints', [])
            if dps:
                latest = max(dps, key=lambda d: d['Timestamp'])
                size_bytes = int(latest.get('Average', 0))

            # NumberOfObjects
            count_resp = cw.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='NumberOfObjects',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': 'AllStorageTypes'},
                ],
                StartTime=start,
                EndTime=now,
                Period=86400,
                Statistics=['Average'],
            )
            dps = count_resp.get('Datapoints', [])
            if dps:
                latest = max(dps, key=lambda d: d['Timestamp'])
                object_count = int(latest.get('Average', 0))
        except Exception:
            pass

        # ── Tags ───────────────────────────────────────────────────
        tags = {}
        try:
            tag_resp = s3.get_bucket_tagging(Bucket=bucket_name)
            tags = tags_to_dict(tag_resp.get('TagSet', []))
        except Exception:
            pass

        arn = f"arn:aws:s3:::{bucket_name}"
        resources.append(make_resource(
            service='s3',
            resource_type='bucket',
            resource_id=bucket_name,
            arn=arn,
            name=bucket_name,
            region=bucket_region,
            details={
                'creation_date': creation_date,
                'versioning': versioning,
                'encryption': encryption,
                'public_access_blocked': public_access_blocked,
                'has_policy': has_policy,
                'logging_target': logging_target,
                'size_bytes': size_bytes,
                'object_count': object_count,
            },
            tags=tags,
        ))

    return resources
