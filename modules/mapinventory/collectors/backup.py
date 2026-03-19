"""
Map Inventory — AWS Backup Collector
Resource types: vault, plan, framework, report-plan, restore-testing-plan
"""

from .base import make_resource, tags_to_dict, get_tag_value


def collect_backup_resources(session, region, account_id):
    """Collect AWS Backup resources for a given region."""
    resources = []
    try:
        client = session.client('backup', region_name=region)
    except Exception:
        return resources

    # ── Backup Vaults ─────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_backup_vaults')
        for page in paginator.paginate():
            for vault in page.get('BackupVaultList', []):
                vault_name = vault.get('BackupVaultName', '')
                vault_arn = vault.get('BackupVaultArn', '')
                is_default = (vault_name == 'Default' or vault_name == 'aws/efs/automatic-backup-vault')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=vault_arn)
                    tags = tag_resp.get('Tags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='backup',
                    resource_type='vault',
                    resource_id=vault_name,
                    arn=vault_arn,
                    name=vault_name,
                    region=region,
                    details={
                        'recovery_points': vault.get('NumberOfRecoveryPoints', 0),
                        'encryption_key_arn': vault.get('EncryptionKeyArn', ''),
                        'creation_date': str(vault.get('CreationDate', '')),
                        'locked': vault.get('Locked', False),
                        'lock_date': str(vault.get('LockDate', '')),
                        'min_retention_days': vault.get('MinRetentionDays', 0),
                        'max_retention_days': vault.get('MaxRetentionDays', 0),
                    },
                    tags=tags,
                    is_default=is_default,
                ))
    except Exception:
        pass

    # ── Backup Plans ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_backup_plans')
        for page in paginator.paginate():
            for plan in page.get('BackupPlansList', []):
                plan_id = plan.get('BackupPlanId', '')
                plan_name = plan.get('BackupPlanName', plan_id)
                plan_arn = plan.get('BackupPlanArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=plan_arn)
                    tags = tag_resp.get('Tags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='backup',
                    resource_type='plan',
                    resource_id=plan_id,
                    arn=plan_arn,
                    name=plan_name,
                    region=region,
                    details={
                        'version_id': plan.get('VersionId', ''),
                        'creation_date': str(plan.get('CreationDate', '')),
                        'last_execution_date': str(plan.get('LastExecutionDate', '')),
                        'advanced_settings': plan.get('AdvancedBackupSettings', []),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Frameworks ────────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_frameworks')
        for page in paginator.paginate():
            for fw in page.get('Frameworks', []):
                fw_name = fw.get('FrameworkName', '')
                fw_arn = fw.get('FrameworkArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=fw_arn)
                    tags = tag_resp.get('Tags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='backup',
                    resource_type='framework',
                    resource_id=fw_name,
                    arn=fw_arn,
                    name=fw_name,
                    region=region,
                    details={
                        'description': fw.get('FrameworkDescription', ''),
                        'number_of_controls': fw.get('NumberOfControls', 0),
                        'creation_time': str(fw.get('CreationTime', '')),
                        'deployment_status': fw.get('DeploymentStatus', ''),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Report Plans ──────────────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_report_plans')
        for page in paginator.paginate():
            for rp in page.get('ReportPlans', []):
                rp_name = rp.get('ReportPlanName', '')
                rp_arn = rp.get('ReportPlanArn', '')
                delivery = rp.get('ReportDeliveryChannel', {})
                setting = rp.get('ReportSetting', {})

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=rp_arn)
                    tags = tag_resp.get('Tags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='backup',
                    resource_type='report-plan',
                    resource_id=rp_name,
                    arn=rp_arn,
                    name=rp_name,
                    region=region,
                    details={
                        'description': rp.get('ReportPlanDescription', ''),
                        'report_template': setting.get('ReportTemplate', ''),
                        'delivery_s3_bucket': delivery.get('S3BucketName', ''),
                        'delivery_s3_prefix': delivery.get('S3KeyPrefix', ''),
                        'delivery_formats': delivery.get('Formats', []),
                        'creation_time': str(rp.get('CreationTime', '')),
                        'last_attempted_execution_time': str(rp.get('LastAttemptedExecutionTime', '')),
                        'last_successful_execution_time': str(rp.get('LastSuccessfulExecutionTime', '')),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    # ── Restore Testing Plans ─────────────────────────────────────────
    try:
        paginator = client.get_paginator('list_restore_testing_plans')
        for page in paginator.paginate():
            for rtp in page.get('RestoreTestingPlans', []):
                rtp_name = rtp.get('RestoreTestingPlanName', '')
                rtp_arn = rtp.get('RestoreTestingPlanArn', '')

                tags = {}
                try:
                    tag_resp = client.list_tags(ResourceArn=rtp_arn)
                    tags = tag_resp.get('Tags', {})
                except Exception:
                    pass

                resources.append(make_resource(
                    service='backup',
                    resource_type='restore-testing-plan',
                    resource_id=rtp_name,
                    arn=rtp_arn,
                    name=rtp_name,
                    region=region,
                    details={
                        'schedule_expression': rtp.get('ScheduleExpression', ''),
                        'start_window_hours': rtp.get('StartWindowHours', 0),
                        'creation_time': str(rtp.get('CreationTime', '')),
                        'last_execution_time': str(rtp.get('LastExecutionTime', '')),
                        'last_updated_time': str(rtp.get('LastUpdatedTime', '')),
                    },
                    tags=tags,
                ))
    except Exception:
        pass

    return resources
