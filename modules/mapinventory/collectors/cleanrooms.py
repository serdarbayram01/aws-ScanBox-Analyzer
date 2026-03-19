"""
Map Inventory — Clean Rooms Collector
Resource types: collaboration, configured-table, membership
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_cleanrooms_resources(session, region, account_id):
    """Collect AWS Clean Rooms resources in the given region."""
    resources = []
    try:
        client = session.client('cleanrooms', region_name=region)
    except Exception:
        return resources

    # ── Collaborations ──────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_collaborations')
        for page in paginator.paginate():
            for c in page.get('collaborationList', []):
                cid = c.get('id', '')
                arn = c.get('arn', '')
                resources.append(make_resource(
                    service='cleanrooms',
                    resource_type='collaboration',
                    resource_id=cid,
                    arn=arn,
                    name=c.get('name', cid),
                    region=region,
                    details={
                        'creator_account_id': c.get('creatorAccountId', ''),
                        'creator_display_name': c.get('creatorDisplayName', ''),
                        'member_status': c.get('memberStatus', ''),
                        'create_time': str(c.get('createTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Configured Tables ───────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            for ct in page.get('configuredTableSummaries', []):
                ct_id = ct.get('id', '')
                arn = ct.get('arn', '')
                resources.append(make_resource(
                    service='cleanrooms',
                    resource_type='configured-table',
                    resource_id=ct_id,
                    arn=arn,
                    name=ct.get('name', ct_id),
                    region=region,
                    details={
                        'analysis_method': ct.get('analysisMethod', ''),
                        'create_time': str(ct.get('createTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Memberships ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_memberships')
        for page in paginator.paginate():
            for m in page.get('membershipSummaries', []):
                mid = m.get('id', '')
                arn = m.get('arn', '')
                resources.append(make_resource(
                    service='cleanrooms',
                    resource_type='membership',
                    resource_id=mid,
                    arn=arn,
                    name=m.get('collaborationName', mid),
                    region=region,
                    details={
                        'collaboration_id': m.get('collaborationId', ''),
                        'collaboration_arn': m.get('collaborationArn', ''),
                        'member_status': m.get('status', ''),
                        'create_time': str(m.get('createTime', '')),
                    },
                ))
    except Exception:
        pass

    return resources
