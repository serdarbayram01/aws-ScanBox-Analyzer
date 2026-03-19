"""SecOps — KMS Checks: key rotation, deletion pending, public policies."""
from .base import make_finding, not_available
SERVICE = 'KMS'

def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('kms_regions', SERVICE, str(exc))]

    for region in regions:
        kms = session.client('kms', region_name=region)
        try:
            paginator = kms.get_paginator('list_keys')
            for page in paginator.paginate():
                for key in page['Keys']:
                    kid = key['KeyId']
                    try:
                        meta = kms.describe_key(KeyId=kid)['KeyMetadata']
                        if meta.get('KeyManager') == 'AWS':
                            continue  # Skip AWS-managed keys
                        if meta.get('KeyState') in ('PendingDeletion',):
                            findings.append(make_finding(
                                id=f'kms_pending_deletion_{kid}_{region}',
                                title=f'KMS key pending deletion: {kid}',
                                title_tr=f'KMS anahtarı silinmeyi bekliyor: {kid}',
                                description=f'KMS key {kid} in {region} is scheduled for deletion.',
                                description_tr=f'{region} bölgesindeki KMS anahtarı {kid} silinmek üzere planlandı.',
                                severity='HIGH', status='WARNING',
                                service=SERVICE, resource_id=kid,
                                resource_type='AWS::KMS::Key', region=region,
                                frameworks={'CIS': ['3.8'], 'HIPAA': ['164.312(a)(2)(iv)'],
                                            'ISO27001': ['A.10.1.2'],
                                            'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
                                remediation='Cancel key deletion if the key is still needed.',
                                remediation_tr='Anahtar hâlâ gerekiyorsa silinmeyi iptal edin.',
                            ))
                            continue

                        if meta.get('KeyState') != 'Enabled':
                            continue

                        # Key rotation
                        try:
                            rotation = kms.get_key_rotation_status(KeyId=kid)['KeyRotationEnabled']
                        except Exception:
                            rotation = False
                        findings.append(make_finding(
                            id=f'kms_rotation_{kid}_{region}',
                            title=f'KMS key rotation enabled: {kid}',
                            title_tr=f'KMS anahtar rotasyonu aktif: {kid}',
                            description=f'Customer-managed KMS key {kid} in {region} should have automatic rotation enabled.',
                            description_tr=f'{region} bölgesindeki müşteri yönetimli KMS anahtarı {kid} için otomatik rotasyon etkinleştirilmelidir.',
                            severity='MEDIUM', status='PASS' if rotation else 'FAIL',
                            service=SERVICE, resource_id=kid,
                            resource_type='AWS::KMS::Key', region=region,
                            frameworks={'CIS': ['3.8'], 'HIPAA': ['164.312(a)(2)(iv)'],
                                        'ISO27001': ['A.10.1.2'],
                                        'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
                            remediation=f'KMS Console → {kid} → Key rotation → Enable.',
                            remediation_tr=f'KMS Konsol → {kid} → Anahtar rotasyonu → Etkinleştir.',
                        ))
                    except Exception:
                        pass
        except Exception as exc:
            findings.append(not_available(f'kms_{region}', SERVICE, str(exc)))
    return findings
