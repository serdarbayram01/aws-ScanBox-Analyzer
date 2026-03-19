"""
Map Inventory — SNS Collector
Collects: topic, subscription
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_sns_resources(session, region, account_id):
    """Collect SNS resources for a given region."""
    resources = []
    try:
        client = session.client('sns', region_name=region)
    except Exception:
        return resources

    # --- Topics ---
    try:
        topic_arns = []
        paginator = client.get_paginator('list_topics')
        for page in paginator.paginate():
            for topic in page.get('Topics', []):
                topic_arns.append(topic.get('TopicArn', ''))

        for topic_arn in topic_arns:
            try:
                # Get topic attributes
                attr_resp = client.get_topic_attributes(TopicArn=topic_arn)
                attrs = attr_resp.get('Attributes', {})
                # Topic name is the last segment of the ARN
                topic_name = topic_arn.rsplit(':', 1)[-1] if ':' in topic_arn else topic_arn

                # Get tags
                tags_dict = {}
                try:
                    tags_resp = client.list_tags_for_resource(ResourceArn=topic_arn)
                    tags_dict = tags_to_dict(tags_resp.get('Tags', []))
                except Exception:
                    pass

                is_fifo = attrs.get('FifoTopic', 'false').lower() == 'true'

                resources.append(make_resource(
                    service='sns',
                    resource_type='topic',
                    resource_id=topic_name,
                    arn=topic_arn,
                    name=attrs.get('DisplayName', '') or topic_name,
                    region=region,
                    details={
                        'display_name': attrs.get('DisplayName', ''),
                        'subscriptions_confirmed': int(attrs.get('SubscriptionsConfirmed', 0)),
                        'kms_master_key_id': attrs.get('KmsMasterKeyId', ''),
                        'fifo_topic': is_fifo,
                    },
                    tags=tags_dict,
                ))
            except Exception:
                pass
    except Exception:
        pass

    # --- Subscriptions ---
    try:
        paginator = client.get_paginator('list_subscriptions')
        for page in paginator.paginate():
            for sub in page.get('Subscriptions', []):
                sub_arn = sub.get('SubscriptionArn', '')
                # Skip PendingConfirmation subscriptions
                if sub_arn == 'PendingConfirmation':
                    continue
                topic_arn = sub.get('TopicArn', '')
                protocol = sub.get('Protocol', '')
                endpoint = sub.get('Endpoint', '')
                owner = sub.get('Owner', '')
                # Derive a readable name
                topic_name = topic_arn.rsplit(':', 1)[-1] if ':' in topic_arn else topic_arn
                sub_name = f"{topic_name}/{protocol}"

                resources.append(make_resource(
                    service='sns',
                    resource_type='subscription',
                    resource_id=sub_arn,
                    arn=sub_arn,
                    name=sub_name,
                    region=region,
                    details={
                        'topic_arn': topic_arn,
                        'protocol': protocol,
                        'endpoint': endpoint,
                        'owner': owner,
                    },
                    tags={},
                ))
    except Exception:
        pass

    return resources
