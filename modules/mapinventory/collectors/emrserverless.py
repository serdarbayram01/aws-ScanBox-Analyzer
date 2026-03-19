"""
Map Inventory — EMR Serverless Collector
Handled in emr.py — this module returns an empty list.
"""

from .base import make_resource, tags_to_dict


def collect_emrserverless_resources(session, region, account_id):
    """EMR Serverless resources are collected by emr.py. Returns []."""
    return []
