"""
Map Inventory — SQS Collector
Collects: queue
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_sqs_resources(session, region, account_id):
    """Collect SQS resources for a given region."""
    resources = []
    try:
        client = session.client('sqs', region_name=region)
    except Exception:
        return resources

    try:
        queue_urls = []
        paginator = client.get_paginator('list_queues')
        for page in paginator.paginate():
            queue_urls.extend(page.get('QueueUrls', []))

        for queue_url in queue_urls:
            try:
                # Get all attributes
                attr_resp = client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['All']
                )
                attrs = attr_resp.get('Attributes', {})
                queue_arn = attrs.get('QueueArn', '')
                # Extract queue name from URL (last segment)
                queue_name = queue_url.rsplit('/', 1)[-1] if '/' in queue_url else queue_url

                # Get tags
                tags_dict = {}
                try:
                    tags_resp = client.list_queue_tags(QueueUrl=queue_url)
                    tags_dict = tags_resp.get('Tags', {})
                except Exception:
                    pass

                # Parse redrive policy for dead letter target
                dead_letter_target_arn = ''
                redrive_policy = attrs.get('RedrivePolicy', '')
                if redrive_policy:
                    try:
                        import json
                        rp = json.loads(redrive_policy)
                        dead_letter_target_arn = rp.get('deadLetterTargetArn', '')
                    except Exception:
                        pass

                is_fifo = attrs.get('FifoQueue', 'false').lower() == 'true'

                resources.append(make_resource(
                    service='sqs',
                    resource_type='queue',
                    resource_id=queue_name,
                    arn=queue_arn,
                    name=queue_name,
                    region=region,
                    details={
                        'url': queue_url,
                        'approximate_messages': int(attrs.get('ApproximateNumberOfMessages', 0)),
                        'fifo_queue': is_fifo,
                        'kms_master_key_id': attrs.get('KmsMasterKeyId', ''),
                        'dead_letter_target_arn': dead_letter_target_arn,
                        'visibility_timeout': int(attrs.get('VisibilityTimeout', 0)),
                        'message_retention_period': int(attrs.get('MessageRetentionPeriod', 0)),
                    },
                    tags=tags_dict if isinstance(tags_dict, dict) else {},
                ))
            except Exception:
                pass
    except Exception:
        pass

    return resources
