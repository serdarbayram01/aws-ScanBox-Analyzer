"""SecOps — Secrets Manager Checks: rotation, unused, old secrets."""
from .base import make_finding, not_available
from datetime import datetime, timezone, timedelta

SERVICE = 'SecretsManager'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('sm_regions', SERVICE, str(exc))]

    now = datetime.now(timezone.utc)

    for region in regions:
        sm = session.client('secretsmanager', region_name=region)
        try:
            paginator = sm.get_paginator('list_secrets')
            for page in paginator.paginate():
                for secret in page.get('SecretList', []):
                    sid  = secret.get('ARN', secret.get('Name', 'unknown'))
                    name = secret.get('Name', sid)

                    # Rotation enabled?
                    rotation = secret.get('RotationEnabled', False)
                    findings.append(make_finding(
                        id=f'sm_rotation_{name}_{region}',
                        title=f'Secrets Manager rotation enabled: {name}',
                        title_tr=f'Secrets Manager rotasyon aktif: {name}',
                        description=f'Secret {name} in {region} should have automatic rotation enabled.',
                        description_tr=f'{region} bölgesindeki {name} gizli anahtarı için otomatik rotasyon etkinleştirilmelidir.',
                        severity='HIGH', status='PASS' if rotation else 'FAIL',
                        service=SERVICE, resource_id=sid,
                        resource_type='AWS::SecretsManager::Secret', region=region,
                        frameworks={
                            'CIS': ['1.14'], 'HIPAA': ['164.312(a)(2)(iv)'],
                            'ISO27001': ['A.9.4.3'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC07']},
                        },
                        remediation=f'Secrets Manager Console → {name} → Rotation → Enable automatic rotation.',
                        remediation_tr=f'Secrets Manager Konsol → {name} → Rotasyon → Otomatik rotasyonu etkinleştir.',
                    ))

                    # Last changed > 90 days?
                    last_changed = secret.get('LastChangedDate') or secret.get('CreatedDate')
                    if last_changed:
                        age_days = (now - last_changed).days
                        if age_days > 90 and not rotation:
                            findings.append(make_finding(
                                id=f'sm_stale_{name}_{region}',
                                title=f'Secrets Manager secret not rotated in 90+ days: {name}',
                                title_tr=f'Secrets Manager gizli anahtarı 90+ gündür rotasyona uğramadı: {name}',
                                description=f'Secret {name} in {region} has not been rotated in {age_days} days.',
                                description_tr=f'{region} bölgesindeki {name} gizli anahtarı {age_days} gündür rotasyona uğramadı.',
                                severity='MEDIUM', status='FAIL',
                                service=SERVICE, resource_id=sid,
                                resource_type='AWS::SecretsManager::Secret', region=region,
                                frameworks={
                                    'HIPAA': ['164.312(a)(2)(iv)'],
                                    'ISO27001': ['A.9.4.3'],
                                    'WAFR': {'pillar': 'Security', 'controls': ['SEC07']},
                                },
                                remediation='Rotate the secret manually or enable automatic rotation.',
                                remediation_tr='Gizli anahtarı manuel olarak döndürün veya otomatik rotasyonu etkinleştirin.',
                                details={'age_days': age_days},
                            ))

                    # Last accessed > 90 days (potentially orphaned)?
                    last_accessed = secret.get('LastAccessedDate')
                    if last_accessed and (now - last_accessed).days > 90:
                        findings.append(make_finding(
                            id=f'sm_unused_{name}_{region}',
                            title=f'Secrets Manager secret unused 90+ days: {name}',
                            title_tr=f'Secrets Manager gizli anahtarı 90+ gündür kullanılmıyor: {name}',
                            description=f'Secret {name} in {region} has not been accessed in {(now - last_accessed).days} days. Consider removing if unused.',
                            description_tr=f'{region} bölgesindeki {name} gizli anahtarı {(now - last_accessed).days} gündür erişilmedi. Kullanılmıyorsa kaldırmayı değerlendirin.',
                            severity='LOW', status='WARNING',
                            service=SERVICE, resource_id=sid,
                            resource_type='AWS::SecretsManager::Secret', region=region,
                            frameworks={'WAFR': {'pillar': 'Security', 'controls': ['SEC07']}},
                            remediation='Verify if the secret is still needed. Delete unused secrets to reduce attack surface.',
                            remediation_tr='Gizli anahtarın hâlâ gerekli olup olmadığını doğrulayın. Kullanılmayanları silerek saldırı yüzeyini azaltın.',
                            details={'days_since_access': (now - last_accessed).days},
                        ))

        except Exception as exc:
            findings.append(not_available(f'sm_{region}', SERVICE, str(exc)))

    return findings
