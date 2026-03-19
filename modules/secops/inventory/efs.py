"""SecOps — EFS Checks: encryption at rest, backup policy, access points."""
from .base import make_finding, not_available

SERVICE = 'EFS'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('efs_regions', SERVICE, str(exc))]

    for region in regions:
        efs = session.client('efs', region_name=region)
        try:
            paginator = efs.get_paginator('describe_file_systems')
            for page in paginator.paginate():
                for fs in page.get('FileSystems', []):
                    fs_id   = fs['FileSystemId']
                    fs_arn  = fs.get('FileSystemArn', fs_id)
                    name    = fs.get('Name') or fs_id
                    encrypted = fs.get('Encrypted', False)
                    kms_key   = fs.get('KmsKeyId', '')

                    # Encryption at rest
                    findings.append(make_finding(
                        id=f'efs_encryption_{fs_id}_{region}',
                        title=f'EFS file system encrypted at rest: {name}',
                        title_tr=f'EFS dosya sistemi bekleme sırasında şifreli: {name}',
                        description=f'EFS file system {name} ({fs_id}) in {region} should be encrypted at rest using KMS.',
                        description_tr=f'{region} bölgesindeki EFS dosya sistemi {name} ({fs_id}), KMS kullanarak bekleme sırasında şifrelenmelidir.',
                        severity='HIGH', status='PASS' if encrypted else 'FAIL',
                        service=SERVICE, resource_id=fs_arn,
                        resource_type='AWS::EFS::FileSystem', region=region,
                        frameworks={
                            'CIS': ['2.4.1'], 'HIPAA': ['164.312(a)(2)(iv)'],
                            'ISO27001': ['A.10.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC08']},
                        },
                        remediation=f'EFS encryption can only be enabled at creation time. Create a new encrypted EFS file system and migrate data from {fs_id}.',
                        remediation_tr=f'EFS şifrelemesi yalnızca oluşturma sırasında etkinleştirilebilir. Yeni şifreli bir EFS dosya sistemi oluşturun ve verileri {fs_id} den taşıyın.',
                        details={'encrypted': encrypted, 'kms_key': kms_key or 'none'},
                    ))

                    # CMK vs AWS-managed key
                    if encrypted and not kms_key:
                        findings.append(make_finding(
                            id=f'efs_cmk_{fs_id}_{region}',
                            title=f'EFS file system uses AWS-managed key (not CMK): {name}',
                            title_tr=f'EFS dosya sistemi AWS tarafından yönetilen anahtar kullanıyor (CMK değil): {name}',
                            description=f'EFS file system {name} is encrypted but uses the AWS-managed default key, not a customer-managed KMS key (CMK).',
                            description_tr=f'EFS dosya sistemi {name} şifreli ancak müşteri tarafından yönetilen KMS anahtarı (CMK) değil, AWS tarafından yönetilen varsayılan anahtarı kullanıyor.',
                            severity='LOW', status='WARNING',
                            service=SERVICE, resource_id=fs_arn,
                            resource_type='AWS::EFS::FileSystem', region=region,
                            frameworks={
                                'ISO27001': ['A.10.1.2'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC08']},
                            },
                            remediation='Create a new EFS file system specifying a customer-managed KMS key for finer access control over encryption.',
                            remediation_tr='Şifreleme üzerinde daha iyi erişim kontrolü için müşteri tarafından yönetilen KMS anahtarı belirterek yeni bir EFS dosya sistemi oluşturun.',
                        ))

                    # Backup policy
                    try:
                        bp = efs.describe_backup_policy(FileSystemId=fs_id)
                        backup_status = bp.get('BackupPolicy', {}).get('Status', 'DISABLED')
                        has_backup = backup_status == 'ENABLED'
                    except Exception:
                        has_backup = False

                    findings.append(make_finding(
                        id=f'efs_backup_{fs_id}_{region}',
                        title=f'EFS file system has backup policy enabled: {name}',
                        title_tr=f'EFS dosya sisteminde yedekleme politikası etkin: {name}',
                        description=f'EFS file system {name} ({fs_id}) in {region} should have automatic backup enabled.',
                        description_tr=f'{region} bölgesindeki EFS dosya sistemi {name} ({fs_id}), otomatik yedekleme etkinleştirilmelidir.',
                        severity='MEDIUM', status='PASS' if has_backup else 'FAIL',
                        service=SERVICE, resource_id=fs_arn,
                        resource_type='AWS::EFS::FileSystem', region=region,
                        frameworks={
                            'HIPAA': ['164.312(c)(1)'],
                            'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']},
                        },
                        remediation=f'EFS Console → File systems → {fs_id} → Actions → Enable automatic backups.',
                        remediation_tr=f'EFS Konsol → Dosya sistemleri → {fs_id} → Eylemler → Otomatik yedeklemeyi etkinleştir.',
                    ))

        except Exception as exc:
            findings.append(not_available(f'efs_{region}', SERVICE, str(exc)))

    return findings
