"""SecOps — CloudWatch Checks: log group encryption, retention, security alarms."""
from .base import make_finding, not_available

SERVICE = 'CloudWatch'

# Critical security events that should have CloudWatch alarms (CIS Benchmark)
REQUIRED_ALARMS = {
    'cw_alarm_root_usage':           ('root account usage', [r'\.root', r'userIdentity\.type.*Root', 'Root']),
    'cw_alarm_unauthorized_api':     ('unauthorized API calls', ['AccessDenied', 'UnauthorizedOperation']),
    'cw_alarm_no_mfa_console':       ('console sign-in without MFA', ['ConsoleLogin', 'notExists.*mfaAuthenticated']),
    'cw_alarm_iam_policy_changes':   ('IAM policy changes', ['CreatePolicy', 'DeletePolicy', 'AttachRolePolicy', 'DetachRolePolicy']),
    'cw_alarm_cloudtrail_changes':   ('CloudTrail configuration changes', ['StopLogging', 'DeleteTrail', 'UpdateTrail']),
    'cw_alarm_console_auth_failure': ('console authentication failures', ['ConsoleLogin.*Failed']),
    'cw_alarm_cmk_deletion':         ('CMK deletion/disabling', ['DisableKey', 'ScheduleKeyDeletion']),
    'cw_alarm_s3_policy_changes':    ('S3 bucket policy changes', ['PutBucketPolicy', 'DeleteBucketPolicy']),
    'cw_alarm_sg_changes':           ('security group changes', ['AuthorizeSecurityGroup', 'RevokeSecurityGroup', 'CreateSecurityGroup', 'DeleteSecurityGroup']),
    'cw_alarm_nacl_changes':         ('network ACL changes', ['CreateNetworkAcl', 'DeleteNetworkAcl', 'ReplaceNetworkAcl']),
    'cw_alarm_network_gw_changes':   ('network gateway changes', ['CreateCustomerGateway', 'DeleteCustomerGateway', 'AttachInternetGateway']),
    'cw_alarm_vpc_changes':          ('VPC changes', ['CreateVpc', 'DeleteVpc', 'ModifyVpcAttribute']),
}


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('cw_regions', SERVICE, str(exc))]

    for region in regions:
        logs = session.client('logs', region_name=region)

        # --- Log Groups: encryption + retention ---
        try:
            paginator = logs.get_paginator('describe_log_groups')
            for page in paginator.paginate():
                for lg in page.get('logGroups', []):
                    name        = lg.get('logGroupName', 'unknown')
                    kms_key_id  = lg.get('kmsKeyId', '')
                    retention   = lg.get('retentionInDays')  # None = never expires

                    findings.append(make_finding(
                        id=f'cw_lg_encryption_{name}_{region}'.replace('/', '_'),
                        title=f'CloudWatch log group encrypted: {name}',
                        title_tr=f'CloudWatch günlük grubu şifreli: {name}',
                        description=f'Log group {name} in {region} should use a KMS key for encryption at rest.',
                        description_tr=f'{region} bölgesindeki {name} günlük grubu, bekleyen şifreleme için KMS anahtarı kullanmalıdır.',
                        severity='MEDIUM', status='PASS' if kms_key_id else 'FAIL',
                        service=SERVICE, resource_id=lg.get('arn', name),
                        resource_type='AWS::Logs::LogGroup', region=region,
                        frameworks={
                            'HIPAA': ['164.312(a)(2)(iv)'],
                            'ISO27001': ['A.10.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC08']},
                        },
                        remediation=f'CloudWatch Console → Log groups → {name} → Actions → Encrypt log group → Select KMS key.',
                        remediation_tr=f'CloudWatch Konsol → Günlük grupları → {name} → Eylemler → Günlük grubunu şifrele → KMS anahtarı seç.',
                    ))

                    if retention is None:
                        findings.append(make_finding(
                            id=f'cw_lg_retention_{name}_{region}'.replace('/', '_'),
                            title=f'CloudWatch log group has no retention policy: {name}',
                            title_tr=f'CloudWatch günlük grubunda saklama politikası yok: {name}',
                            description=f'Log group {name} in {region} never expires. Set a retention policy to control costs and reduce data exposure.',
                            description_tr=f'{region} bölgesindeki {name} günlük grubu hiç sona ermiyor. Maliyetleri kontrol etmek ve veri maruziyetini azaltmak için saklama politikası belirleyin.',
                            severity='LOW', status='FAIL',
                            service=SERVICE, resource_id=lg.get('arn', name),
                            resource_type='AWS::Logs::LogGroup', region=region,
                            frameworks={'WAFR': {'pillar': 'Operational Excellence', 'controls': ['OPS06']}},
                            remediation=f'CloudWatch Console → Log groups → {name} → Edit retention setting (90–365 days recommended).',
                            remediation_tr=f'CloudWatch Konsol → Günlük grupları → {name} → Saklama ayarını düzenle (90–365 gün önerilir).',
                        ))
        except Exception as exc:
            findings.append(not_available(f'cw_loggroups_{region}', SERVICE, str(exc)))

        # --- Security Alarms (CIS Benchmark) — check only once in us-east-1 ---
        if region != 'us-east-1':
            continue
        try:
            # Collect all metric filters across all log groups
            all_filters = []
            paginator = logs.get_paginator('describe_metric_filters')
            for page in paginator.paginate():
                all_filters.extend(page.get('metricFilters', []))

            # Flatten all filter patterns for quick lookup
            filter_patterns = ' '.join(f.get('filterPattern', '').lower() for f in all_filters)

            for alarm_id, (alarm_desc, keywords) in REQUIRED_ALARMS.items():
                # Check if any filter pattern covers this alarm's keywords
                covered = any(kw.lower() in filter_patterns for kw in keywords)
                findings.append(make_finding(
                    id=f'{alarm_id}',
                    title=f'CloudWatch alarm for {alarm_desc}',
                    title_tr=f'CloudWatch alarmı: {alarm_desc}',
                    description=f'CIS Benchmark requires a CloudWatch metric filter and alarm for {alarm_desc}.',
                    description_tr=f'CIS Benchmark, {alarm_desc} için CloudWatch metrik filtresi ve alarmı gerektirir.',
                    severity='MEDIUM', status='PASS' if covered else 'FAIL',
                    service=SERVICE, resource_id='global',
                    resource_type='AWS::CloudWatch::Alarm', region='us-east-1',
                    frameworks={
                        'CIS': ['3.1–3.14'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC04']},
                    },
                    remediation=f'Create a CloudWatch metric filter + alarm for: {alarm_desc}. See CIS AWS Foundations Benchmark section 3.',
                    remediation_tr=f'{alarm_desc} için CloudWatch metrik filtresi ve alarmı oluşturun. CIS AWS Foundations Benchmark bölüm 3\'e bakın.',
                ))
        except Exception as exc:
            findings.append(not_available('cw_alarms', SERVICE, str(exc)))

    return findings
