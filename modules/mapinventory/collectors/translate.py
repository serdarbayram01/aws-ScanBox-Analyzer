"""
Map Inventory — Amazon Translate Collector
Resource types: terminology, parallel-data
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_translate_resources(session, region, account_id):
    """Collect Amazon Translate resources in the given region."""
    resources = []
    try:
        client = session.client('translate', region_name=region)
    except Exception:
        return resources

    # ── Terminologies ───────────────────────────────────────────────
    try:
        resp = client.list_terminologies(MaxSize=500)
        for t in resp.get('TerminologyPropertiesList', []):
            name = t.get('Name', '')
            arn = t.get('Arn', '')
            resources.append(make_resource(
                service='translate',
                resource_type='terminology',
                resource_id=name,
                arn=arn,
                name=name,
                region=region,
                details={
                    'description': t.get('Description', ''),
                    'source_language_code': t.get('SourceLanguageCode', ''),
                    'target_language_codes': t.get('TargetLanguageCodes', []),
                    'size_bytes': t.get('SizeBytes', 0),
                    'term_count': t.get('TermCount', 0),
                    'created_at': str(t.get('CreatedAt', '')),
                    'last_updated_at': str(t.get('LastUpdatedAt', '')),
                    'directionality': t.get('Directionality', ''),
                    'format': t.get('Format', ''),
                },
            ))
    except Exception:
        pass

    # ── Parallel Data ───────────────────────────────────────────────
    try:
        resp = client.list_parallel_data(MaxResults=500)
        for pd in resp.get('ParallelDataPropertiesList', []):
            name = pd.get('Name', '')
            arn = pd.get('Arn', '')
            resources.append(make_resource(
                service='translate',
                resource_type='parallel-data',
                resource_id=name,
                arn=arn,
                name=name,
                region=region,
                details={
                    'description': pd.get('Description', ''),
                    'status': pd.get('Status', ''),
                    'source_language_code': pd.get('SourceLanguageCode', ''),
                    'target_language_codes': pd.get('TargetLanguageCodes', []),
                    'created_at': str(pd.get('CreatedAt', '')),
                    'last_updated_at': str(pd.get('LastUpdatedAt', '')),
                    'imported_record_count': pd.get('ImportedRecordCount', 0),
                    'failed_record_count': pd.get('FailedRecordCount', 0),
                },
            ))
    except Exception:
        pass

    return resources
