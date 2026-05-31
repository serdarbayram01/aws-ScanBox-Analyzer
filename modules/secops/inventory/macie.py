"""SecOps — Amazon Macie 2 Checks: enabled per region, finding summary,
S3 bucket classification coverage, delegated admin (account-level)."""

from .base import make_finding, not_available

SERVICE = 'Macie'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('macie_regions', SERVICE, str(exc))]

    # Account-level: delegated admin (run once from us-east-1)
    try:
        findings += _check_delegated_admin(session)
    except Exception as exc:
        findings.append(not_available('macie_admin', SERVICE, str(exc)))

    for region in regions:
        try:
            findings += _check_region(session, region)
        except Exception as exc:
            findings.append(not_available(f'macie_{region}', SERVICE, str(exc)))
    return findings


def _check_delegated_admin(session):
    """Macie delegated administrator inside AWS Organizations."""
    findings = []
    try:
        macie = session.client('macie2', region_name='us-east-1')
        resp = macie.list_organization_admin_accounts()
        admins = [a for a in resp.get('adminAccounts', []) or []
                  if (a.get('status') or '').upper() == 'ENABLED']
    except Exception as exc:
        # AWSOrganizationsNotInUseException, AccessDenied — non-Organizations
        # account → skip silently; we don't want to penalise single-account setups.
        if 'OrganizationsNotInUse' in str(exc) or 'AccessDenied' in str(exc):
            return findings
        return findings

    findings.append(make_finding(
        id='macie_delegated_admin',
        title='Macie delegated administrator configured',
        title_tr='Macie yetkilendirilmiş yönetici yapılandırılmış',
        description=(
            f'AWS Organizations delegated admin for Macie is '
            f'{"set (" + admins[0].get("accountId","?") + ")" if admins else "not configured"}. '
            f'A delegated admin in the security-tooling account allows org-wide '
            f'Macie management and aggregated findings.'
        ),
        description_tr=(
            f'Macie için AWS Organizations yetkilendirilmiş yönetici '
            f'{"belirlenmiş (" + admins[0].get("accountId","?") + ")" if admins else "yapılandırılmamış"}. '
            f'Güvenlik-aracı hesabındaki bir yetkilendirilmiş yönetici, organizasyon genelinde '
            f'Macie yönetimini ve toplu bulguları sağlar.'
        ),
        severity='LOW', status='PASS' if admins else 'WARNING',
        service=SERVICE, resource_id='account',
        resource_type='AWS::Macie::OrganizationAdmin', region='global',
        frameworks={
            'ISO27001': ['A.18.2.2'],
            'SOC2':     ['CC1.3', 'CC4.1'],
            'WAFR':     {'pillar': 'Security', 'controls': ['SEC01']},
        },
        remediation=(
            'Organizations → Services → Macie → Choose delegated administrator. '
            'Run from the management account; security tooling account is the target.'
        ),
        remediation_tr=(
            'Organizations → Hizmetler → Macie → Yetkilendirilmiş yönetici seç. '
            'Yönetim hesabından çalıştırın; güvenlik aracı hesabı hedefiniz olmalı.'
        ),
        details={'admin_accounts': [a.get('accountId') for a in admins]},
    ))
    return findings


