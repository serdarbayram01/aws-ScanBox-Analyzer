"""
Map Inventory — ACM Collector
Resource types: certificate
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_acm_resources(session, region, account_id):
    """Collect all ACM certificate resources in the given region."""
    resources = []
    try:
        acm = session.client('acm', region_name=region)
    except Exception:
        return resources

    # ── Certificates ─────────────────────────────────────────────────
    try:
        paginator = acm.get_paginator('list_certificates')
        for page in paginator.paginate():
            for cert_summary in page.get('CertificateSummaryList', []):
                cert_arn = cert_summary.get('CertificateArn', '')
                domain = cert_summary.get('DomainName', '')
                details = {
                    'domain_name': domain,
                    'status': cert_summary.get('Status', ''),
                    'type': cert_summary.get('Type', ''),
                    'key_algorithm': cert_summary.get('KeyAlgorithm', ''),
                }
                tags_dict = {}

                # Describe for full details
                try:
                    desc = acm.describe_certificate(CertificateArn=cert_arn)
                    cert = desc.get('Certificate', {})
                    details.update({
                        'domain_name': cert.get('DomainName', domain),
                        'subject_alternative_names': cert.get('SubjectAlternativeNames', []),
                        'status': cert.get('Status', details.get('status', '')),
                        'type': cert.get('Type', details.get('type', '')),
                        'key_algorithm': cert.get('KeyAlgorithm', details.get('key_algorithm', '')),
                        'issuer': cert.get('Issuer', ''),
                        'not_after': str(cert.get('NotAfter', '')),
                        'not_before': str(cert.get('NotBefore', '')),
                        'in_use_by': cert.get('InUseBy', []),
                        'renewal_eligibility': cert.get('RenewalEligibility', ''),
                        'serial': cert.get('Serial', ''),
                        'created_at': str(cert.get('CreatedAt', '')),
                        'imported_at': str(cert.get('ImportedAt', '')),
                        'issued_at': str(cert.get('IssuedAt', '')),
                    })
                except Exception:
                    pass

                # Tags
                try:
                    tag_resp = acm.list_tags_for_certificate(CertificateArn=cert_arn)
                    tags_dict = tags_to_dict(tag_resp.get('Tags', []))
                except Exception:
                    pass

                name = get_tag_value(
                    tag_resp.get('Tags', []) if tags_dict else [],
                    'Name'
                ) or domain or cert_arn.split('/')[-1]

                resources.append(make_resource(
                    service='acm',
                    resource_type='certificate',
                    resource_id=cert_arn.split('/')[-1] if '/' in cert_arn else cert_arn,
                    arn=cert_arn,
                    name=name,
                    region=region,
                    details=details,
                    tags=tags_dict,
                ))
    except Exception:
        pass

    return resources
