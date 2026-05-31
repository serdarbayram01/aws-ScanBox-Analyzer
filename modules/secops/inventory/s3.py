"""
SecOps — S3 Checks
Public access, encryption, logging, versioning, MFA delete, bucket policy, lifecycle.
"""

import json
from .base import make_finding, not_available

SERVICE = 'S3'


def run_checks(session, exclude_defaults=False, regions=None):
    s3 = session.client('s3', region_name='us-east-1')
    findings = []
    try:
        # Account-level public access block
        findings += _check_account_public_access_block(s3)

        buckets = s3.list_buckets().get('Buckets', [])
        for bucket in buckets:
            name = bucket['Name']
            try:
                region = s3.get_bucket_location(Bucket=name)
                location = region.get('LocationConstraint') or 'us-east-1'
                s3_regional = session.client('s3', region_name=location)
            except Exception:
                s3_regional = s3

            findings += _check_bucket_public_access(s3_regional, name)
            findings += _check_bucket_encryption(s3_regional, name)
            findings += _check_bucket_logging(s3_regional, name)
            findings += _check_bucket_versioning(s3_regional, name)
            findings += _check_bucket_mfa_delete(s3_regional, name)
            findings += _check_bucket_replication(s3_regional, name)
            findings += _check_bucket_object_lock(s3_regional, name)
            findings += _check_bucket_policy_public(s3_regional, name)
            findings += _check_bucket_lifecycle(s3_regional, name)

    except Exception as exc:
        findings.append(not_available('s3_general', SERVICE, str(exc)))
    return findings


