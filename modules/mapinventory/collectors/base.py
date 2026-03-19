"""
Map Inventory — Collector Base Helpers
Every collector uses make_resource() to produce standardized resource dicts.
"""


def tags_to_dict(tags_list):
    """Convert [{'Key': k, 'Value': v}, ...] to {k: v} dict."""
    if not tags_list:
        return {}
    return {t.get('Key', ''): t.get('Value', '') for t in tags_list if isinstance(t, dict)}


def get_tag_value(tags_list, key):
    """Extract a single tag value from a tags list, or None."""
    if not tags_list:
        return None
    for t in tags_list:
        if isinstance(t, dict) and t.get('Key') == key:
            return t.get('Value')
    return None


def make_resource(service, resource_type, resource_id, arn, name, region,
                  details=None, tags=None, is_default=False):
    """
    Build a standardized resource dictionary.

    Args:
        service: lowercase service name (e.g. 'ec2', 's3')
        resource_type: resource type (e.g. 'instance', 'bucket')
        resource_id: unique identifier
        arn: AWS ARN (can be constructed or empty string)
        name: display name
        region: AWS region or 'global'
        details: dict of service-specific metadata
        tags: dict of {key: value} tags
        is_default: True if this is a default AWS resource

    Returns:
        dict with standardized keys
    """
    return {
        'service': service,
        'type': resource_type,
        'id': resource_id,
        'arn': arn or '',
        'name': name or resource_id,
        'region': region or 'global',
        'is_default': bool(is_default),
        'details': details or {},
        'tags': tags or {},
    }


def not_available(service, resource_type, region, error=''):
    """
    Produce a placeholder resource when a collector cannot run
    (e.g., missing IAM permissions). Never raise — return this instead.
    """
    return make_resource(
        service=service,
        resource_type=resource_type,
        resource_id=f'{service}-not-available',
        arn='',
        name=f'{service} (not available)',
        region=region or 'global',
        details={'error': str(error), 'not_available': True},
        tags={},
        is_default=False,
    )
