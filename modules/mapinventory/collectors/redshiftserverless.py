"""
Map Inventory — Redshift Serverless Collector
Handled in redshift.py — this module returns an empty list.
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_redshiftserverless_resources(session, region, account_id):
    """Redshift Serverless resources are collected by redshift.py. Returns []."""
    return []
