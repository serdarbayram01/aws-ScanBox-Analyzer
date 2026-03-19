"""SecOps — Route 53 Checks: DNSSEC, public zones, query logging."""
from .base import make_finding, not_available

SERVICE = 'Route53'


def run_checks(session, exclude_defaults=False, regions=None):
    """Route 53 is a global service — called once."""
    findings = []
    r53 = session.client('route53', region_name='us-east-1')

    try:
        paginator = r53.get_paginator('list_hosted_zones')
        for page in paginator.paginate():
            for zone in page.get('HostedZones', []):
                zone_id    = zone['Id'].split('/')[-1]
                zone_name  = zone['Name'].rstrip('.')
                is_private = zone['Config'].get('PrivateZone', False)
                record_count = zone.get('ResourceRecordSetCount', 0)

                # --- DNSSEC (public zones only) ---
                if not is_private:
                    try:
                        dnssec = r53.get_dnssec(HostedZoneId=zone_id)
                        status     = dnssec.get('Status', {}).get('ServedSigning', 'NOT_SIGNING')
                        dnssec_on  = status == 'SIGNING'
                    except Exception:
                        dnssec_on = False

                    findings.append(make_finding(
                        id=f'route53_dnssec_{zone_id}',
                        title=f'Route 53 DNSSEC enabled: {zone_name}',
                        title_tr=f'Route 53 DNSSEC aktif: {zone_name}',
                        description=f'Public hosted zone {zone_name} should have DNSSEC signing enabled to prevent DNS spoofing attacks.',
                        description_tr=f'Genel barındırılan bölge {zone_name}, DNS yanıltma saldırılarını önlemek için DNSSEC imzalama etkinleştirilmelidir.',
                        severity='MEDIUM', status='PASS' if dnssec_on else 'FAIL',
                        service=SERVICE, resource_id=zone_id,
                        resource_type='AWS::Route53::HostedZone', region='global',
                        frameworks={
                            'CIS': ['3.12'], 'ISO27001': ['A.13.1.2'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC05']},
                        },
                        remediation=f'Route 53 Console → Hosted zones → {zone_name} → DNSSEC signing → Enable DNSSEC signing.',
                        remediation_tr=f'Route 53 Konsol → Barındırılan bölgeler → {zone_name} → DNSSEC imzalama → DNSSEC imzalamayı etkinleştir.',
                    ))

                # --- Query logging (public zones) ---
                if not is_private:
                    try:
                        qlc = r53.list_query_logging_configs(HostedZoneId=zone_id)
                        has_query_logging = len(qlc.get('QueryLoggingConfigs', [])) > 0
                    except Exception:
                        has_query_logging = False

                    findings.append(make_finding(
                        id=f'route53_query_logging_{zone_id}',
                        title=f'Route 53 query logging enabled: {zone_name}',
                        title_tr=f'Route 53 sorgu günlüğü aktif: {zone_name}',
                        description=f'Public hosted zone {zone_name} should have DNS query logging enabled for security monitoring.',
                        description_tr=f'Genel barındırılan bölge {zone_name}, güvenlik izleme için DNS sorgu günlüğü etkinleştirilmelidir.',
                        severity='LOW', status='PASS' if has_query_logging else 'FAIL',
                        service=SERVICE, resource_id=zone_id,
                        resource_type='AWS::Route53::HostedZone', region='global',
                        frameworks={
                            'HIPAA': ['164.312(b)'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']},
                        },
                        remediation=f'Route 53 Console → Hosted zones → {zone_name} → Configure query logging → Select CloudWatch Logs log group.',
                        remediation_tr=f'Route 53 Konsol → Barındırılan bölgeler → {zone_name} → Sorgu günlüğünü yapılandır → CloudWatch Logs günlük grubu seç.',
                    ))

    except Exception as exc:
        findings.append(not_available('route53_zones', SERVICE, str(exc)))

    return findings