def _check_account_public_access_block(s3):
    try:
        block = s3.get_public_access_block()['PublicAccessBlockConfiguration']
        all_on = all([
            block.get('BlockPublicAcls', False),
            block.get('IgnorePublicAcls', False),
            block.get('BlockPublicPolicy', False),
            block.get('RestrictPublicBuckets', False),
        ])
        return [make_finding(
            id='s3_account_public_access_block',
            title='S3 account-level public access block enabled',
            title_tr='S3 hesap düzeyinde genel erişim engeli aktif',
            description='Account-level S3 block public access settings prevent any public access.',
            description_tr='Hesap düzeyindeki S3 genel erişim engeli ayarları tüm genel erişimi önler.',
            severity='HIGH', status='PASS' if all_on else 'FAIL',
            service=SERVICE, resource_id='account',
            resource_type='AWS::S3::AccountPublicAccessBlock',
            frameworks={'CIS': ['2.1.5'], 'ISO27001': ['A.13.1.3'],
                        'SOC2': ['CC6.6', 'C1.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
            remediation='S3 Console → Block Public Access (account settings) → Enable all four settings.',
            remediation_tr='S3 Konsol → Genel Erişimi Engelle (hesap ayarları) → Dört ayarı da etkinleştirin.',
            details={'config': block},
        )]
    except Exception as exc:
        return [not_available('s3_account_public_access_block', SERVICE, str(exc))]


def _check_bucket_public_access(s3, bucket_name):
    findings = []
    try:
        block = s3.get_public_access_block(Bucket=bucket_name)['PublicAccessBlockConfiguration']
        all_on = all([
            block.get('BlockPublicAcls', False),
            block.get('IgnorePublicAcls', False),
            block.get('BlockPublicPolicy', False),
            block.get('RestrictPublicBuckets', False),
        ])
        findings.append(make_finding(
            id=f's3_bucket_public_block_{bucket_name}',
            title=f'S3 bucket public access block: {bucket_name}',
            title_tr=f'S3 bucket genel erişim engeli: {bucket_name}',
            description=f'Bucket {bucket_name} should have all public access block settings enabled.',
            description_tr=f'{bucket_name} bucket\'ı için tüm genel erişim engeli ayarları etkinleştirilmelidir.',
            severity='HIGH', status='PASS' if all_on else 'FAIL',
            service=SERVICE, resource_id=bucket_name,
            resource_type='AWS::S3::Bucket',
            resource_name=bucket_name,
            frameworks={'CIS': ['2.1.5'], 'ISO27001': ['A.13.1.3'],
                        'SOC2': ['CC6.6', 'C1.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
            remediation=f'S3 Console → {bucket_name} → Permissions → Block public access → Enable all.',
            remediation_tr=f'S3 Konsol → {bucket_name} → İzinler → Genel erişimi engelle → Tümünü etkinleştir.',
        ))
    except s3.exceptions.NoSuchPublicAccessBlockConfiguration:
        findings.append(make_finding(
            id=f's3_bucket_public_block_{bucket_name}',
            title=f'S3 bucket public access block: {bucket_name}',
            title_tr=f'S3 bucket genel erişim engeli: {bucket_name}',
            description=f'Bucket {bucket_name} has no public access block configuration.',
            description_tr=f'{bucket_name} bucket\'ında genel erişim engeli yapılandırması yok.',
            severity='HIGH', status='FAIL',
            service=SERVICE, resource_id=bucket_name,
            resource_type='AWS::S3::Bucket', resource_name=bucket_name,
            frameworks={'CIS': ['2.1.5'], 'ISO27001': ['A.13.1.3'],
                        'SOC2': ['CC6.6', 'C1.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
            remediation=f'S3 Console → {bucket_name} → Permissions → Block public access → Enable all.',
            remediation_tr=f'S3 Konsol → {bucket_name} → İzinler → Genel erişimi engelle → Tümünü etkinleştir.',
        ))
    except Exception:
        pass
    return findings


def _check_bucket_encryption(s3, bucket_name):
    try:
        s3.get_bucket_encryption(Bucket=bucket_name)
        encrypted = True
    except s3.exceptions.ClientError as e:
        encrypted = 'ServerSideEncryptionConfigurationNotFoundError' not in str(e)
    except Exception:
        return []
    return [make_finding(
        id=f's3_bucket_encryption_{bucket_name}',
        title=f'S3 bucket server-side encryption: {bucket_name}',
        title_tr=f'S3 bucket sunucu taraflı şifreleme: {bucket_name}',
        description=f'Bucket {bucket_name} should have default server-side encryption enabled.',
        description_tr=f'{bucket_name} bucket\'ı için varsayılan sunucu taraflı şifreleme etkinleştirilmelidir.',
        severity='HIGH', status='PASS' if encrypted else 'FAIL',
        service=SERVICE, resource_id=bucket_name,
        resource_type='AWS::S3::Bucket', resource_name=bucket_name,
        frameworks={'CIS': ['2.1.1'], 'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.10.1.1'],
                    'SOC2': ['CC6.7', 'C1.2'],
                    'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
        remediation=f'S3 Console → {bucket_name} → Properties → Default encryption → Enable.',
        remediation_tr=f'S3 Konsol → {bucket_name} → Özellikler → Varsayılan şifreleme → Etkinleştir.',
    )]


def _check_bucket_logging(s3, bucket_name):
    try:
        log = s3.get_bucket_logging(Bucket=bucket_name).get('LoggingEnabled')
        enabled = log is not None
    except Exception:
        return []
    return [make_finding(
        id=f's3_bucket_logging_{bucket_name}',
        title=f'S3 bucket access logging: {bucket_name}',
        title_tr=f'S3 bucket erişim günlüğü: {bucket_name}',
        description=f'Bucket {bucket_name} should have access logging enabled.',
        description_tr=f'{bucket_name} bucket\'ı için erişim günlüğü etkinleştirilmelidir.',
        severity='MEDIUM', status='PASS' if enabled else 'FAIL',
        service=SERVICE, resource_id=bucket_name,
        resource_type='AWS::S3::Bucket', resource_name=bucket_name,
        frameworks={'CIS': ['2.1.2'], 'HIPAA': ['164.312(b)'], 'ISO27001': ['A.12.4.1'],
                    'SOC2': ['CC7.2', 'CC2.1'],
                    'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
        remediation=f'S3 Console → {bucket_name} → Properties → Server access logging → Enable.',
        remediation_tr=f'S3 Konsol → {bucket_name} → Özellikler → Sunucu erişim günlüğü → Etkinleştir.',
    )]


def _check_bucket_versioning(s3, bucket_name):
    try:
        v = s3.get_bucket_versioning(Bucket=bucket_name)
        enabled = v.get('Status') == 'Enabled'
    except Exception:
        return []
    return [make_finding(
        id=f's3_bucket_versioning_{bucket_name}',
        title=f'S3 bucket versioning: {bucket_name}',
        title_tr=f'S3 bucket sürümleme: {bucket_name}',
        description=f'Bucket {bucket_name} versioning helps protect against accidental deletion.',
        description_tr=f'{bucket_name} bucket\'ı sürümlemesi kazara silmeye karşı koruma sağlar.',
        severity='MEDIUM', status='PASS' if enabled else 'FAIL',
        service=SERVICE, resource_id=bucket_name,
        resource_type='AWS::S3::Bucket', resource_name=bucket_name,
        frameworks={'CIS': ['2.1.3'], 'ISO27001': ['A.12.3.1'],
                    'SOC2': ['A1.2', 'PI1.4'],
                    'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']}},
        remediation=f'S3 Console → {bucket_name} → Properties → Bucket versioning → Enable.',
        remediation_tr=f'S3 Konsol → {bucket_name} → Özellikler → Bucket sürümlemesi → Etkinleştir.',
    )]


def _check_bucket_mfa_delete(s3, bucket_name):
    """MFA Delete protects against accidental/malicious permanent deletion of
    versioned objects. Cannot be set via API — only by the root user via CLI/SDK
    with MFA token, so most accounts have it OFF. We report it as INFO."""
    try:
        v = s3.get_bucket_versioning(Bucket=bucket_name)
        # Versioning must be enabled for MFA-Delete to make sense
        if v.get('Status') != 'Enabled':
            return []
        mfa_on = v.get('MFADelete') == 'Enabled'
    except Exception:
        return []
    return [make_finding(
        id=f's3_bucket_mfa_delete_{bucket_name}',
        title=f'S3 bucket MFA Delete: {bucket_name}',
        title_tr=f'S3 bucket MFA Silme: {bucket_name}',
        description=(
            f'Bucket {bucket_name} {"has" if mfa_on else "does not have"} MFA Delete enabled. '
            f'MFA Delete prevents permanent deletion of versions without a valid MFA token — '
            f'critical for ransomware resilience and tamper-evident audit logs.'
        ),
        description_tr=(
            f'{bucket_name} bucket\'ında MFA Silme '
            f'{"etkin" if mfa_on else "etkin değil"}. '
            f'MFA Silme, geçerli bir MFA token olmadan sürümlerin kalıcı silinmesini önler — '
            f'fidye yazılımı dayanıklılığı ve değiştirilemez denetim günlükleri için kritik.'
        ),
        severity='MEDIUM', status='PASS' if mfa_on else 'WARNING',
        service=SERVICE, resource_id=bucket_name,
        resource_type='AWS::S3::Bucket', resource_name=bucket_name,
        frameworks={
            'CIS':      ['2.1.4'],
            'HIPAA':    ['164.312(c)(1)'],
            'ISO27001': ['A.12.3.1'],
            'SOC2':     ['CC6.1', 'PI1.4'],
            'WAFR':     {'pillar': 'Security', 'controls': ['SEC08']},
        },
        remediation=(
            'Root user only — via AWS CLI with MFA:\n'
            f's3api put-bucket-versioning --bucket {bucket_name} '
            '--versioning-configuration Status=Enabled,MFADelete=Enabled '
            '--mfa "<root-mfa-serial> <token>"'
        ),
        remediation_tr=(
            'Yalnızca root kullanıcı — AWS CLI ile MFA kullanarak:\n'
            f's3api put-bucket-versioning --bucket {bucket_name} '
            '--versioning-configuration Status=Enabled,MFADelete=Enabled '
            '--mfa "<root-mfa-serial> <token>"'
        ),
    )]


def _check_bucket_replication(s3, bucket_name):
    """Cross-region replication for DR / compliance. Only reported when the
    bucket has replication rules — we don't flag every bucket as 'missing'."""
    try:
        resp = s3.get_bucket_replication(Bucket=bucket_name)
        rules = resp.get('ReplicationConfiguration', {}).get('Rules', [])
        enabled_rules = [r for r in rules if r.get('Status') == 'Enabled']
        has_repl = len(enabled_rules) > 0
    except Exception as exc:
        if 'ReplicationConfigurationNotFoundError' in str(exc):
            # No replication — return informational finding so DR-aware
            # consumers can see the gap; default severity LOW.
            return [make_finding(
                id=f's3_bucket_replication_{bucket_name}',
                title=f'S3 bucket replication: {bucket_name}',
                title_tr=f'S3 bucket çoğaltma: {bucket_name}',
                description=(
                    f'Bucket {bucket_name} has no cross-region replication. '
                    f'For business-critical / regulated data, replication to a different '
                    f'region provides disaster recovery and meets RTO/RPO targets.'
                ),
                description_tr=(
                    f'{bucket_name} bucket\'ının bölgeler arası çoğaltması yok. '
                    f'İş açısından kritik / regüle veriler için, farklı bir bölgeye çoğaltma '
                    f'felaket kurtarma ve RTO/RPO hedeflerini karşılar.'
                ),
                severity='LOW', status='WARNING',
                service=SERVICE, resource_id=bucket_name,
                resource_type='AWS::S3::Bucket', resource_name=bucket_name,
                frameworks={
                    'ISO27001': ['A.17.1.2'],
                    'SOC2':     ['A1.2', 'A1.3'],
                    'WAFR':     {'pillar': 'Reliability', 'controls': ['REL09', 'REL13']},
                },
                remediation=(
                    f'S3 → {bucket_name} → Management → Replication rules → Create rule. '
                    f'Versioning must be enabled on source AND destination.'
                ),
                remediation_tr=(
                    f'S3 → {bucket_name} → Yönetim → Çoğaltma kuralları → Kural oluştur. '
                    f'Versioning hem kaynakta hem hedefte etkin olmalı.'
                ),
            )]
        return []
    return [make_finding(
        id=f's3_bucket_replication_{bucket_name}',
        title=f'S3 bucket replication configured: {bucket_name}',
        title_tr=f'S3 bucket çoğaltma yapılandırılmış: {bucket_name}',
        description=f'Bucket {bucket_name} has {len(enabled_rules)} active replication rule(s).',
        description_tr=f'{bucket_name} bucket\'ında {len(enabled_rules)} aktif çoğaltma kuralı var.',
        severity='INFO', status='PASS' if has_repl else 'WARNING',
        service=SERVICE, resource_id=bucket_name,
        resource_type='AWS::S3::Bucket', resource_name=bucket_name,
        frameworks={
            'ISO27001': ['A.17.1.2'],
            'SOC2':     ['A1.2', 'A1.3'],
            'WAFR':     {'pillar': 'Reliability', 'controls': ['REL09', 'REL13']},
        },
        remediation='No action required.',
        remediation_tr='Herhangi bir işlem gerekmiyor.',
    )]


def _check_bucket_object_lock(s3, bucket_name):
    """Object Lock (WORM) — required for HIPAA / SEC 17a-4 / PCI archival.
    Only flagged when explicitly configured — most general-purpose buckets
    don't need it, so missing lock is reported as INFO only."""
    try:
        resp = s3.get_object_lock_configuration(Bucket=bucket_name)
        cfg = resp.get('ObjectLockConfiguration', {})
        enabled = cfg.get('ObjectLockEnabled') == 'Enabled'
        rule = cfg.get('Rule', {}).get('DefaultRetention', {})
        retention_days = rule.get('Days') or (rule.get('Years', 0) * 365)
        mode = rule.get('Mode', 'none')
    except Exception as exc:
        if 'ObjectLockConfigurationNotFoundError' in str(exc):
            return []  # not configured — silent (vast majority of buckets)
        return []
    if not enabled:
        return []
    return [make_finding(
        id=f's3_bucket_object_lock_{bucket_name}',
        title=f'S3 Object Lock configured: {bucket_name}',
        title_tr=f'S3 Object Lock yapılandırılmış: {bucket_name}',
        description=(
            f'Bucket {bucket_name} uses Object Lock in {mode.upper()} mode with '
            f'{retention_days}d default retention. WORM-style protection prevents '
            f'object deletion/overwrite for the retention period.'
        ),
        description_tr=(
            f'{bucket_name} bucket\'ı {retention_days} gün varsayılan saklama ile '
            f'{mode.upper()} modunda Object Lock kullanıyor. WORM tarzı koruma, '
            f'saklama süresi boyunca nesne silme/üzerine yazmayı önler.'
        ),
        severity='INFO', status='PASS',
        service=SERVICE, resource_id=bucket_name,
        resource_type='AWS::S3::Bucket', resource_name=bucket_name,
        frameworks={
            'HIPAA':    ['164.312(c)(1)'],
            'ISO27001': ['A.12.3.1'],
            'SOC2':     ['PI1.4', 'PI1.5'],
            'WAFR':     {'pillar': 'Security', 'controls': ['SEC08']},
        },
        remediation='No action required — Object Lock is active.',
        remediation_tr='Herhangi bir işlem gerekmiyor — Object Lock etkin.',
        details={'mode': mode, 'retention_days': retention_days},
    )]


_SCOPING_CONDITION_KEYS = {
    'aws:sourcearn', 'aws:sourceaccount', 'aws:sourceowner',
    'aws:principalorgid', 'aws:principalorgpaths', 'aws:principalaccount',
    'aws:principalarn', 'aws:sourcevpc', 'aws:sourcevpce',
    'aws:sourceip', 'aws:userid', 'aws:principaltype',
}


def _statement_grants_public_access(stmt):
    """A statement grants public access only if Effect=Allow, Principal is a wildcard,
    and no Condition keys scope it to a specific account/org/VPC/ARN/IP."""
    if stmt.get('Effect') != 'Allow':
        return False

    principal = stmt.get('Principal', {})
    is_wildcard = principal == '*' or (
        isinstance(principal, dict) and (
            principal.get('AWS') == '*' or
            (isinstance(principal.get('AWS'), list) and '*' in principal['AWS'])
        )
    )
    if not is_wildcard:
        return False

    conditions = stmt.get('Condition') or {}
    for cond_kvs in conditions.values():
        if not isinstance(cond_kvs, dict):
            continue
        for cond_key in cond_kvs.keys():
            if cond_key.lower() in _SCOPING_CONDITION_KEYS:
                return False

    return True


def _check_bucket_policy_public(s3, bucket_name):
    """Check if bucket policy grants public access via an unconditional Allow with Principal '*'."""
    try:
        policy_str = s3.get_bucket_policy(Bucket=bucket_name)['Policy']
    except Exception as exc:
        if 'NoSuchBucketPolicy' in str(exc):
            return []
        return []

    try:
        policy = json.loads(policy_str)
    except Exception:
        return []

    statements = policy.get('Statement', [])
    if isinstance(statements, dict):
        statements = [statements]

    is_public = any(_statement_grants_public_access(stmt) for stmt in statements)

    return [make_finding(
        id=f's3_bucket_policy_public_{bucket_name}',
        title=f'S3 bucket policy public access: {bucket_name}',
        title_tr=f'S3 bucket politikası genel erişim: {bucket_name}',
        description=f'Bucket {bucket_name} has a policy that grants public access (Principal: "*").',
        description_tr=f'{bucket_name} bucket\'ının politikası genel erişime izin veriyor (Principal: "*").',
        severity='CRITICAL' if is_public else 'INFO',
        status='FAIL' if is_public else 'PASS',
        service=SERVICE, resource_id=bucket_name,
        resource_type='AWS::S3::BucketPolicy',
        resource_name=bucket_name,
        frameworks={'CIS': ['2.1.5'], 'HIPAA': ['164.312(a)(1)'], 'ISO27001': ['A.13.1.3'],
                    'SOC2': ['CC6.6', 'C1.1'],
                    'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
        remediation=f'S3 Console → {bucket_name} → Permissions → Bucket policy → Remove statements with Principal "*".',
        remediation_tr=f'S3 Konsol → {bucket_name} → İzinler → Bucket politikası → Principal "*" olan ifadeleri kaldırın.',
        details={'policy': policy},
    )]


def _check_bucket_lifecycle(s3, bucket_name):
    """Check if bucket has a lifecycle configuration."""
    try:
        s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        return [make_finding(
            id=f's3_bucket_lifecycle_{bucket_name}',
            title=f'S3 bucket lifecycle configured: {bucket_name}',
            title_tr=f'S3 bucket yaşam döngüsü yapılandırılmış: {bucket_name}',
            description=f'Bucket {bucket_name} has lifecycle rules configured for cost optimization.',
            description_tr=f'{bucket_name} bucket\'ı maliyet optimizasyonu için yaşam döngüsü kuralları yapılandırılmış.',
            severity='LOW', status='PASS',
            service=SERVICE, resource_id=bucket_name,
            resource_type='AWS::S3::Bucket',
            resource_name=bucket_name,
            frameworks={'CIS': ['2.1.3'], 'ISO27001': ['A.12.3.1'],
                        'WAFR': {'pillar': 'Cost Optimization', 'controls': ['COST07']}},
            remediation=f'S3 Console → {bucket_name} → Management → Lifecycle rules.',
            remediation_tr=f'S3 Konsol → {bucket_name} → Yönetim → Yaşam döngüsü kuralları.',
        )]
    except Exception as exc:
        if 'NoSuchLifecycleConfiguration' in str(exc):
            return [make_finding(
                id=f's3_bucket_lifecycle_{bucket_name}',
                title=f'S3 bucket lifecycle not configured: {bucket_name}',
                title_tr=f'S3 bucket yaşam döngüsü yapılandırılmamış: {bucket_name}',
                description=f'Bucket {bucket_name} has no lifecycle rules. Configure lifecycle rules to transition or expire objects for cost optimization.',
                description_tr=f'{bucket_name} bucket\'ında yaşam döngüsü kuralı yok. Maliyet optimizasyonu için nesneleri geçiş veya süre sonu için yaşam döngüsü kuralları yapılandırın.',
                severity='LOW', status='WARNING',
                service=SERVICE, resource_id=bucket_name,
                resource_type='AWS::S3::Bucket',
                resource_name=bucket_name,
                frameworks={'CIS': ['2.1.3'], 'ISO27001': ['A.12.3.1'],
                            'WAFR': {'pillar': 'Cost Optimization', 'controls': ['COST07']}},
                remediation=f'S3 Console → {bucket_name} → Management → Create lifecycle rule to transition/expire objects.',
                remediation_tr=f'S3 Konsol → {bucket_name} → Yönetim → Nesneleri geçiş/süre sonu için yaşam döngüsü kuralı oluşturun.',
            )]
        return []
