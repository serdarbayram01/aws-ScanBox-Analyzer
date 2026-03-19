"""
Map Inventory — Amazon Transcribe Collector
Resource types: vocabulary, language-model, medical-vocabulary
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_transcribe_resources(session, region, account_id):
    """Collect Amazon Transcribe resources in the given region."""
    resources = []
    try:
        client = session.client('transcribe', region_name=region)
    except Exception:
        return resources

    # ── Custom Vocabularies ─────────────────────────────────────────
    try:
        resp = client.list_vocabularies(MaxResults=100)
        for v in resp.get('Vocabularies', []):
            name = v.get('VocabularyName', '')
            resources.append(make_resource(
                service='transcribe',
                resource_type='vocabulary',
                resource_id=name,
                arn=f'arn:aws:transcribe:{region}:{account_id}:vocabulary/{name}',
                name=name,
                region=region,
                details={
                    'language_code': v.get('LanguageCode', ''),
                    'vocabulary_state': v.get('VocabularyState', ''),
                    'last_modified_time': str(v.get('LastModifiedTime', '')),
                },
            ))
        # Handle pagination via NextToken
        while resp.get('NextToken'):
            resp = client.list_vocabularies(MaxResults=100, NextToken=resp['NextToken'])
            for v in resp.get('Vocabularies', []):
                name = v.get('VocabularyName', '')
                resources.append(make_resource(
                    service='transcribe',
                    resource_type='vocabulary',
                    resource_id=name,
                    arn=f'arn:aws:transcribe:{region}:{account_id}:vocabulary/{name}',
                    name=name,
                    region=region,
                    details={
                        'language_code': v.get('LanguageCode', ''),
                        'vocabulary_state': v.get('VocabularyState', ''),
                        'last_modified_time': str(v.get('LastModifiedTime', '')),
                    },
                ))
    except Exception:
        pass

    # ── Language Models ─────────────────────────────────────────────
    try:
        resp = client.list_language_models(MaxResults=100)
        for m in resp.get('Models', []):
            name = m.get('ModelName', '')
            resources.append(make_resource(
                service='transcribe',
                resource_type='language-model',
                resource_id=name,
                arn=f'arn:aws:transcribe:{region}:{account_id}:language-model/{name}',
                name=name,
                region=region,
                details={
                    'language_code': m.get('LanguageCode', ''),
                    'model_status': m.get('ModelStatus', ''),
                    'base_model_name': m.get('BaseModelName', ''),
                    'create_time': str(m.get('CreateTime', '')),
                    'last_modified_time': str(m.get('LastModifiedTime', '')),
                },
            ))
    except Exception:
        pass

    # ── Medical Vocabularies ────────────────────────────────────────
    try:
        resp = client.list_medical_vocabularies(MaxResults=100)
        for v in resp.get('Vocabularies', []):
            name = v.get('VocabularyName', '')
            resources.append(make_resource(
                service='transcribe',
                resource_type='medical-vocabulary',
                resource_id=name,
                arn=f'arn:aws:transcribe:{region}:{account_id}:medical-vocabulary/{name}',
                name=name,
                region=region,
                details={
                    'language_code': v.get('LanguageCode', ''),
                    'vocabulary_state': v.get('VocabularyState', ''),
                    'last_modified_time': str(v.get('LastModifiedTime', '')),
                },
            ))
    except Exception:
        pass

    return resources
