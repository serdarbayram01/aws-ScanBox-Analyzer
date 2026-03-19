"""SecOps — ACM Checks: expiring/expired certificates, validation status."""
from .base import make_finding, not_available
from datetime import datetime, timezone, timedelta

SERVICE = 'ACM'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('acm_regions', SERVICE, str(exc))]

    now = datetime.now(timezone.utc)

    for region in regions:
        acm = session.client('acm', region_name=region)
        try:
            paginator = acm.get_paginator('list_certificates')
            for page in paginator.paginate(CertificateStatuses=['ISSUED', 'EXPIRED', 'FAILED', 'PENDING_VALIDATION']):
                for cert_summary in page.get('CertificateSummaryList', []):
                    arn    = cert_summary['CertificateArn']
                    domain = cert_summary.get('DomainName', arn)

                    try:
                        detail = acm.describe_certificate(CertificateArn=arn)['Certificate']
                    except Exception:
                        detail = cert_summary

                    status     = detail.get('Status', '')
                    not_after  = detail.get('NotAfter')
                    not_before = detail.get('NotBefore')
                    in_use     = bool(detail.get('InUseBy', []))

                    # Expired certificate
                    if status == 'EXPIRED':
                        findings.append(make_finding(
                            id=f'acm_expired_{arn.split("/")[-1]}_{region}',
                            title=f'ACM certificate expired: {domain}',
                            title_tr=f'ACM sertifikası süresi dolmuş: {domain}',
                            description=f'ACM certificate for {domain} in {region} has expired. Any service using it is serving invalid TLS.',
                            description_tr=f'{region} bölgesindeki {domain} için ACM sertifikasının süresi dolmuş. Kullanan servisler geçersiz TLS sunuyor.',
                            severity='CRITICAL', status='FAIL',
                            service=SERVICE, resource_id=arn,
                            resource_type='AWS::CertificateManager::Certificate', region=region,
                            frameworks={
                                'CIS': ['2.1.3'], 'HIPAA': ['164.312(e)(2)(ii)'],
                                'ISO27001': ['A.10.1.2'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
                            },
                            remediation=f'Renew or replace expired certificate {domain} in ACM immediately.',
                            remediation_tr=f'ACM\'deki {domain} sertifikasını hemen yenileyin veya değiştirin.',
                        ))
                        continue

                    # Expiring soon
                    if not_after:
                        days_left = (not_after - now).days
                        if days_left < 0:
                            pass  # already expired above
                        elif days_left <= 7:
                            findings.append(make_finding(
                                id=f'acm_expiring_critical_{arn.split("/")[-1]}_{region}',
                                title=f'ACM certificate expiring in {days_left} days: {domain}',
                                title_tr=f'ACM sertifikası {days_left} gün içinde sona eriyor: {domain}',
                                description=f'ACM certificate for {domain} in {region} expires in {days_left} days.',
                                description_tr=f'{region} bölgesindeki {domain} için ACM sertifikası {days_left} gün içinde sona eriyor.',
                                severity='CRITICAL', status='FAIL',
                                service=SERVICE, resource_id=arn,
                                resource_type='AWS::CertificateManager::Certificate', region=region,
                                frameworks={
                                    'ISO27001': ['A.10.1.2'],
                                    'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
                                },
                                remediation=f'Renew ACM certificate {domain} immediately — {days_left} days remaining.',
                                remediation_tr=f'ACM sertifikası {domain}\'i hemen yenileyin — {days_left} gün kaldı.',
                                details={'days_left': days_left},
                            ))
                        elif days_left <= 30:
                            findings.append(make_finding(
                                id=f'acm_expiring_soon_{arn.split("/")[-1]}_{region}',
                                title=f'ACM certificate expiring in {days_left} days: {domain}',
                                title_tr=f'ACM sertifikası {days_left} gün içinde sona eriyor: {domain}',
                                description=f'ACM certificate for {domain} in {region} expires in {days_left} days. Renew proactively.',
                                description_tr=f'{region} bölgesindeki {domain} için ACM sertifikası {days_left} gün içinde sona eriyor. Proaktif olarak yenileyin.',
                                severity='HIGH', status='FAIL',
                                service=SERVICE, resource_id=arn,
                                resource_type='AWS::CertificateManager::Certificate', region=region,
                                frameworks={
                                    'ISO27001': ['A.10.1.2'],
                                    'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
                                },
                                remediation=f'Renew ACM certificate {domain} within the next {days_left} days.',
                                remediation_tr=f'ACM sertifikası {domain}\'i önümüzdeki {days_left} gün içinde yenileyin.',
                                details={'days_left': days_left},
                            ))
                        else:
                            findings.append(make_finding(
                                id=f'acm_valid_{arn.split("/")[-1]}_{region}',
                                title=f'ACM certificate valid: {domain}',
                                title_tr=f'ACM sertifikası geçerli: {domain}',
                                description=f'ACM certificate for {domain} in {region} is valid for {days_left} more days.',
                                description_tr=f'{region} bölgesindeki {domain} için ACM sertifikası {days_left} gün daha geçerli.',
                                severity='LOW', status='PASS',
                                service=SERVICE, resource_id=arn,
                                resource_type='AWS::CertificateManager::Certificate', region=region,
                                frameworks={'WAFR': {'pillar': 'Security', 'controls': ['SEC09']}},
                                remediation='No action required.',
                                remediation_tr='İşlem gerekmiyor.',
                                details={'days_left': days_left},
                            ))

                    # Failed validation
                    if status == 'FAILED':
                        findings.append(make_finding(
                            id=f'acm_failed_{arn.split("/")[-1]}_{region}',
                            title=f'ACM certificate validation failed: {domain}',
                            title_tr=f'ACM sertifika doğrulaması başarısız: {domain}',
                            description=f'ACM certificate for {domain} in {region} failed validation. It cannot be used.',
                            description_tr=f'{region} bölgesindeki {domain} için ACM sertifika doğrulaması başarısız. Kullanılamaz.',
                            severity='HIGH', status='FAIL',
                            service=SERVICE, resource_id=arn,
                            resource_type='AWS::CertificateManager::Certificate', region=region,
                            frameworks={'WAFR': {'pillar': 'Security', 'controls': ['SEC09']}},
                            remediation=f'Check DNS/email validation records for {domain} and reissue the certificate.',
                            remediation_tr=f'{domain} için DNS/e-posta doğrulama kayıtlarını kontrol edin ve sertifikayı yeniden yayınlayın.',
                        ))

        except Exception as exc:
            findings.append(not_available(f'acm_{region}', SERVICE, str(exc)))

    return findings
