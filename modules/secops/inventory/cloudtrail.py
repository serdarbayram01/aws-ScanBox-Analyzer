"""SecOps — CloudTrail Checks: enabled, multi-region, log validation, CloudWatch integration, event selectors, S3 bucket encryption."""
from botocore.exceptions import ClientError
from .base import make_finding, not_available
SERVICE = 'CloudTrail'

def run_checks(session, exclude_defaults=False, regions=None):
    ct = session.client('cloudtrail', region_name='us-east-1')
    findings = []
    try:
        trails = ct.describe_trails(includeShadowTrails=False)['trailList']
        if not trails:
            findings.append(make_finding(
                id='cloudtrail_not_enabled',
                title='CloudTrail is not enabled',
                title_tr='CloudTrail etkin değil',
                description='No CloudTrail trails found. All API activity should be logged.',
                description_tr='CloudTrail trail bulunamadı. Tüm API aktivitesi günlüğe kaydedilmelidir.',
                severity='CRITICAL', status='FAIL',
                service=SERVICE, resource_id='account',
                resource_type='AWS::CloudTrail::Trail',
                frameworks={'CIS': ['3.1'], 'HIPAA': ['164.312(b)'], 'ISO27001': ['A.12.4.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                remediation='CloudTrail Console → Create trail → Enable for all regions.',
                remediation_tr='CloudTrail Konsol → Trail oluştur → Tüm bölgeler için etkinleştir.',
            ))
            return findings

        for trail in trails:
            name    = trail['Name']
            arn     = trail['TrailARN']
            home    = trail.get('HomeRegion', 'us-east-1')
            ct_home = session.client('cloudtrail', region_name=home)

            # Multi-region
            multi = trail.get('IsMultiRegionTrail', False)
            findings.append(make_finding(
                id=f'cloudtrail_multiregion_{name}',
                title=f'CloudTrail multi-region: {name}',
                title_tr=f'CloudTrail çok bölgeli: {name}',
                description=f'Trail {name} should be multi-region to capture all API activity.',
                description_tr=f'{name} trail\'i tüm API aktivitesini yakalamak için çok bölgeli olmalıdır.',
                severity='HIGH', status='PASS' if multi else 'FAIL',
                service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                frameworks={'CIS': ['3.1'], 'ISO27001': ['A.12.4.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                remediation=f'CloudTrail → {name} → Edit → Enable for all regions.',
                remediation_tr=f'CloudTrail → {name} → Düzenle → Tüm bölgeler için etkinleştir.',
            ))

            # Log file validation
            validation = trail.get('LogFileValidationEnabled', False)
            findings.append(make_finding(
                id=f'cloudtrail_log_validation_{name}',
                title=f'CloudTrail log file validation: {name}',
                title_tr=f'CloudTrail log dosyası doğrulama: {name}',
                description=f'Trail {name} log file validation detects tampering.',
                description_tr=f'{name} trail\'i log dosyası doğrulaması kurcalamayı tespit eder.',
                severity='HIGH', status='PASS' if validation else 'FAIL',
                service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                frameworks={'CIS': ['3.2'], 'ISO27001': ['A.12.4.2'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                remediation=f'CloudTrail → {name} → Edit → Enable log file validation.',
                remediation_tr=f'CloudTrail → {name} → Düzenle → Log dosyası doğrulamayı etkinleştir.',
            ))

            # CloudWatch Logs integration
            cw_arn = trail.get('CloudWatchLogsLogGroupArn', '')
            findings.append(make_finding(
                id=f'cloudtrail_cloudwatch_{name}',
                title=f'CloudTrail CloudWatch Logs integration: {name}',
                title_tr=f'CloudTrail CloudWatch Logs entegrasyonu: {name}',
                description=f'Trail {name} should send logs to CloudWatch for real-time alerting.',
                description_tr=f'{name} trail\'i gerçek zamanlı uyarı için CloudWatch\'a log göndermelidir.',
                severity='MEDIUM', status='PASS' if cw_arn else 'FAIL',
                service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                frameworks={'CIS': ['3.4'], 'HIPAA': ['164.312(b)'], 'ISO27001': ['A.12.4.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                remediation=f'CloudTrail → {name} → Edit → CloudWatch Logs → Configure.',
                remediation_tr=f'CloudTrail → {name} → Düzenle → CloudWatch Logs → Yapılandır.',
            ))

            # KMS encryption
            kms = trail.get('KMSKeyId', '')
            findings.append(make_finding(
                id=f'cloudtrail_kms_{name}',
                title=f'CloudTrail encrypted with KMS: {name}',
                title_tr=f'CloudTrail KMS ile şifrelenmiş: {name}',
                description=f'Trail {name} should use KMS encryption for log files.',
                description_tr=f'{name} trail\'i log dosyaları için KMS şifrelemesi kullanmalıdır.',
                severity='MEDIUM', status='PASS' if kms else 'FAIL',
                service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                frameworks={'CIS': ['3.7'], 'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.10.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
                remediation=f'CloudTrail → {name} → Edit → Log file SSE-KMS encryption → Enable.',
                remediation_tr=f'CloudTrail → {name} → Düzenle → Log dosyası SSE-KMS şifrelemesi → Etkinleştir.',
            ))

            # S3 bucket access logging for trail
            try:
                status = ct_home.get_trail_status(Name=arn)
                logging_on = status.get('IsLogging', False)
                findings.append(make_finding(
                    id=f'cloudtrail_logging_on_{name}',
                    title=f'CloudTrail logging is active: {name}',
                    title_tr=f'CloudTrail günlükleme aktif: {name}',
                    description=f'Trail {name} logging status should be active.',
                    description_tr=f'{name} trail\'i günlükleme durumu aktif olmalıdır.',
                    severity='CRITICAL', status='PASS' if logging_on else 'FAIL',
                    service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                    frameworks={'CIS': ['3.1'], 'ISO27001': ['A.12.4.1'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                    remediation=f'CloudTrail → {name} → Start logging.',
                    remediation_tr=f'CloudTrail → {name} → Günlüklemeyi başlat.',
                ))
            except Exception:
                pass

            # Event selectors — management events
            try:
                selectors_resp = ct_home.get_event_selectors(TrailName=arn)
                mgmt_events_included = False

                # Check classic event selectors
                for sel in selectors_resp.get('EventSelectors', []):
                    if sel.get('IncludeManagementEvents', False):
                        mgmt_events_included = True
                        break

                # Check advanced event selectors (if classic not found)
                if not mgmt_events_included:
                    for adv in selectors_resp.get('AdvancedEventSelectors', []):
                        for fs in adv.get('FieldSelectors', []):
                            if fs.get('Field') == 'eventCategory' and 'Management' in fs.get('Equals', []):
                                mgmt_events_included = True
                                break
                        if mgmt_events_included:
                            break

                findings.append(make_finding(
                    id=f'cloudtrail_mgmt_events_{name}',
                    title=f'CloudTrail management events enabled: {name}',
                    title_tr=f'CloudTrail yönetim olayları etkin: {name}',
                    description=(
                        f'Trail {name} {"includes" if mgmt_events_included else "does not include"} '
                        f'management events. Management events capture control plane operations '
                        f'(e.g., CreateBucket, RunInstances) and are essential for security auditing.'
                    ),
                    description_tr=(
                        f'{name} trail\'i yönetim olaylarını '
                        f'{"içeriyor" if mgmt_events_included else "içermiyor"}. '
                        f'Yönetim olayları kontrol düzlemi işlemlerini (örn. CreateBucket, RunInstances) '
                        f'yakalar ve güvenlik denetimi için gereklidir.'
                    ),
                    severity='HIGH', status='PASS' if mgmt_events_included else 'FAIL',
                    service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                    frameworks={
                        'CIS': ['3.1'], 'HIPAA': ['164.312(b)'], 'ISO27001': ['A.12.4.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC04']},
                    },
                    remediation=(
                        f'CloudTrail → {name} → Edit → Event selectors → '
                        f'Enable management events (Read/Write: All).'
                    ),
                    remediation_tr=(
                        f'CloudTrail → {name} → Düzenle → Olay seçicileri → '
                        f'Yönetim olaylarını etkinleştir (Okuma/Yazma: Tümü).'
                    ),
                ))
            except Exception as exc:
                findings.append(not_available(f'cloudtrail_event_selectors_{name}', SERVICE, str(exc)))

            # Trail S3 bucket encryption
            bucket_name = trail.get('S3BucketName', '')
            if bucket_name:
                try:
                    s3 = session.client('s3', region_name='us-east-1')
                    s3.get_bucket_encryption(Bucket=bucket_name)
                    # If no exception, encryption is configured
                    findings.append(make_finding(
                        id=f'cloudtrail_s3_encryption_{name}',
                        title=f'CloudTrail S3 bucket encrypted: {bucket_name}',
                        title_tr=f'CloudTrail S3 bucket şifreli: {bucket_name}',
                        description=(
                            f'The S3 bucket {bucket_name} used by trail {name} has '
                            f'default encryption enabled, protecting log files at rest.'
                        ),
                        description_tr=(
                            f'{name} trail\'i tarafından kullanılan S3 bucket {bucket_name} '
                            f'varsayılan şifreleme etkin, log dosyalarını beklemede korur.'
                        ),
                        severity='INFO', status='PASS',
                        service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                        resource_name=bucket_name,
                        frameworks={
                            'CIS': ['3.7'], 'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.10.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC06']},
                        },
                        remediation=f'S3 Console → {bucket_name} → Properties → Default encryption.',
                        remediation_tr=f'S3 Konsol → {bucket_name} → Özellikler → Varsayılan şifreleme.',
                    ))
                except ClientError as ce:
                    error_code = ce.response.get('Error', {}).get('Code', '')
                    if error_code == 'ServerSideEncryptionConfigurationNotFoundError':
                        findings.append(make_finding(
                            id=f'cloudtrail_s3_encryption_{name}',
                            title=f'CloudTrail S3 bucket not encrypted: {bucket_name}',
                            title_tr=f'CloudTrail S3 bucket şifrelenmemiş: {bucket_name}',
                            description=(
                                f'The S3 bucket {bucket_name} used by trail {name} does not have '
                                f'default encryption enabled. CloudTrail log files should be '
                                f'encrypted at rest to protect sensitive API activity data.'
                            ),
                            description_tr=(
                                f'{name} trail\'i tarafından kullanılan S3 bucket {bucket_name} '
                                f'varsayılan şifreleme etkin değil. CloudTrail log dosyaları hassas '
                                f'API aktivite verilerini korumak için beklemede şifrelenmelidir.'
                            ),
                            severity='MEDIUM', status='WARNING',
                            service=SERVICE, resource_id=arn, resource_type='AWS::CloudTrail::Trail',
                            resource_name=bucket_name,
                            frameworks={
                                'CIS': ['3.7'], 'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.10.1.1'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC06']},
                            },
                            remediation=(
                                f'S3 Console → {bucket_name} → Properties → Default encryption → '
                                f'Enable with SSE-S3 or SSE-KMS.'
                            ),
                            remediation_tr=(
                                f'S3 Konsol → {bucket_name} → Özellikler → Varsayılan şifreleme → '
                                f'SSE-S3 veya SSE-KMS ile etkinleştir.'
                            ),
                        ))
                    else:
                        findings.append(not_available(
                            f'cloudtrail_s3_encryption_{name}', SERVICE,
                            f'Cannot check bucket {bucket_name} encryption: {error_code}'
                        ))
                except Exception as exc:
                    findings.append(not_available(
                        f'cloudtrail_s3_encryption_{name}', SERVICE,
                        f'Cannot check bucket {bucket_name} encryption: {str(exc)}'
                    ))

    except Exception as exc:
        findings.append(not_available('cloudtrail_general', SERVICE, str(exc)))
    return findings
