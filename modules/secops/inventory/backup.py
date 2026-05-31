"""SecOps — AWS Backup Checks: vault lock, vault KMS encryption, backup plan
retention, cross-region copy, recovery point encryption.

Run per-region. AWS Backup is regional; an Organisation may also enforce
cross-account backup policies via Backup Policies (not covered here)."""

from .base import make_finding, not_available

SERVICE = 'Backup'

# Minimum retention recommended for compliance (HIPAA / SOC2 audit retention).
MIN_RETENTION_DAYS = 30


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('backup_regions', SERVICE, str(exc))]

    for region in regions:
        try:
            findings += _check_region(session, region)
        except Exception as exc:
            findings.append(not_available(f'backup_{region}', SERVICE, str(exc)))
    return findings


def _check_region(session, region):
    findings = []
    backup = session.client('backup', region_name=region)

    # ----- Backup Vaults -----
    try:
        vaults = []
        paginator = backup.get_paginator('list_backup_vaults')
        for page in paginator.paginate():
            vaults.extend(page.get('BackupVaultList', []) or [])
    except Exception as exc:
        # Either Backup not used in this region or permission missing — silent.
        if 'AccessDenied' in str(exc) or 'OptIn' in str(exc):
            return findings
        return findings  # other errors swallowed per region

    for v in vaults:
        vault_name = v.get('BackupVaultName', '')
        vault_arn  = v.get('BackupVaultArn', vault_name)
        kms_key    = v.get('EncryptionKeyArn', '')

        # 1) Vault KMS encryption
        findings.append(make_finding(
            id=f'backup_vault_encryption_{vault_name}_{region}',
            title=f'AWS Backup vault encrypted with KMS: {vault_name}',
            title_tr=f'AWS Backup kasası KMS ile şifreli: {vault_name}',
            description=(
                f'Backup vault {vault_name} in {region} '
                f'{"uses KMS encryption (" + kms_key.split("/")[-1] + ")" if kms_key else "has no KMS key configured"}. '
                f'Vault encryption protects recovery point data at rest.'
            ),
            description_tr=(
                f'{region} bölgesindeki Backup kasası {vault_name}, '
                f'{"KMS şifrelemesi kullanıyor (" + kms_key.split("/")[-1] + ")" if kms_key else "KMS anahtarı yapılandırılmamış"}. '
                f'Kasa şifrelemesi, kurtarma noktası verilerini beklemede korur.'
            ),
            severity='HIGH', status='PASS' if kms_key else 'FAIL',
            service=SERVICE, resource_id=vault_arn,
            resource_type='AWS::Backup::BackupVault', region=region,
            frameworks={
                'CIS':      ['2.3.1'],
                'HIPAA':    ['164.312(a)(2)(iv)'],
                'ISO27001': ['A.10.1.1'],
                'SOC2':     ['CC6.7', 'C1.2'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC08']},
            },
            remediation=(
                f'Backup → Vaults → {vault_name} → cannot change post-creation. '
                f'Create a new vault with a customer-managed KMS key and migrate plans.'
            ),
            remediation_tr=(
                f'Backup → Kasalar → {vault_name} → oluşturma sonrası değiştirilemez. '
                f'Müşteri yönetimli KMS anahtarı ile yeni bir kasa oluşturun ve planları taşıyın.'
            ),
            details={'kms_key_arn': kms_key},
        ))

        # 2) Vault Lock — immutable / WORM backups
        try:
            lock = backup.describe_backup_vault(BackupVaultName=vault_name)
            lock_state = lock.get('LockDate') is not None
            min_retention = lock.get('MinRetentionDays')
            max_retention = lock.get('MaxRetentionDays')
        except Exception:
            lock_state = False
            min_retention = max_retention = None

        findings.append(make_finding(
            id=f'backup_vault_lock_{vault_name}_{region}',
            title=f'AWS Backup Vault Lock configured: {vault_name}',
            title_tr=f'AWS Backup Vault Lock yapılandırılmış: {vault_name}',
            description=(
                f'Backup vault {vault_name} Vault Lock is '
                f'{"in effect (immutable, WORM)" if lock_state else "not configured"}. '
                f'Vault Lock prevents deletion/modification of recovery points — '
                f'mandatory for HIPAA, SEC 17a-4(f), and ransomware resilience.'
            ),
            description_tr=(
                f'Backup kasası {vault_name} Vault Lock '
                f'{"etkin (değiştirilemez, WORM)" if lock_state else "yapılandırılmamış"}. '
                f'Vault Lock, kurtarma noktalarının silinmesini/değiştirilmesini önler — '
                f'HIPAA, SEC 17a-4(f) ve fidye yazılımı dayanıklılığı için zorunlu.'
            ),
            severity='MEDIUM', status='PASS' if lock_state else 'WARNING',
            service=SERVICE, resource_id=vault_arn,
            resource_type='AWS::Backup::BackupVault', region=region,
            frameworks={
                'HIPAA':    ['164.312(c)(1)'],
                'ISO27001': ['A.12.3.1'],
                'SOC2':     ['PI1.4', 'PI1.5', 'CC6.5'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC08']},
            },
            remediation=(
                f'aws backup put-backup-vault-lock-configuration --backup-vault-name {vault_name} '
                f'--min-retention-days 30 --max-retention-days 3650 [--changeable-for-days 3]. '
                f'NOTE: once the cooling-off period expires the lock is irreversible.'
            ),
            remediation_tr=(
                f'aws backup put-backup-vault-lock-configuration --backup-vault-name {vault_name} '
                f'--min-retention-days 30 --max-retention-days 3650 [--changeable-for-days 3]. '
                f'NOT: bekleme süresi dolduktan sonra kilit geri alınamaz.'
            ),
            details={
                'lock_active': lock_state,
                'min_retention_days': min_retention,
                'max_retention_days': max_retention,
            },
        ))

    # ----- Backup Plans -----
    try:
        plans = []
        paginator = backup.get_paginator('list_backup_plans')
        for page in paginator.paginate():
            plans.extend(page.get('BackupPlansList', []) or [])
    except Exception:
        plans = []

    # Account-level: at least one plan exists?
    findings.append(make_finding(
        id=f'backup_plan_exists_{region}',
        title=f'AWS Backup plan exists: {region}',
        title_tr=f'AWS Backup planı mevcut: {region}',
        description=(
            f'Region {region} has {len(plans)} active backup plan(s). '
            f'Without backup plans, recovery point creation is manual/best-effort.'
        ),
        description_tr=(
            f'{region} bölgesinde {len(plans)} aktif backup planı var. '
            f'Backup planı olmadan kurtarma noktası oluşturma manuel/en-iyi-çabaya kalır.'
        ),
        severity='LOW', status='PASS' if plans else 'WARNING',
        service=SERVICE, resource_id=region,
        resource_type='AWS::Backup::BackupPlan', region=region,
        frameworks={
            'HIPAA':    ['164.308(a)(7)(ii)(A)'],
            'ISO27001': ['A.12.3.1', 'A.17.1.2'],
            'SOC2':     ['A1.2', 'A1.3'],
            'WAFR':     {'pillar': 'Reliability', 'controls': ['REL09']},
        },
        remediation=(
            f'Backup ({region}) → Backup plans → Create plan. Use a managed template '
            f'(daily-35day, monthly-1year) or build a custom rule set per resource tier.'
        ),
        remediation_tr=(
            f'Backup ({region}) → Backup planları → Plan oluştur. Yönetilen şablon kullanın '
            f'(günlük-35gün, aylık-1yıl) veya kaynak katmanına göre özel kural seti oluşturun.'
        ),
        details={'plan_count': len(plans)},
    ))

    # Per-plan: retention + cross-region copy
    for p in plans:
        plan_id   = p.get('BackupPlanId', '')
        plan_name = p.get('BackupPlanName', plan_id)
        plan_arn  = p.get('BackupPlanArn', plan_id)
        try:
            plan_resp = backup.get_backup_plan(BackupPlanId=plan_id)
            rules = plan_resp.get('BackupPlan', {}).get('Rules', []) or []
        except Exception:
            rules = []

        # Worst-case retention (we want the *minimum* across rules to be >= MIN_RETENTION_DAYS)
        retentions = []
        has_cross_region = False
        for r in rules:
            lifecycle = r.get('Lifecycle') or {}
            days = lifecycle.get('DeleteAfterDays')
            if days is not None:
                retentions.append(days)
            # Cross-region copy actions
            for copy_action in r.get('CopyActions', []) or []:
                dest = copy_action.get('DestinationBackupVaultArn', '')
                # ARN format: arn:aws:backup:<region>:<acct>:backup-vault:<name>
                if dest and len(dest.split(':')) > 3 and dest.split(':')[3] != region:
                    has_cross_region = True

        min_retention = min(retentions) if retentions else 0
        sufficient = bool(rules) and (not retentions or min_retention >= MIN_RETENTION_DAYS)

        findings.append(make_finding(
            id=f'backup_plan_retention_{plan_id}_{region}',
            title=f'AWS Backup plan retention >= {MIN_RETENTION_DAYS}d: {plan_name}',
            title_tr=f'AWS Backup planı saklama >= {MIN_RETENTION_DAYS} gün: {plan_name}',
            description=(
                f'Plan {plan_name} in {region} has '
                f'{len(rules)} rule(s); minimum DeleteAfterDays = {min_retention or "∞"}. '
                f'Compliance baselines (HIPAA, SOC2) typically require >= 30 days.'
            ),
            description_tr=(
                f'{region} bölgesindeki plan {plan_name}, '
                f'{len(rules)} kurala sahip; minimum DeleteAfterDays = {min_retention or "∞"}. '
                f'Uyumluluk taban çizgileri (HIPAA, SOC2) genellikle >= 30 gün gerektirir.'
            ),
            severity='MEDIUM', status='PASS' if sufficient else 'WARNING',
            service=SERVICE, resource_id=plan_arn,
            resource_type='AWS::Backup::BackupPlan', region=region,
            frameworks={
                'HIPAA':    ['164.308(a)(7)(ii)(A)'],
                'ISO27001': ['A.12.3.1'],
                'SOC2':     ['A1.2'],
                'WAFR':     {'pillar': 'Reliability', 'controls': ['REL09']},
            },
            remediation=(
                f'Backup → Plans → {plan_name} → Edit each rule → Lifecycle → '
                f'set "Delete backups after" to at least 30 days.'
            ),
            remediation_tr=(
                f'Backup → Planlar → {plan_name} → Her kuralı düzenle → Yaşam döngüsü → '
                f'"Yedekleri sil" değerini en az 30 gün olarak ayarlayın.'
            ),
            details={'rule_count': len(rules), 'min_retention_days': min_retention},
        ))

        findings.append(make_finding(
            id=f'backup_plan_cross_region_{plan_id}_{region}',
            title=f'AWS Backup plan has cross-region copy: {plan_name}',
            title_tr=f'AWS Backup planında bölgeler arası kopyalama var: {plan_name}',
            description=(
                f'Plan {plan_name} in {region} '
                f'{"copies to" if has_cross_region else "does not copy to"} a different region. '
                f'Cross-region copies are the foundation of a regional-failure DR strategy.'
            ),
            description_tr=(
                f'{region} bölgesindeki plan {plan_name}, '
                f'{"farklı bir bölgeye kopyalıyor" if has_cross_region else "farklı bir bölgeye kopyalamıyor"}. '
                f'Bölgeler arası kopyalar, bölgesel-arıza DR stratejisinin temelidir.'
            ),
            severity='LOW', status='PASS' if has_cross_region else 'WARNING',
            service=SERVICE, resource_id=plan_arn,
            resource_type='AWS::Backup::BackupPlan', region=region,
            frameworks={
                'ISO27001': ['A.17.1.2', 'A.17.2.1'],
                'SOC2':     ['A1.2', 'A1.3'],
                'WAFR':     {'pillar': 'Reliability', 'controls': ['REL13']},
            },
            remediation=(
                f'Backup → Plans → {plan_name} → each rule → add Copy action → '
                f'select a different region\'s vault as destination.'
            ),
            remediation_tr=(
                f'Backup → Planlar → {plan_name} → her kural → Kopyalama eylemi ekle → '
                f'farklı bir bölgenin kasasını hedef olarak seçin.'
            ),
        ))

    return findings
