"""
Map Inventory — IAM Access Analyzer Collector
Resource types: analyzer
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_accessanalyzer_resources(session, region, account_id):
    """Collect IAM Access Analyzer resources in the given region."""
    resources = []
    try:
        client = session.client('accessanalyzer', region_name=region)
    except Exception:
        return resources

    # ── Analyzers ────────────────────────────────────────────────────
    try:
        next_token = None
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            resp = client.list_analyzers(**kwargs)
            for analyzer in resp.get('analyzers', []):
                analyzer_name = analyzer.get('name', '')
                analyzer_arn = analyzer.get('arn', '')
                analyzer_type = analyzer.get('type', '')
                status = analyzer.get('status', '')
                created = str(analyzer.get('createdAt', ''))
                last_scan = str(analyzer.get('lastResourceAnalyzed', ''))

                tags = analyzer.get('tags', {})

                resources.append(make_resource(
                    service='accessanalyzer',
                    resource_type='analyzer',
                    resource_id=analyzer_name,
                    arn=analyzer_arn,
                    name=analyzer_name,
                    region=region,
                    details={
                        'type': analyzer_type,
                        'status': status,
                        'created_at': created,
                        'last_resource_analyzed': last_scan,
                        'last_resource_analyzed_at': str(analyzer.get('lastResourceAnalyzedAt', '')),
                    },
                    tags=tags,
                ))
            next_token = resp.get('NextToken')
            if not next_token:
                break
    except Exception:
        pass

    return resources
