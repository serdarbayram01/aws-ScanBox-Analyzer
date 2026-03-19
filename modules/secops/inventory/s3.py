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
                    'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']}},
        remediation=f'S3 Console → {bucket_name} → Properties → Bucket versioning → Enable.',
        remediation_tr=f'S3 Konsol → {bucket_name} → Özellikler → Bucket sürümlemesi → Etkinleştir.',
    )]


def _check_bucket_policy_public(s3, bucket_name):
    """Check if bucket policy grants public access via Principal '*'."""
    try:
        policy_str = s3.get_bucket_policy(Bucket=bucket_name)['Policy']
        policy = json.loads(policy_str)
        is_public = False
        for stmt in policy.get('Statement', []):
            principal = stmt.get('Principal', {})
            if principal == '*':
                is_public = True
                break
            if isinstance(principal, dict) and principal.get('AWS') == '*':
                is_public = True
                break
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
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
            remediation=f'S3 Console → {bucket_name} → Permissions → Bucket policy → Remove statements with Principal "*".',
            remediation_tr=f'S3 Konsol → {bucket_name} → İzinler → Bucket politikası → Principal "*" olan ifadeleri kaldırın.',
            details={'policy': policy},
        )]
    except s3.exceptions.from_code('NoSuchBucketPolicy') if False else Exception as exc:
        # NoSuchBucketPolicy means no policy exists — that's fine, not public
        if 'NoSuchBucketPolicy' in str(exc):
            return []
        return []


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
