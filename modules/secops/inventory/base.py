"""
SecOps — Base Finding Helper
All inventory modules use make_finding() to produce consistent finding dicts.
"""

from typing import Optional


SEVERITIES = ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')
STATUSES   = ('PASS', 'FAIL', 'WARNING', 'NOT_AVAILABLE', 'MANUAL')


def make_finding(
    *,
    id: str,
    title: str,
    title_tr: str,
    description: str,
    description_tr: str,
    severity: str,
    status: str,
    service: str,
    resource_id: str        = 'global',
    resource_type: str      = '',
    resource_name: str      = '',
    region: str             = 'global',
    frameworks: Optional[dict] = None,
    remediation: str        = '',
    remediation_tr: str     = '',
    is_default_resource: bool = False,
    details: Optional[dict] = None,
) -> dict:
    """Return a normalised finding dictionary."""
    return {
        'id':                   id,
        'title':                title,
        'title_tr':             title_tr,
        'description':          description,
        'description_tr':       description_tr,
        'severity':             severity,
        'status':               status,
        'service':              service,
        'resource_id':          resource_id,
        'resource_type':        resource_type,
        'resource_name':        resource_name or resource_id,
        'region':               region,
        'frameworks':           frameworks or {},
        'remediation':          remediation,
        'remediation_tr':       remediation_tr,
        'is_default_resource':  is_default_resource,
        'details':              details or {},
    }


def not_available(id: str, service: str, error: str) -> dict:
    """Return a NOT_AVAILABLE finding for a check that couldn't run."""
    return make_finding(
        id=id,
        title=f'{service}: check unavailable',
        title_tr=f'{service}: kontrol kullanılamıyor',
        description=f'Could not run check: {error}',
        description_tr=f'Kontrol çalıştırılamadı: {error}',
        severity='INFO',
        status='NOT_AVAILABLE',
        service=service,
        remediation='Verify IAM permissions for this check.',
        remediation_tr='Bu kontrol için IAM yetkilerini doğrulayın.',
    )
