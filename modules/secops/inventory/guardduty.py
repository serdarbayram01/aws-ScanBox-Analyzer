"""SecOps — GuardDuty Checks: enabled per region, active HIGH/CRITICAL findings."""
from .base import make_finding, not_available
SERVICE = 'GuardDuty'

def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('guardduty_regions', SERVICE, str(exc))]

    for region in regions:
        gd = session.client('guardduty', region_name=region)
        try:
            detectors = gd.list_detectors()['DetectorIds']
            if not detectors:
                findings.append(make_finding(
                    id=f'guardduty_enabled_{region}',
                    title=f'GuardDuty enabled: {region}',
                    title_tr=f'GuardDuty aktif: {region}',
                    description=f'GuardDuty is not enabled in {region}.',
                    description_tr=f'{region} bölgesinde GuardDuty etkin değil.',
                    severity='HIGH', status='FAIL',
                    service=SERVICE, resource_id=region,
                    resource_type='AWS::GuardDuty::Detector', region=region,
                    frameworks={'CIS': ['3.8'], 'HIPAA': ['164.312(b)'],
                                'ISO27001': ['A.16.1.2'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                    remediation=f'GuardDuty Console ({region}) → Enable GuardDuty.',
                    remediation_tr=f'GuardDuty Konsol ({region}) → GuardDuty\'ı etkinleştir.',
                ))
                continue

            did = detectors[0]
            det = gd.get_detector(DetectorId=did)
            enabled = det.get('Status') == 'ENABLED'
            findings.append(make_finding(
                id=f'guardduty_enabled_{region}',
                title=f'GuardDuty enabled: {region}',
                title_tr=f'GuardDuty aktif: {region}',
                description=f'GuardDuty detector {did} in {region}.',
                description_tr=f'{region} bölgesindeki GuardDuty detector {did}.',
                severity='HIGH', status='PASS' if enabled else 'FAIL',
                service=SERVICE, resource_id=did,
                resource_type='AWS::GuardDuty::Detector', region=region,
                frameworks={'CIS': ['3.8'], 'ISO27001': ['A.16.1.2'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                remediation='Enable GuardDuty in all regions.',
                remediation_tr='Tüm bölgelerde GuardDuty\'ı etkinleştirin.',
            ))

            if not enabled:
                continue

            # Active HIGH/CRITICAL findings
            try:
                fids = gd.list_findings(
                    DetectorId=did,
                    FindingCriteria={'Criterion': {
                        'severity': {'Gte': 7},
                        'service.archived': {'Eq': ['false']},
                    }}
                ).get('FindingIds', [])
                if fids:
                    gd_findings = gd.get_findings(DetectorId=did, FindingIds=fids[:50])['Findings']
                    for gdf in gd_findings:
                        sev_num = gdf.get('Severity', 0)
                        sev_str = 'CRITICAL' if sev_num >= 9 else 'HIGH'
                        findings.append(make_finding(
                            id=f'guardduty_finding_{gdf["Id"]}',
                            title=f'GuardDuty finding: {gdf.get("Title", "Unknown")}',
                            title_tr=f'GuardDuty bulgusu: {gdf.get("Title", "Bilinmiyor")}',
                            description=gdf.get('Description', ''),
                            description_tr=gdf.get('Description', ''),
                            severity=sev_str, status='FAIL',
                            service=SERVICE, resource_id=gdf['Id'],
                            resource_type='AWS::GuardDuty::Finding', region=region,
                            frameworks={'HIPAA': ['164.312(b)'], 'ISO27001': ['A.16.1.5'],
                                        'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                            remediation='Investigate and remediate the GuardDuty finding.',
                            remediation_tr='GuardDuty bulgusunu araştırın ve düzeltin.',
                            details={'type': gdf.get('Type'), 'severity': sev_num},
                        ))
            except Exception:
                pass
        except Exception as exc:
            findings.append(not_available(f'guardduty_{region}', SERVICE, str(exc)))
    return findings
