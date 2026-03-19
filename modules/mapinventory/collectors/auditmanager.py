"""
Map Inventory — AWS Audit Manager Collector
Resource types: assessment, framework
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_auditmanager_resources(session, region, account_id):
    """Collect Audit Manager resources in the given region."""
    resources = []
    try:
        client = session.client('auditmanager', region_name=region)
    except Exception:
        return resources

    # ── Assessments ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_assessments')
        for page in paginator.paginate():
            for a in page.get('assessmentMetadata', []):
                aid = a.get('id', '')
                name = a.get('name', aid)
                resources.append(make_resource(
                    service='auditmanager',
                    resource_type='assessment',
                    resource_id=aid,
                    arn=f'arn:aws:auditmanager:{region}:{account_id}:assessment/{aid}',
                    name=name,
                    region=region,
                    details={
                        'status': a.get('status', ''),
                        'compliance_type': a.get('complianceType', ''),
                        'creation_time': str(a.get('creationTime', '')),
                        'last_updated': str(a.get('lastUpdated', '')),
                        'delegations': len(a.get('delegations', [])),
                        'roles': len(a.get('roles', [])),
                    },
                ))
    except Exception:
        pass

    # ── Custom Frameworks ───────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_assessment_frameworks')
        for page in paginator.paginate(frameworkType='Custom'):
            for f in page.get('frameworkMetadataList', []):
                fid = f.get('id', '')
                arn = f.get('arn', '')
                resources.append(make_resource(
                    service='auditmanager',
                    resource_type='framework',
                    resource_id=fid,
                    arn=arn,
                    name=f.get('name', fid),
                    region=region,
                    details={
                        'type': f.get('type', ''),
                        'description': f.get('description', ''),
                        'compliance_type': f.get('complianceType', ''),
                        'controls_count': f.get('controlsCount', 0),
                        'control_sets_count': f.get('controlSetsCount', 0),
                        'created_at': str(f.get('createdAt', '')),
                        'last_updated_at': str(f.get('lastUpdatedAt', '')),
                    },
                ))
    except Exception:
        pass

    return resources
