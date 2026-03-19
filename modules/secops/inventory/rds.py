"""SecOps — RDS Checks: public access, encryption, backups, multi-AZ, deletion protection."""
from .base import make_finding, not_available
SERVICE = 'RDS'

def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('rds_regions', SERVICE, str(exc))]

    for region in regions:
        rds = session.client('rds', region_name=region)
        try:
            paginator = rds.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for db in page['DBInstances']:
                    findings += _check_db(db, region)
        except Exception as exc:
            findings.append(not_available(f'rds_{region}', SERVICE, str(exc)))
    return findings


def _check_db(db, region):
    findings = []
    dbid = db['DBInstanceIdentifier']

    checks = [
        ('rds_public',     'RDS not publicly accessible',    'RDS genel erişilebilir değil',
         not db.get('PubliclyAccessible', False), 'HIGH',
         {'CIS': ['2.3.3'], 'ISO27001': ['A.13.1.1'],
          'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
         'Modify DB → Network & Security → Uncheck Publicly accessible.',
         'DB\'yi Düzenle → Ağ ve Güvenlik → Genel erişilebilir işaretini kaldır.'),

        ('rds_encryption', 'RDS storage encrypted',         'RDS depolama şifrelenmiş',
         db.get('StorageEncrypted', False), 'HIGH',
         {'CIS': ['2.3.1'], 'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.10.1.1'],
          'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
         'Enable storage encryption when creating RDS (cannot be changed after creation).',
         'RDS oluştururken depolama şifrelemesini etkinleştirin (oluşturulduktan sonra değiştirilemez).'),

        ('rds_backups',    'RDS automated backups enabled', 'RDS otomatik yedeklemeler aktif',
         db.get('BackupRetentionPeriod', 0) > 0, 'MEDIUM',
         {'CIS': ['2.3.2'], 'ISO27001': ['A.12.3.1'],
          'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']}},
         f'Modify {dbid} → Backup retention period → Set to ≥ 7 days.',
         f'{dbid} DB\'yi Düzenle → Yedekleme saklama süresi → ≥ 7 gün olarak ayarlayın.'),

        ('rds_multiaz',    'RDS Multi-AZ enabled',          'RDS Multi-AZ aktif',
         db.get('MultiAZ', False), 'MEDIUM',
         {'ISO27001': ['A.17.2.1'], 'WAFR': {'pillar': 'Reliability', 'controls': ['REL02']}},
         f'Modify {dbid} → Availability & Durability → Enable Multi-AZ.',
         f'{dbid} DB\'yi Düzenle → Kullanılabilirlik → Multi-AZ\'ı etkinleştir.'),

        ('rds_deletion',   'RDS deletion protection enabled', 'RDS silme koruması aktif',
         db.get('DeletionProtection', False), 'MEDIUM',
         {'ISO27001': ['A.12.3.1'], 'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']}},
         f'Modify {dbid} → Deletion protection → Enable.',
         f'{dbid} DB\'yi Düzenle → Silme koruması → Etkinleştir.'),
    ]

    for check_id, title, title_tr, passed, sev, fw, rem, rem_tr in checks:
        findings.append(make_finding(
            id=f'{check_id}_{dbid}_{region}',
            title=f'{title}: {dbid}',
            title_tr=f'{title_tr}: {dbid}',
            description=f'RDS instance {dbid} in {region}: {title.lower()}.',
            description_tr=f'{region} bölgesindeki RDS instance {dbid}: {title_tr.lower()}.',
            severity=sev, status='PASS' if passed else 'FAIL',
            service=SERVICE, resource_id=dbid,
            resource_type='AWS::RDS::DBInstance', region=region,
            frameworks=fw, remediation=rem, remediation_tr=rem_tr,
        ))

    # --- IAM Database Authentication ---
    iam_auth = db.get('IAMDatabaseAuthenticationEnabled', False)
    findings.append(make_finding(
        id=f'rds_iam_auth_{dbid}_{region}',
        title=f'RDS IAM database authentication enabled: {dbid}',
        title_tr=f'RDS IAM veritabanı kimlik doğrulaması aktif: {dbid}',
        description=f'RDS instance {dbid} in {region} should use IAM database authentication for enhanced access control.',
        description_tr=f'{region} bölgesindeki RDS instance {dbid}, gelişmiş erişim kontrolü için IAM veritabanı kimlik doğrulaması kullanmalıdır.',
        severity='MEDIUM', status='PASS' if iam_auth else 'WARNING',
        service=SERVICE, resource_id=dbid,
        resource_type='AWS::RDS::DBInstance', region=region,
        frameworks={'CIS': ['2.3.3'], 'HIPAA': ['164.312(d)'], 'ISO27001': ['A.9.2.1'],
                    'WAFR': {'pillar': 'Security', 'controls': ['SEC03']}},
        remediation=f'Modify {dbid} → Enable IAM DB authentication for token-based access instead of passwords.',
        remediation_tr=f'{dbid} DB\'yi Düzenle → Parola yerine token tabanlı erişim için IAM DB kimlik doğrulamasını etkinleştirin.',
    ))

    # --- Backup Retention >= 7 days ---
    retention = db.get('BackupRetentionPeriod', 0)
    retention_ok = retention >= 7
    findings.append(make_finding(
        id=f'rds_backup_retention_{dbid}_{region}',
        title=f'RDS backup retention >= 7 days: {dbid}',
        title_tr=f'RDS yedekleme saklama >= 7 gün: {dbid}',
        description=f'RDS instance {dbid} in {region} has backup retention of {retention} days. A minimum of 7 days is recommended.',
        description_tr=f'{region} bölgesindeki RDS instance {dbid}, {retention} günlük yedekleme saklama süresine sahip. En az 7 gün önerilir.',
        severity='MEDIUM', status='PASS' if retention_ok else 'WARNING',
        service=SERVICE, resource_id=dbid,
        resource_type='AWS::RDS::DBInstance', region=region,
        frameworks={'CIS': ['2.3.2'], 'HIPAA': ['164.308(a)(7)(ii)(A)'], 'ISO27001': ['A.12.3.1'],
                    'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']}},
        remediation=f'Modify {dbid} → Backup retention period → Set to >= 7 days.',
        remediation_tr=f'{dbid} DB\'yi Düzenle → Yedekleme saklama süresi → >= 7 gün olarak ayarlayın.',
        details={'backup_retention_period': retention},
    ))

    # --- Auto Minor Version Upgrade ---
    auto_upgrade = db.get('AutoMinorVersionUpgrade', False)
    findings.append(make_finding(
        id=f'rds_auto_minor_upgrade_{dbid}_{region}',
        title=f'RDS auto minor version upgrade enabled: {dbid}',
        title_tr=f'RDS otomatik küçük sürüm yükseltmesi aktif: {dbid}',
        description=f'RDS instance {dbid} in {region} should have auto minor version upgrade enabled for security patches.',
        description_tr=f'{region} bölgesindeki RDS instance {dbid}, güvenlik yamaları için otomatik küçük sürüm yükseltmesi etkinleştirilmelidir.',
        severity='LOW', status='PASS' if auto_upgrade else 'WARNING',
        service=SERVICE, resource_id=dbid,
        resource_type='AWS::RDS::DBInstance', region=region,
        frameworks={'ISO27001': ['A.12.6.1'],
                    'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
        remediation=f'Modify {dbid} → Maintenance → Enable auto minor version upgrade.',
        remediation_tr=f'{dbid} DB\'yi Düzenle → Bakım → Otomatik küçük sürüm yükseltmesini etkinleştirin.',
    ))

    return findings
