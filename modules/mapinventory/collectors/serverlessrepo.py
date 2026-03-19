"""
Map Inventory — AWS Serverless Application Repository Collector
Resource types: application
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_serverlessrepo_resources(session, region, account_id):
    """Collect Serverless Application Repository applications in the given region."""
    resources = []
    try:
        client = session.client('serverlessrepo', region_name=region)
    except Exception:
        return resources

    # ── Applications ────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_applications')
        for page in paginator.paginate():
            for app in page.get('Applications', []):
                app_id = app.get('ApplicationId', '')
                name = app.get('Name', app_id.split('/')[-1] if '/' in app_id else app_id)
                resources.append(make_resource(
                    service='serverlessrepo',
                    resource_type='application',
                    resource_id=app_id,
                    arn=app_id,  # ApplicationId is the ARN
                    name=name,
                    region=region,
                    details={
                        'description': app.get('Description', ''),
                        'author': app.get('Author', ''),
                        'creation_time': app.get('CreationTime', ''),
                        'spdx_license_id': app.get('SpdxLicenseId', ''),
                        'labels': app.get('Labels', []),
                    },
                ))
    except Exception:
        pass

    return resources
