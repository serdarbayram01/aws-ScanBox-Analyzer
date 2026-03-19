"""
Map Inventory — Kinesis Collector
Resource types: stream, stream-consumer
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_kinesis_resources(session, region, account_id):
    """Collect Kinesis Data Streams resources for a given region."""
    resources = []
    try:
        client = session.client('kinesis', region_name=region)
    except Exception:
        return resources

    # ── Streams ───────────────────────────────────────────────────────
    stream_names = []
    try:
        paginator = client.get_paginator('list_streams')
        for page in paginator.paginate():
            for summary in page.get('StreamSummaries', []):
                stream_names.append(summary.get('StreamName', ''))
    except Exception:
        # Fallback for older SDK without StreamSummaries
        try:
            paginator = client.get_paginator('list_streams')
            for page in paginator.paginate():
                stream_names.extend(page.get('StreamNames', []))
        except Exception:
            pass

    for stream_name in stream_names:
        try:
            resp = client.describe_stream_summary(StreamName=stream_name)
            desc = resp.get('StreamDescriptionSummary', {})
            stream_arn = desc.get('StreamARN', f"arn:aws:kinesis:{region}:{account_id}:stream/{stream_name}")
            stream_status = desc.get('StreamStatus', '')

            tags = {}
            try:
                tag_resp = client.list_tags_for_stream(StreamName=stream_name)
                raw_tags = tag_resp.get('Tags', [])
                tags = tags_to_dict(raw_tags)
            except Exception:
                pass

            resources.append(make_resource(
                service='kinesis',
                resource_type='stream',
                resource_id=stream_name,
                arn=stream_arn,
                name=stream_name,
                region=region,
                details={
                    'status': stream_status,
                    'shard_count': desc.get('OpenShardCount', 0),
                    'retention_period_hours': desc.get('RetentionPeriodHours', 0),
                    'encryption_type': desc.get('EncryptionType', 'NONE'),
                    'key_id': desc.get('KeyId', ''),
                    'stream_mode': desc.get('StreamModeDetails', {}).get('StreamMode', ''),
                    'creation_timestamp': str(desc.get('StreamCreationTimestamp', '')),
                    'consumer_count': desc.get('ConsumerCount', 0),
                },
                tags=tags,
            ))

            # ── Stream Consumers ──────────────────────────────────────
            try:
                consumer_paginator = client.get_paginator('list_stream_consumers')
                for cpage in consumer_paginator.paginate(StreamARN=stream_arn):
                    for consumer in cpage.get('Consumers', []):
                        consumer_name = consumer.get('ConsumerName', '')
                        consumer_arn = consumer.get('ConsumerARN', '')
                        resources.append(make_resource(
                            service='kinesis',
                            resource_type='stream-consumer',
                            resource_id=consumer_name,
                            arn=consumer_arn,
                            name=consumer_name,
                            region=region,
                            details={
                                'stream': stream_name,
                                'status': consumer.get('ConsumerStatus', ''),
                                'creation_timestamp': str(consumer.get('ConsumerCreationTimestamp', '')),
                            },
                            tags={},
                        ))
            except Exception:
                pass

        except Exception:
            pass

    return resources
