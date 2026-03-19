"""
Map Inventory — Amazon Polly Collector
Resource types: lexicon
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_polly_resources(session, region, account_id):
    """Collect Amazon Polly lexicons in the given region."""
    resources = []
    try:
        client = session.client('polly', region_name=region)
    except Exception:
        return resources

    # ── Lexicons ────────────────────────────────────────────────────
    try:
        resp = client.list_lexicons()
        for lex in resp.get('Lexicons', []):
            name = lex.get('Name', '')
            attrs = lex.get('Attributes', {})
            resources.append(make_resource(
                service='polly',
                resource_type='lexicon',
                resource_id=name,
                arn=f'arn:aws:polly:{region}:{account_id}:lexicon/{name}',
                name=name,
                region=region,
                details={
                    'language_code': attrs.get('LanguageCode', ''),
                    'alphabet': attrs.get('Alphabet', ''),
                    'lexemes_count': attrs.get('LexemesCount', 0),
                    'size': attrs.get('Size', 0),
                    'last_modified': str(attrs.get('LastModified', '')),
                },
            ))
    except Exception:
        pass

    return resources
