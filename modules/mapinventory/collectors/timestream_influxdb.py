"""
Map Inventory — Amazon Timestream for InfluxDB Collector
Resource types: db-instance
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_timestream_influxdb_resources(session, region, account_id):
    """Collect Timestream for InfluxDB instances in the given region."""
    resources = []
    try:
        client = session.client('timestream-influxdb', region_name=region)
    except Exception:
        return resources

    # ── DB Instances ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_db_instances')
        for page in paginator.paginate():
            for inst in page.get('items', []):
                iid = inst.get('id', '')
                arn = inst.get('arn', '')
                name = inst.get('name', iid)
                tags_dict = {}
                try:
                    tag_resp = client.list_tags_for_resource(resourceArn=arn)
                    tags_dict = tag_resp.get('tags', {})
                except Exception:
                    pass
                resources.append(make_resource(
                    service='timestream-influxdb',
                    resource_type='db-instance',
                    resource_id=iid,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': inst.get('status', ''),
                        'endpoint': inst.get('endpoint', ''),
                        'db_instance_type': inst.get('dbInstanceType', ''),
                        'db_storage_type': inst.get('dbStorageType', ''),
                        'allocated_storage': inst.get('allocatedStorage', 0),
                        'deployment_type': inst.get('deploymentType', ''),
                    },
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