def _check_region(session, region):
    findings = []
    try:
        macie = session.client('macie2', region_name=region)
        session_info = macie.get_macie_session()
        status = (session_info.get('status') or '').upper()
        enabled = status == 'ENABLED'
    except Exception as exc:
        msg = str(exc)
        if 'AccessDenied' in msg:
            return findings
        # Macie not enabled — AWS returns AccessDeniedException OR a specific
        # "Macie is not enabled" error. Emit a single WARNING finding.
        findings.append(make_finding(
            id=f'macie_enabled_{region}',
            title=f'Amazon Macie enabled: {region}',
            title_tr=f'Amazon Macie etkin: {region}',
            description=(
                f'Macie is not enabled in {region}. Macie discovers sensitive data '
                f'(PII, financial, credentials) in S3 — required for GDPR / PCI / HIPAA '
                f'data-residency due-diligence.'
            ),
            description_tr=(
                f'{region} bölgesinde Macie etkin değil. Macie, S3\'te hassas veri (PII, '
                f'finansal, kimlik bilgileri) keşfeder — GDPR / PCI / HIPAA veri-ikametgâhı '
                f'incelemesi için gereklidir.'
            ),
            severity='LOW', status='WARNING',
            service=SERVICE, resource_id=region,
            resource_type='AWS::Macie::Session', region=region,
            frameworks={
                'HIPAA':    ['164.308(a)(1)(ii)(A)'],
                'ISO27001': ['A.18.1.4', 'A.8.2.1'],
                'SOC2':     ['CC3.2', 'C1.1'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC07']},
            },
            remediation=(
                f'Macie ({region}) → Get started → Enable Macie. '
                f'Cost: ~$1/GB scanned (first 30 days free).'
            ),
            remediation_tr=(
                f'Macie ({region}) → Get started → Macie\'yi etkinleştir. '
                f'Maliyet: taranan GB başına ~$1 (ilk 30 gün ücretsiz).'
            ),
        ))
        return findings

    findings.append(make_finding(
        id=f'macie_enabled_{region}',
        title=f'Amazon Macie enabled: {region}',
        title_tr=f'Amazon Macie etkin: {region}',
        description=f'Macie is {status} in {region}.',
        description_tr=f'{region} bölgesinde Macie durumu: {status}.',
        severity='LOW', status='PASS' if enabled else 'WARNING',
        service=SERVICE, resource_id=region,
        resource_type='AWS::Macie::Session', region=region,
        frameworks={
            'HIPAA':    ['164.308(a)(1)(ii)(A)'],
            'ISO27001': ['A.18.1.4', 'A.8.2.1'],
            'SOC2':     ['CC3.2', 'C1.1'],
            'WAFR':     {'pillar': 'Security', 'controls': ['SEC07']},
        },
        remediation='Macie session must remain ENABLED for continuous discovery.',
        remediation_tr='Sürekli keşif için Macie oturumu ENABLED kalmalı.',
    ))

    if not enabled:
        return findings

    # Active findings — sample severity rollup
    try:
        # list_findings supports filters but for a summary we pull totals via
        # get_finding_statistics which returns aggregated counts.
        stats_resp = macie.get_finding_statistics(
            findingCriteria={'criterion': {'archived': {'eq': ['false']}}},
            groupBy='severity.description',
        )
        counts = {row.get('groupKey'): int(row.get('count', 0))
                  for row in stats_resp.get('countsByGroup', []) or []}
    except Exception:
        counts = {}

    high = counts.get('High', 0)
    med  = counts.get('Medium', 0)
    low  = counts.get('Low', 0)
    total = high + med + low

    if high > 0:
        findings.append(make_finding(
            id=f'macie_high_findings_{region}',
            title=f'Macie {high} HIGH-severity sensitive-data finding(s): {region}',
            title_tr=f'Macie {high} YÜKSEK önemde hassas-veri bulgusu: {region}',
            description=(
                f'Macie reports {high} HIGH-severity finding(s) in {region}. '
                f'HIGH usually indicates exposed credentials, PII collections, '
                f'or financial data in unintended locations.'
            ),
            description_tr=(
                f'Macie {region} bölgesinde {high} YÜKSEK önemde bulgu raporluyor. '
                f'YÜKSEK genellikle istenmeyen yerlerde ifşa edilmiş kimlik bilgileri, '
                f'PII koleksiyonları veya finansal veri anlamına gelir.'
            ),
            severity='HIGH', status='FAIL',
            service=SERVICE, resource_id=region,
            resource_type='AWS::Macie::Finding', region=region,
            frameworks={
                'HIPAA':    ['164.402'],
                'ISO27001': ['A.18.1.4'],
                'SOC2':     ['C1.1', 'C1.2'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC07']},
            },
            remediation=(
                f'Macie ({region}) → Findings → Sort by Severity → '
                f'investigate and remediate (move data, restrict access, encrypt).'
            ),
            remediation_tr=(
                f'Macie ({region}) → Bulgular → Severity\'e göre sırala → '
                f'inceleyip düzeltin (veriyi taşıyın, erişimi kısıtlayın, şifreleyin).'
            ),
            details={'severity_counts': counts, 'total_active': total},
        ))
    elif total > 0:
        findings.append(make_finding(
            id=f'macie_active_findings_{region}',
            title=f'Macie {total} active finding(s): {region}',
            title_tr=f'Macie {total} aktif bulgu: {region}',
            description=f'Macie has {total} active finding(s) (no HIGH severity) in {region}.',
            description_tr=f'Macie {region} bölgesinde {total} aktif bulgu (YÜKSEK önem yok).',
            severity='LOW', status='WARNING',
            service=SERVICE, resource_id=region,
            resource_type='AWS::Macie::Finding', region=region,
            frameworks={
                'ISO27001': ['A.18.1.4'],
                'SOC2':     ['C1.1'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC07']},
            },
            remediation=f'Macie ({region}) → Findings → review and triage.',
            remediation_tr=f'Macie ({region}) → Bulgular → inceleyip triage edin.',
            details={'severity_counts': counts},
        ))

    return findings
