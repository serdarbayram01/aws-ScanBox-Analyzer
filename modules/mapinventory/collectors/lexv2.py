"""
Map Inventory — Amazon Lex V2 Collector
Resource types: bot
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_lexv2_resources(session, region, account_id):
    """Collect Amazon Lex V2 bots in the given region."""
    resources = []
    try:
        client = session.client('lexv2-models', region_name=region)
    except Exception:
        return resources

    # ── Bots ────────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_bots')
        for page in paginator.paginate():
            for b in page.get('botSummaries', []):
                bid = b.get('botId', '')
                name = b.get('botName', bid)
                arn = f'arn:aws:lex:{region}:{account_id}:bot/{bid}'
                resources.append(make_resource(
                    service='lexv2',
                    resource_type='bot',
                    resource_id=bid,
                    arn=arn,
                    name=name,
                    region=region,
                    details={
                        'description': b.get('description', ''),
                        'bot_status': b.get('botStatus', ''),
                        'bot_type': b.get('botType', ''),
                        'latest_bot_version': b.get('latestBotVersion', ''),
                        'last_updated_date_time': str(b.get('lastUpdatedDateTime', '')),
                    },
                ))
    except Exception:
        pass

    return resources
