"""SecOps — Amazon Inspector V2 Checks: enabled per resource type
(EC2 / ECR / Lambda / LambdaCode), open critical/high CVE counts,
scan coverage. Uses the inspector2 API (legacy v1 'inspector' is not
covered — its EOL is 2024)."""

from .base import make_finding, not_available

SERVICE = 'Inspector'

# Resource types that Inspector V2 can scan
SCAN_TYPES = ('EC2', 'ECR', 'LAMBDA', 'LAMBDA_CODE')


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('inspector_regions', SERVICE, str(exc))]

    for region in regions:
        try:
            findings += _check_region(session, region)
        except Exception as exc:
            findings.append(not_available(f'inspector_{region}', SERVICE, str(exc)))
    return findings


def _check_region(session, region):
    findings = []
    try:
        ins = session.client('inspector2', region_name=region)
    except Exception:
        return findings  # Inspector V2 not available in this region

    # ----- Enabled-per-scan-type -----
    try:
        # Use current account ID
        sts = session.client('sts')
        acct = sts.get_caller_identity()['Account']
        status_resp = ins.batch_get_account_status(accountIds=[acct])
        accounts = status_resp.get('accounts', []) or []
        if not accounts:
            return findings
        acct_status = accounts[0]
        resource_state = acct_status.get('resourceState', {}) or {}
    except Exception as exc:
        if 'AccessDenied' in str(exc) or 'OptIn' in str(exc):
            return findings
        return findings

    # Per-scan-type enabled? Each scan type has its own `status`.
    enabled_count = 0
    for stype in ('ec2', 'ecr', 'lambda', 'lambdaCode'):
        cfg = resource_state.get(stype, {}) or {}
        st = cfg.get('status', 'DISABLED').upper()
        is_enabled = st == 'ENABLED'
        if is_enabled:
            enabled_count += 1
        findings.append(make_finding(
            id=f'inspector_{stype.lower()}_enabled_{region}',
            title=f'Amazon Inspector V2 ({stype.upper()}) enabled: {region}',
            title_tr=f'Amazon Inspector V2 ({stype.upper()}) etkin: {region}',
            description=(
                f'Inspector V2 {stype.upper()} scanning in {region} is {st}. '
                f'Inspector continuously scans for software vulnerabilities (CVEs) '
                f'and unintended network exposure.'
            ),
            description_tr=(
                f'{region} bölgesinde Inspector V2 {stype.upper()} taraması durumu: {st}. '
                f'Inspector, yazılım açıklarını (CVE) ve istenmeyen ağ açıklığını sürekli olarak tarar.'
            ),
            severity='MEDIUM', status='PASS' if is_enabled else 'WARNING',
            service=SERVICE, resource_id=region,
            resource_type='AWS::Inspector::Configuration', region=region,
            frameworks={
                'CIS':      ['4.6'],
                'HIPAA':    ['164.308(a)(1)(ii)(A)'],
                'ISO27001': ['A.12.6.1'],
                'SOC2':     ['CC7.1', 'CC3.2'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC11']},
            },
            remediation=(
                f'Inspector ({region}) → Account management → Enable for {stype.upper()}. '
                f'Free trial covers EC2; pricing is per-resource-scanned thereafter.'
            ),
            remediation_tr=(
                f'Inspector ({region}) → Hesap yönetimi → {stype.upper()} için etkinleştir. '
                f'Ücretsiz deneme EC2\'yi kapsar; sonrasında taranan kaynak başına ücretlendirilir.'
            ),
            details={'status': st},
        ))

    # If nothing enabled, skip findings-aggregation queries
    if enabled_count == 0:
        return findings

    # ----- Aggregate open finding counts by severity -----
    severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFORMATIONAL': 0}
    try:
        paginator = ins.get_paginator('list_findings')
        filter_criteria = {
            'findingStatus': [{'comparison': 'EQUALS', 'value': 'ACTIVE'}],
        }
        for page in paginator.paginate(filterCriteria=filter_criteria,
                                       PaginationConfig={'MaxItems': 500, 'PageSize': 100}):
            for f in page.get('findings', []) or []:
                sev = (f.get('severity') or '').upper()
                if sev in severity_counts:
                    severity_counts[sev] += 1
    except Exception:
        pass

    crit = severity_counts['CRITICAL']
    high = severity_counts['HIGH']
    med  = severity_counts['MEDIUM']

    if crit > 0:
        findings.append(make_finding(
            id=f'inspector_critical_findings_{region}',
            title=f'Amazon Inspector reports {crit} CRITICAL finding(s): {region}',
            title_tr=f'Amazon Inspector {crit} KRİTİK bulgu raporladı: {region}',
            description=(
                f'Inspector V2 has {crit} active CRITICAL finding(s) in {region}. '
                f'These typically represent unpatched CVEs with public exploits or '
                f'severe network exposure on running resources.'
            ),
            description_tr=(
                f'Inspector V2 {region} bölgesinde {crit} aktif KRİTİK bulgu raporluyor. '
                f'Bunlar genellikle herkese açık exploit\'i olan yamasız CVE\'leri veya '
                f'çalışan kaynaklarda ciddi ağ açığını temsil eder.'
            ),
            severity='CRITICAL', status='FAIL',
            service=SERVICE, resource_id=region,
            resource_type='AWS::Inspector::Finding', region=region,
            frameworks={
                'CIS':      ['4.6'],
                'HIPAA':    ['164.308(a)(1)(ii)(A)'],
                'ISO27001': ['A.12.6.1'],
                'SOC2':     ['CC7.1', 'CC3.2'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC11']},
            },
            remediation=(
                f'Inspector → Findings ({region}) → Filter Severity = Critical → '
                f'patch/remediate top items. Suppress (with rationale) only for false positives.'
            ),
            remediation_tr=(
                f'Inspector → Bulgular ({region}) → Filtre: Severity = Critical → '
                f'üst maddelerden başlayarak yamalayın. Yalnızca false-positive\'leri (gerekçe ile) bastırın.'
            ),
            details={'severity_counts': severity_counts},
        ))

    if high > 0:
        findings.append(make_finding(
            id=f'inspector_high_findings_{region}',
            title=f'Amazon Inspector reports {high} HIGH finding(s): {region}',
            title_tr=f'Amazon Inspector {high} YÜKSEK bulgu raporladı: {region}',
            description=(
                f'Inspector V2 has {high} active HIGH-severity finding(s) in {region}. '
                f'Triage within SLA; many will be CVE patches available via OS / image rebuild.'
            ),
            description_tr=(
                f'Inspector V2 {region} bölgesinde {high} aktif YÜKSEK önemde bulgu raporluyor. '
                f'SLA içinde triage edin; çoğu OS / image yeniden inşası ile yamalanabilir.'
            ),
            severity='HIGH', status='FAIL',
            service=SERVICE, resource_id=region,
            resource_type='AWS::Inspector::Finding', region=region,
            frameworks={
                'CIS':      ['4.6'],
                'ISO27001': ['A.12.6.1'],
                'SOC2':     ['CC7.1'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC11']},
            },
            remediation=f'Inspector → Findings ({region}) → Filter Severity = High → triage.',
            remediation_tr=f'Inspector → Bulgular ({region}) → Filtre: Severity = High → triage.',
            details={'severity_counts': severity_counts},
        ))

    # Informational rollup for medium / low — single finding, INFO status
    if med > 0:
        findings.append(make_finding(
            id=f'inspector_medium_findings_{region}',
            title=f'Amazon Inspector reports {med} MEDIUM finding(s): {region}',
            title_tr=f'Amazon Inspector {med} ORTA bulgu raporladı: {region}',
            description=f'Inspector V2 has {med} active MEDIUM finding(s) in {region}.',
            description_tr=f'Inspector V2 {region} bölgesinde {med} aktif ORTA bulgu raporluyor.',
            severity='MEDIUM', status='WARNING',
            service=SERVICE, resource_id=region,
            resource_type='AWS::Inspector::Finding', region=region,
            frameworks={
                'ISO27001': ['A.12.6.1'],
                'SOC2':     ['CC7.1'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC11']},
            },
            remediation=f'Inspector → Findings ({region}) → Filter Severity = Medium → triage.',
            remediation_tr=f'Inspector → Bulgular ({region}) → Filtre: Severity = Medium → triage.',
            details={'severity_counts': severity_counts},
        ))

    return findings
