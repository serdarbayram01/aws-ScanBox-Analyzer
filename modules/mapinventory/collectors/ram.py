"""
Map Inventory — AWS Resource Access Manager (RAM) Collector
Resource types: resource-share
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_ram_resources(session, region, account_id):
    """Collect RAM resource shares in the given region."""
    resources = []
    try:
        client = session.client('ram', region_name=region)
    except Exception:
        return resources

    # ── Resource Shares ─────────────────────────────────────────────
    for owner in ['SELF', 'OTHER-ACCOUNTS']:
        try:
            paginator = client.get_paginator('get_resource_shares')
            for page in paginator.paginate(resourceOwner=owner):
                for rs in page.get('resourceShares', []):
                    arn = rs.get('resourceShareArn', '')
                    name = rs.get('name', arn.split('/')[-1] if '/' in arn else arn)
                    tags_dict = tags_to_dict(rs.get('tags', []))
                    resources.append(make_resource(
                        service='ram',
                        resource_type='resource-share',
                        resource_id=arn.split(':')[-1] if ':' in arn else arn,
                        arn=arn,
                        name=name,
                        region=region,
                        details={
                            'status': rs.get('status', ''),
                            'owner': owner,
                            'owning_account_id': rs.get('owningAccountId', ''),
                            'allow_external_principals': rs.get('allowExternalPrincipals', False),
                            'creation_time': str(rs.get('creationTime', '')),
                            'last_updated_time': str(rs.get('lastUpdatedTime', '')),
                        },
                        tags=tags_dict,
                    ))
        except Exception:
            pass

    return resources
