"""
Map Inventory — Amazon Comprehend Collector
Resource types: entity-recognizer, document-classifier, endpoint
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_comprehend_resources(session, region, account_id):
    """Collect Amazon Comprehend resources in the given region."""
    resources = []
    try:
        client = session.client('comprehend', region_name=region)
    except Exception:
        return resources

    # ── Entity Recognizers ──────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_entity_recognizers')
        for page in paginator.paginate():
            for er in page.get('EntityRecognizerPropertiesList', []):
                arn = er.get('EntityRecognizerArn', '')
                name = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='comprehend',
                    resource_type='entity-recognizer',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': er.get('Status', ''),
                        'language_code': er.get('LanguageCode', ''),
                        'submit_time': str(er.get('SubmitTime', '')),
                        'end_time': str(er.get('EndTime', '')),
                        'version_name': er.get('VersionName', ''),
                    },
                ))
    except Exception:
        pass

    # ── Document Classifiers ────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_document_classifiers')
        for page in paginator.paginate():
            for dc in page.get('DocumentClassifierPropertiesList', []):
                arn = dc.get('DocumentClassifierArn', '')
                name = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='comprehend',
                    resource_type='document-classifier',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': dc.get('Status', ''),
                        'language_code': dc.get('LanguageCode', ''),
                        'submit_time': str(dc.get('SubmitTime', '')),
                        'end_time': str(dc.get('EndTime', '')),
                        'version_name': dc.get('VersionName', ''),
                        'mode': dc.get('Mode', ''),
                    },
                ))
    except Exception:
        pass

    # ── Endpoints ───────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_endpoints')
        for page in paginator.paginate():
            for ep in page.get('EndpointPropertiesList', []):
                arn = ep.get('EndpointArn', '')
                name = arn.split('/')[-1] if '/' in arn else arn
                resources.append(make_resource(
                    service='comprehend',
                    resource_type='endpoint',
                    resource_id=name,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'status': ep.get('Status', ''),
                        'model_arn': ep.get('ModelArn', ''),
                        'desired_model_arn': ep.get('DesiredModelArn', ''),
                        'desired_inference_units': ep.get('DesiredInferenceUnits', 0),
                        'current_inference_units': ep.get('CurrentInferenceUnits', 0),
                        'creation_time': str(ep.get('CreationTime', '')),
                        'last_modified_time': str(ep.get('LastModifiedTime', '')),
                    },
                ))
    except Exception:
        pass

    return resources
