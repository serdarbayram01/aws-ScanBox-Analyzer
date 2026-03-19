"""SecOps — DynamoDB Checks: encryption, PITR, backup."""
from .base import make_finding, not_available

SERVICE = 'DynamoDB'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('dynamodb_regions', SERVICE, str(exc))]

    for region in regions:
        ddb = session.client('dynamodb', region_name=region)
        try:
            paginator = ddb.get_paginator('list_tables')
            for page in paginator.paginate():
                for table_name in page.get('TableNames', []):
                    try:
                        desc = ddb.describe_table(TableName=table_name)['Table']
                        table_arn = desc.get('TableArn', table_name)

                        # Encryption at rest (CMK preferred)
                        sse = desc.get('SSEDescription', {})
                        sse_type   = sse.get('SSEType', 'AES256')  # AES256 = default AWS key
                        sse_status = sse.get('Status', 'DISABLED')
                        has_cmk = sse_status == 'ENABLED' and sse_type == 'KMS'
                        # AES256 (default) is encrypted but not with CMK
                        is_encrypted = sse_status in ('ENABLED', 'ENABLING') or sse_type == 'AES256'

                        findings.append(make_finding(
                            id=f'dynamodb_encryption_{table_name}_{region}',
                            title=f'DynamoDB table encrypted at rest: {table_name}',
                            title_tr=f'DynamoDB tablosu bekleyen verileri şifreli: {table_name}',
                            description=(
                                f'Table {table_name} in {region} uses CMK encryption.'
                                if has_cmk else
                                f'Table {table_name} in {region} uses default AWS-managed encryption (AES256), not a customer-managed KMS key.'
                            ),
                            description_tr=(
                                f'{region} bölgesindeki {table_name} tablosu CMK şifrelemesi kullanıyor.'
                                if has_cmk else
                                f'{region} bölgesindeki {table_name} tablosu varsayılan AWS yönetimli şifreleme (AES256) kullanıyor, müşteri yönetimli KMS anahtarı değil.'
                            ),
                            severity='LOW', status='PASS' if has_cmk else 'WARNING',
                            service=SERVICE, resource_id=table_arn,
                            resource_type='AWS::DynamoDB::Table', region=region,
                            frameworks={
                                'CIS': ['2.4'],
                                'HIPAA': ['164.312(a)(2)(iv)'],
                                'ISO27001': ['A.10.1.1'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC08']},
                            },
                            remediation=f'DynamoDB Console → {table_name} → Additional settings → Encryption at rest → Use KMS key.',
                            remediation_tr=f'DynamoDB Konsol → {table_name} → Ek ayarlar → Bekleyen şifreleme → KMS anahtarı kullan.',
                        ))

                        # Point-in-time recovery
                        try:
                            pitr = ddb.describe_continuous_backups(TableName=table_name)
                            pitr_status = (pitr.get('ContinuousBackupsDescription', {})
                                           .get('PointInTimeRecoveryDescription', {})
                                           .get('PointInTimeRecoveryStatus', 'DISABLED'))
                            pitr_enabled = pitr_status == 'ENABLED'
                        except Exception:
                            pitr_enabled = False

                        findings.append(make_finding(
                            id=f'dynamodb_pitr_{table_name}_{region}',
                            title=f'DynamoDB point-in-time recovery enabled: {table_name}',
                            title_tr=f'DynamoDB zaman içinde nokta kurtarma aktif: {table_name}',
                            description=f'Table {table_name} in {region} should have PITR enabled for accidental deletion recovery.',
                            description_tr=f'{region} bölgesindeki {table_name} tablosunda yanlışlıkla silme durumunda kurtarma için PITR etkinleştirilmelidir.',
                            severity='MEDIUM', status='PASS' if pitr_enabled else 'FAIL',
                            service=SERVICE, resource_id=table_arn,
                            resource_type='AWS::DynamoDB::Table', region=region,
                            frameworks={
                                'CIS': ['2.7'],
                                'HIPAA': ['164.308(a)(7)(ii)(B)'],
                                'ISO27001': ['A.12.3.1'],
                                'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']},
                            },
                            remediation=f'DynamoDB Console → {table_name} → Backups → Enable point-in-time recovery.',
                            remediation_tr=f'DynamoDB Konsol → {table_name} → Yedekler → Zaman içinde nokta kurtarmayı etkinleştir.',
                        ))

                        # Deletion protection
                        del_protect = desc.get('DeletionProtectionEnabled', False)
                        findings.append(make_finding(
                            id=f'dynamodb_delete_protect_{table_name}_{region}',
                            title=f'DynamoDB deletion protection: {table_name}',
                            title_tr=f'DynamoDB silme koruması: {table_name}',
                            description=f'Table {table_name} in {region} {"has" if del_protect else "does not have"} deletion protection enabled.',
                            description_tr=f'{region} bölgesindeki {table_name} tablosunda silme koruması {"aktif" if del_protect else "aktif değil"}.',
                            severity='MEDIUM', status='PASS' if del_protect else 'WARNING',
                            service=SERVICE, resource_id=table_arn,
                            resource_type='AWS::DynamoDB::Table', region=region,
                            frameworks={
                                'CIS': ['2.7'],
                                'ISO27001': ['A.12.3.1'],
                                'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']},
                            },
                            remediation=f'DynamoDB Console → {table_name} → Additional settings → Enable deletion protection.',
                            remediation_tr=f'DynamoDB Konsol → {table_name} → Ek ayarlar → Silme korumasını etkinleştir.',
                        ))

                    except Exception:
                        pass
        except Exception as exc:
            findings.append(not_available(f'dynamodb_{region}', SERVICE, str(exc)))

    return findings
