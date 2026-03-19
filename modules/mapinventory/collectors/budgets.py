"""
Map Inventory — AWS Budgets Collector
Resource types: budget
GLOBAL — uses us-east-1, requires AccountId.
"""

from .base import make_resource, tags_to_dict


def collect_budgets_resources(session, region, account_id):
    """Collect AWS Budgets (global service, ignores region param)."""
    resources = []
    try:
        client = session.client('budgets', region_name='us-east-1')
    except Exception:
        return resources

    # ── Budgets ──────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('describe_budgets')
        for page in paginator.paginate(AccountId=account_id):
            for b in page.get('Budgets', []):
                name = b.get('BudgetName', '')
                budget_type = b.get('BudgetType', '')
                limit = b.get('BudgetLimit', {})
                time_unit = b.get('TimeUnit', '')
                time_period = b.get('TimePeriod', {})
                cost_filters = b.get('CostFilters', {})
                calculated = b.get('CalculatedSpend', {})
                actual = calculated.get('ActualSpend', {})
                forecasted = calculated.get('ForecastedSpend', {})
                resources.append(make_resource(
                    service='budgets',
                    resource_type='budget',
                    resource_id=name,
                    arn=f'arn:aws:budgets::{account_id}:budget/{name}',
                    name=name,
                    region='global',
                    details={
                        'budget_type': budget_type,
                        'time_unit': time_unit,
                        'limit_amount': limit.get('Amount', ''),
                        'limit_unit': limit.get('Unit', ''),
                        'start': str(time_period.get('Start', '')),
                        'end': str(time_period.get('End', '')),
                        'cost_filters': str(cost_filters),
                        'actual_amount': actual.get('Amount', ''),
                        'actual_unit': actual.get('Unit', ''),
                        'forecasted_amount': forecasted.get('Amount', ''),
                        'forecasted_unit': forecasted.get('Unit', ''),
                    },
                ))
    except Exception:
        pass

    return resources
