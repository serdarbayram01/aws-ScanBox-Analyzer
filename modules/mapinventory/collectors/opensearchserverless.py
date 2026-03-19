"""
Map Inventory — Amazon OpenSearch Serverless Collector
Handled in opensearch.py — this module returns an empty list.
"""

from .base import make_resource, tags_to_dict


def collect_opensearchserverless_resources(session, region, account_id):
    """OpenSearch Serverless resources are collected by opensearch.py. Returns []."""
    return []
