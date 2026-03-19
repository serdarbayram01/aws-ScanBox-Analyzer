"""
Map Inventory — ACM PCA (Private Certificate Authority) Collector
Resource types: certificate-authority
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_acm_pca_resources(session, region, account_id):
    """Collect all ACM PCA certificate authorities in the given region."""
    resources = []
    try:
        client = session.client('acm-pca', region_name=region)
    except Exception:
        return resources

    # ── Certificate Authorities ──────────────────────────────────────
    try:
        paginator = client.get_paginator('list_certificate_authorities')
        for page in paginator.paginate():
            for ca in page.get('CertificateAuthorities', []):
                ca_arn = ca.get('Arn', '')
                ca_id = ca_arn.split('/')[-1] if '/' in ca_arn else ca_arn
                ca_config = ca.get('CertificateAuthorityConfiguration', {})
                subject = ca_config.get('Subject', {})
                ca_name = subject.get('CommonName', '') or subject.get('Organization', '') or ca_id
                # Fetch tags
                ca_tags = []
                try:
                    tag_resp = client.list_tags(CertificateAuthorityArn=ca_arn)
                    ca_tags = tag_resp.get('Tags', [])
                except Exception:
                    pass
                revocation = ca.get('RevocationConfiguration', {})
                crl_config = revocation.get('CrlConfiguration', {})
                ocsp_config = revocation.get('OcspConfiguration', {})
                resources.append(make_resource(
                    service='acm-pca',
                    resource_type='certificate-authority',
                    resource_id=ca_id,
                    arn=ca_arn,
                    name=get_tag_value(ca_tags, 'Name') or ca_name,
                    region=region,
                    details={
                        'status': ca.get('Status', ''),
                        'type': ca.get('Type', ''),
                        'key_algorithm': ca_config.get('KeyAlgorithm', ''),
                        'signing_algorithm': ca_config.get('SigningAlgorithm', ''),
                        'subject_common_name': subject.get('CommonName', ''),
                        'subject_organization': subject.get('Organization', ''),
                        'subject_country': subject.get('Country', ''),
                        'created_at': str(ca.get('CreatedAt', '')),
                        'not_before': str(ca.get('NotBefore', '')),
                        'not_after': str(ca.get('NotAfter', '')),
                        'last_state_change_at': str(ca.get('LastStateChangeAt', '')),
                        'serial': ca.get('Serial', ''),
                        'key_storage_security_standard': ca.get(
                            'KeyStorageSecurityStandard', ''),
                        'usage_mode': ca.get('UsageMode', ''),
                        'crl_enabled': crl_config.get('Enabled', False),
                        'ocsp_enabled': ocsp_config.get('Enabled', False),
                    },
                    tags=tags_to_dict(ca_tags),
                ))
    except Exception:
        pass

    return resources
