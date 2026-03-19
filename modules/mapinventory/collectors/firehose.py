"""
Map Inventory — Firehose Collector
Resource types: delivery-stream
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_firehose_resources(session, region, account_id):
    """Collect Kinesis Data Firehose resources for a given region."""
    resources = []
    try:
        client = session.client('firehose', region_name=region)
    except Exception:
        return resources

    # ── Delivery Streams ──────────────────────────────────────────────
    try:
        stream_names = []
        paginator = client.get_paginator('list_delivery_streams')
        for page in paginator.paginate():
            for ds in page.get('DeliveryStreamNames', []):
                stream_names.append(ds)

        for ds_name in stream_names:
            try:
                resp = client.describe_delivery_stream(DeliveryStreamName=ds_name)
                desc = resp.get('DeliveryStreamDescription', {})
                ds_arn = desc.get('DeliveryStreamARN',
                                 f"arn:aws:firehose:{region}:{account_id}:deliverystream/{ds_name}")
                ds_status = desc.get('DeliveryStreamStatus', '')
                ds_type = desc.get('DeliveryStreamType', '')
                source = desc.get('Source', {})
                destinations = desc.get('Destinations', [])

                # Determine destination type
                dest_type = ''
                if destinations:
                    d = destinations[0]
                    if d.get('S3DestinationDescription'):
                        dest_type = 'S3'
                    elif d.get('ExtendedS3DestinationDescription'):
                        dest_type = 'ExtendedS3'
                    elif d.get('RedshiftDestinationDescription'):
                        dest_type = 'Redshift'
                    elif d.get('ElasticsearchDestinationDescription'):
                        dest_type = 'Elasticsearch'
                    elif d.get('AmazonopensearchserviceDestinationDescription'):
                        dest_type = 'OpenSearch'
                    elif d.get('SplunkDestinationDescription'):
                        dest_type = 'Splunk'
                    elif d.get('HttpEndpointDestinationDescription'):
                        dest_type = 'HttpEndpoint'
                    elif d.get('AmazonOpenSearchServerlessDestinationDescription'):
                        dest_type = 'OpenSearchServerless'

                tags = {}
                try:
                    tag_resp = client.list_tags_for_delivery_stream(
                        DeliveryStreamName=ds_name)
                    tags = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                resources.append(make_resource(
                    service='firehose',
                    resource_type='delivery-stream',
                    resource_id=ds_name,
                    arn=ds_arn,
                    name=ds_name,
                    region=region,
                    details={
                        'status': ds_status,
                        'stream_type': ds_type,
                        'destination_type': dest_type,
                        'destination_count': len(destinations),
                        'encryption': desc.get('DeliveryStreamEncryptionConfiguration', {}).get('Status', 'DISABLED'),
                        'create_timestamp': str(desc.get('CreateTimestamp', '')),
                        'source_kinesis_stream': source.get('KinesisStreamSourceDescription', {}).get('KinesisStreamARN', ''),
                    },
                    tags=tags,
                ))
            except Exception:
                pass
    except Exception:
        pass

    return resources
