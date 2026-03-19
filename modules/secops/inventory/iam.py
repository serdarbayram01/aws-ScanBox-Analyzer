"""
SecOps — IAM Checks
Covers: root MFA, access keys, password policy, user MFA, credential report,
        admin policies, support role, group membership.
"""

import io
import csv
import time
from datetime import datetime, timezone

from .base import make_finding, not_available

SERVICE = 'IAM'
FW = {
    'CIS':     ['1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '1.8', '1.9', '1.10', '1.11', '1.12', '1.13', '1.14', '1.15', '1.16'],
    'HIPAA':   ['164.308(a)(3)', '164.312(a)(1)', '164.312(a)(2)(i)'],
    'ISO27001':['A.9.1.1', 'A.9.2.1', 'A.9.2.3', 'A.9.2.4', 'A.9.4.2'],
    'WAFR':    {'pillar': 'Security', 'controls': ['SEC01', 'SEC02', 'SEC03']},
}


def run_checks(session, exclude_defaults=False, regions=None):
    iam = session.client('iam')
    findings = []
    try:
        findings += _check_account_summary(iam)
        findings += _check_password_policy(iam)
        cred_findings, users = _check_credential_report(iam)
        findings += cred_findings
        findings += _check_support_role(iam)
        findings += _check_admin_policies(iam)
        findings += _check_inactive_users(users)
        findings += _check_console_no_mfa(users)
        findings += _check_inline_policies(iam)
    except Exception as exc:
        findings.append(not_available('iam_general', SERVICE, str(exc)))
    return findings


# ---------------------------------------------------------------------------

def _check_account_summary(iam):
    findings = []
    try:
        s = iam.get_account_summary()['SummaryMap']

        # Root MFA
        mfa_on = s.get('AccountMFAEnabled', 0) == 1
        findings.append(make_finding(
            id='iam_root_mfa',
            title='Root account MFA enabled',
            title_tr='Root hesabı MFA aktif',
            description='The root account should have MFA enabled to prevent unauthorized access.',
            description_tr='Root hesabı yetkisiz erişimi önlemek için MFA etkinleştirilmelidir.',
            severity='CRITICAL',
            status='PASS' if mfa_on else 'FAIL',
            service=SERVICE,
            resource_id='root',
            resource_type='AWS::IAM::Root',
            frameworks={'CIS': ['1.5'], 'HIPAA': ['164.312(a)(2)(i)'], 'ISO27001': ['A.9.4.2'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
            remediation='AWS Console → IAM → Dashboard → Activate MFA on your root account.',
            remediation_tr='AWS Konsol → IAM → Dashboard → Root hesabınızda MFA etkinleştirin.',
        ))

        # Root access keys
        has_keys = s.get('AccountAccessKeysPresent', 0) > 0
        findings.append(make_finding(
            id='iam_root_no_access_keys',
            title='Root account has no access keys',
            title_tr='Root hesabında erişim anahtarı yok',
            description='The root account should not have active access keys.',
            description_tr='Root hesabının aktif erişim anahtarı olmamalıdır.',
            severity='CRITICAL',
            status='FAIL' if has_keys else 'PASS',
            service=SERVICE,
            resource_id='root',
            resource_type='AWS::IAM::Root',
            frameworks={'CIS': ['1.4'], 'HIPAA': ['164.312(a)(1)'], 'ISO27001': ['A.9.2.3'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
            remediation='IAM Console → Security Credentials → Delete root access keys.',
            remediation_tr='IAM Konsol → Güvenlik Kimlik Bilgileri → Root erişim anahtarlarını silin.',
        ))
    except Exception as exc:
        findings.append(not_available('iam_account_summary', SERVICE, str(exc)))
    return findings


def _check_password_policy(iam):
    findings = []
    try:
        policy = iam.get_account_password_policy()['PasswordPolicy']

        checks = [
            ('iam_pw_length',     'Minimum password length ≥ 14',         'Minimum şifre uzunluğu ≥ 14',
             policy.get('MinimumPasswordLength', 0) >= 14, 'MEDIUM', '1.8'),
            ('iam_pw_uppercase',  'Password requires uppercase',           'Şifre büyük harf gerektiriyor',
             policy.get('RequireUppercaseCharacters', False), 'MEDIUM', '1.9'),
            ('iam_pw_lowercase',  'Password requires lowercase',           'Şifre küçük harf gerektiriyor',
             policy.get('RequireLowercaseCharacters', False), 'MEDIUM', '1.9'),
            ('iam_pw_numbers',    'Password requires numbers',             'Şifre rakam gerektiriyor',
             policy.get('RequireNumbers', False), 'MEDIUM', '1.9'),
            ('iam_pw_symbols',    'Password requires symbols',             'Şifre sembol gerektiriyor',
             policy.get('RequireSymbols', False), 'MEDIUM', '1.9'),
            ('iam_pw_reuse',      'Password reuse prevention ≥ 24',        'Şifre yeniden kullanım önlemi ≥ 24',
             policy.get('PasswordReusePrevention', 0) >= 24, 'LOW', '1.9'),
            ('iam_pw_expiry',     'Password expiry ≤ 90 days',             'Şifre süresi ≤ 90 gün',
             0 < policy.get('MaxPasswordAge', 0) <= 90, 'LOW', '1.9'),
        ]
        for cid, title, title_tr, passed, sev, cis in checks:
            findings.append(make_finding(
                id=cid, title=title, title_tr=title_tr,
                description=f'IAM password policy: {title.lower()}.',
                description_tr=f'IAM şifre politikası: {title_tr.lower()}.',
                severity=sev, status='PASS' if passed else 'FAIL',
                service=SERVICE, resource_id='password_policy',
                resource_type='AWS::IAM::PasswordPolicy',
                frameworks={'CIS': [cis], 'ISO27001': ['A.9.4.2'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
                remediation='IAM Console → Account Settings → Edit password policy.',
                remediation_tr='IAM Konsol → Hesap Ayarları → Şifre politikasını düzenleyin.',
            ))
    except iam.exceptions.NoSuchEntityException:
        findings.append(make_finding(
            id='iam_pw_policy_missing',
            title='No IAM password policy configured',
            title_tr='IAM şifre politikası yapılandırılmamış',
            description='An IAM password policy is not configured for this account.',
            description_tr='Bu hesap için IAM şifre politikası yapılandırılmamış.',
            severity='HIGH', status='FAIL',
            service=SERVICE, resource_id='password_policy',
            resource_type='AWS::IAM::PasswordPolicy',
            frameworks={'CIS': ['1.8', '1.9'], 'ISO27001': ['A.9.4.2'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
            remediation='IAM Console → Account Settings → Set password policy.',
            remediation_tr='IAM Konsol → Hesap Ayarları → Şifre politikası belirleyin.',
        ))
    except Exception as exc:
        findings.append(not_available('iam_pw_policy', SERVICE, str(exc)))
    return findings


def _check_credential_report(iam):
    findings = []
    users = []
    try:
        # Generate / retrieve report
        for _ in range(10):
            resp = iam.generate_credential_report()
            if resp['State'] == 'COMPLETE':
                break
            time.sleep(1)

        report_csv = iam.get_credential_report()['Content'].decode('utf-8')
        reader = csv.DictReader(io.StringIO(report_csv))

        for row in reader:
            user = row['user']
            if user == '<root_account>':
                continue

            users.append(row)

            # MFA enabled for each user
            mfa = row.get('mfa_active', 'false').lower() == 'true'
            findings.append(make_finding(
                id=f'iam_user_mfa_{user}',
                title=f'MFA enabled for user: {user}',
                title_tr=f'Kullanıcı için MFA aktif: {user}',
                description=f'IAM user {user} should have MFA enabled.',
                description_tr=f'IAM kullanıcısı {user} için MFA etkinleştirilmelidir.',
                severity='HIGH', status='PASS' if mfa else 'FAIL',
                service=SERVICE, resource_id=user,
                resource_type='AWS::IAM::User',
                frameworks={'CIS': ['1.10'], 'HIPAA': ['164.312(a)(2)(i)'],
                            'ISO27001': ['A.9.4.2'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
                remediation=f'IAM Console → Users → {user} → Security credentials → Assign MFA.',
                remediation_tr=f'IAM Konsol → Kullanıcılar → {user} → Güvenlik kimlik bilgileri → MFA atayın.',
            ))

            # Access key rotation < 90 days
            for key_n in ('1', '2'):
                active = row.get(f'access_key_{key_n}_active', 'false').lower() == 'true'
                last   = row.get(f'access_key_{key_n}_last_rotated', 'N/A')
                if active and last not in ('N/A', 'no_information'):
                    try:
                        dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                        age_days = (datetime.now(timezone.utc) - dt).days
                        stale = age_days > 90
                    except Exception:
                        stale = False
                        age_days = 0
                    findings.append(make_finding(
                        id=f'iam_key_rotation_{user}_{key_n}',
                        title=f'Access key {key_n} rotated < 90 days: {user}',
                        title_tr=f'Erişim anahtarı {key_n} 90 günden önce rotasyona sokulmuş: {user}',
                        description=f'Access key {key_n} for {user} is {age_days} days old.',
                        description_tr=f'{user} için erişim anahtarı {key_n}, {age_days} gündür kullanılıyor.',
                        severity='MEDIUM', status='FAIL' if stale else 'PASS',
                        service=SERVICE, resource_id=user,
                        resource_type='AWS::IAM::AccessKey',
                        frameworks={'CIS': ['1.14'], 'ISO27001': ['A.9.2.4'],
                                    'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
                        remediation='Rotate access keys every 90 days.',
                        remediation_tr='Erişim anahtarlarını her 90 günde bir döndürün.',
                        details={'age_days': age_days},
                    ))

    except Exception as exc:
        findings.append(not_available('iam_credential_report', SERVICE, str(exc)))
    return findings, users


def _check_support_role(iam):
    try:
        paginator = iam.get_paginator('list_policies')
        for page in paginator.paginate(Scope='AWS'):
            for policy in page['Policies']:
                if policy['PolicyName'] == 'AWSSupportAccess':
                    entities = iam.list_entities_for_policy(
                        PolicyArn=policy['Arn'])
                    attached = (
                        len(entities.get('PolicyRoles', [])) +
                        len(entities.get('PolicyGroups', [])) +
                        len(entities.get('PolicyUsers', []))
                    ) > 0
                    return [make_finding(
                        id='iam_support_role',
                        title='AWS Support role is configured',
                        title_tr='AWS Destek rolü yapılandırılmış',
                        description='A role with AWSSupportAccess policy should exist for incident management.',
                        description_tr='Olay yönetimi için AWSSupportAccess politikasına sahip bir rol bulunmalıdır.',
                        severity='LOW', status='PASS' if attached else 'FAIL',
                        service=SERVICE, resource_id='AWSSupportAccess',
                        resource_type='AWS::IAM::Policy',
                        frameworks={'CIS': ['1.17'], 'WAFR': {'pillar': 'Security', 'controls': ['SEC01']}},
                        remediation='Create a role with AWSSupportAccess managed policy.',
                        remediation_tr='AWSSupportAccess politikasıyla bir rol oluşturun.',
                    )]
    except Exception as exc:
        return [not_available('iam_support_role', SERVICE, str(exc))]
    return [make_finding(
        id='iam_support_role',
        title='AWS Support role is configured',
        title_tr='AWS Destek rolü yapılandırılmış',
        description='AWSSupportAccess policy not found or not attached.',
        description_tr='AWSSupportAccess politikası bulunamadı veya atanmadı.',
        severity='LOW', status='FAIL',
        service=SERVICE, resource_id='AWSSupportAccess',
        resource_type='AWS::IAM::Policy',
        frameworks={'CIS': ['1.17'], 'WAFR': {'pillar': 'Security', 'controls': ['SEC01']}},
        remediation='Create a role with AWSSupportAccess managed policy.',
        remediation_tr='AWSSupportAccess politikasıyla bir rol oluşturun.',
    )]


def _check_admin_policies(iam):
    findings = []
    try:
        # Check for custom policies with admin (*:*) access
        paginator = iam.get_paginator('list_policies')
        for page in paginator.paginate(Scope='Local'):
            for policy in page['Policies']:
                try:
                    version = iam.get_policy_version(
                        PolicyArn=policy['Arn'],
                        VersionId=policy['DefaultVersionId']
                    )['PolicyVersion']['Document']
                    for stmt in version.get('Statement', []):
                        if (stmt.get('Effect') == 'Allow' and
                                '*' in _as_list(stmt.get('Action', [])) and
                                '*' in _as_list(stmt.get('Resource', []))):
                            findings.append(make_finding(
                                id=f'iam_admin_policy_{policy["PolicyName"]}',
                                title=f'Policy grants full admin access: {policy["PolicyName"]}',
                                title_tr=f'Politika tam yönetici erişimi veriyor: {policy["PolicyName"]}',
                                description='Custom IAM policy allows Action:* on Resource:* — violates least privilege.',
                                description_tr='Özel IAM politikası *:* erişimi sağlıyor — en az ayrıcalık ilkesini ihlal ediyor.',
                                severity='HIGH', status='FAIL',
                                service=SERVICE, resource_id=policy['Arn'],
                                resource_type='AWS::IAM::Policy',
                                frameworks={'CIS': ['1.16'], 'ISO27001': ['A.9.1.1'],
                                            'WAFR': {'pillar': 'Security', 'controls': ['SEC03']}},
                                remediation='Refine the policy to use specific actions and resources.',
                                remediation_tr='Politikayı belirli eylemler ve kaynaklar kullanacak şekilde düzenleyin.',
                            ))
                            break
                except Exception:
                    pass
    except Exception as exc:
        findings.append(not_available('iam_admin_policies', SERVICE, str(exc)))
    return findings


def _check_inactive_users(users):
    """Check for IAM users inactive for 90+ days (no console login or API activity)."""
    findings = []
    try:
        now = datetime.now(timezone.utc)
        for row in users:
            user = row['user']
            last_activity = None

            # Check password_last_used
            pw_last = row.get('password_last_used', 'N/A')
            if pw_last not in ('N/A', 'no_information', 'not_supported'):
                try:
                    dt = datetime.fromisoformat(pw_last.replace('Z', '+00:00'))
                    if last_activity is None or dt > last_activity:
                        last_activity = dt
                except Exception:
                    pass

            # Check access_key last_used_date
            for key_n in ('1', '2'):
                key_active = row.get(f'access_key_{key_n}_active', 'false').lower() == 'true'
                key_last = row.get(f'access_key_{key_n}_last_used_date', 'N/A')
                if key_active and key_last not in ('N/A', 'no_information'):
                    try:
                        dt = datetime.fromisoformat(key_last.replace('Z', '+00:00'))
                        if last_activity is None or dt > last_activity:
                            last_activity = dt
                    except Exception:
                        pass

            if last_activity is not None:
                inactive_days = (now - last_activity).days
                if inactive_days >= 90:
                    findings.append(make_finding(
                        id=f'iam_inactive_user_{user}',
                        title=f'User inactive for {inactive_days} days: {user}',
                        title_tr=f'Kullanıcı {inactive_days} gündür etkin değil: {user}',
                        description=f'IAM user {user} has had no console or API activity for {inactive_days} days. Inactive accounts increase the attack surface.',
                        description_tr=f'IAM kullanıcısı {user}, {inactive_days} gündür konsol veya API etkinliği göstermemiştir. Etkin olmayan hesaplar saldırı yüzeyini artırır.',
                        severity='MEDIUM', status='WARNING',
                        service=SERVICE, resource_id=user,
                        resource_type='AWS::IAM::User',
                        frameworks={'CIS': ['1.12'], 'HIPAA': ['164.308(a)(3)'],
                                    'ISO27001': ['A.9.2.1'],
                                    'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
                        remediation=f'Review IAM user {user}. Disable or remove the account if no longer needed.',
                        remediation_tr=f'IAM kullanıcısı {user} gözden geçirin. Artık gerekli değilse hesabı devre dışı bırakın veya kaldırın.',
                        details={'inactive_days': inactive_days},
                    ))
    except Exception as exc:
        findings.append(not_available('iam_inactive_users', SERVICE, str(exc)))
    return findings


def _check_console_no_mfa(users):
    """Check for users with console access (password enabled) but no MFA."""
    findings = []
    try:
        for row in users:
            user = row['user']
            password_enabled = row.get('password_enabled', 'false').lower() == 'true'
            mfa_active = row.get('mfa_active', 'false').lower() == 'true'

            if password_enabled and not mfa_active:
                findings.append(make_finding(
                    id=f'iam_console_no_mfa_{user}',
                    title=f'Console access without MFA: {user}',
                    title_tr=f'MFA olmadan konsol erişimi: {user}',
                    description=f'IAM user {user} has console password enabled but MFA is not active. Console access without MFA is a significant security risk.',
                    description_tr=f'IAM kullanıcısı {user} konsol şifresi etkin ancak MFA aktif değil. MFA olmadan konsol erişimi önemli bir güvenlik riskidir.',
                    severity='MEDIUM', status='WARNING',
                    service=SERVICE, resource_id=user,
                    resource_type='AWS::IAM::User',
                    frameworks={'CIS': ['1.10'], 'HIPAA': ['164.312(a)(2)(i)'],
                                'ISO27001': ['A.9.4.2'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC02']}},
                    remediation=f'IAM Console → Users → {user} → Security credentials → Assign MFA device, or remove console access if not needed.',
                    remediation_tr=f'IAM Konsol → Kullanıcılar → {user} → Güvenlik kimlik bilgileri → MFA cihazı atayın veya gerekli değilse konsol erişimini kaldırın.',
                ))
    except Exception as exc:
        findings.append(not_available('iam_console_no_mfa', SERVICE, str(exc)))
    return findings


def _check_inline_policies(iam):
    """Check for IAM users with inline policies (should use managed policies instead)."""
    findings = []
    try:
        paginator = iam.get_paginator('list_users')
        for page in paginator.paginate():
            for user_obj in page['Users']:
                username = user_obj['UserName']
                try:
                    inline_resp = iam.list_user_policies(UserName=username)
                    inline_policies = inline_resp.get('PolicyNames', [])
                    if inline_policies:
                        findings.append(make_finding(
                            id=f'iam_inline_policy_{username}',
                            title=f'User has inline policies: {username}',
                            title_tr=f'Kullanıcının satır içi politikaları var: {username}',
                            description=f'IAM user {username} has {len(inline_policies)} inline policy(ies): {", ".join(inline_policies)}. Inline policies are harder to manage and audit than managed policies.',
                            description_tr=f'IAM kullanıcısı {username}, {len(inline_policies)} satır içi politikaya sahip: {", ".join(inline_policies)}. Satır içi politikalar, yönetilen politikalardan daha zor yönetilir ve denetlenir.',
                            severity='MEDIUM', status='WARNING',
                            service=SERVICE, resource_id=username,
                            resource_type='AWS::IAM::User',
                            frameworks={'CIS': ['1.16'], 'HIPAA': ['164.312(a)(1)'],
                                        'ISO27001': ['A.9.1.1', 'A.9.2.3'],
                                        'WAFR': {'pillar': 'Security', 'controls': ['SEC03']}},
                            remediation=f'Convert inline policies for {username} to managed policies. IAM Console → Users → {username} → Permissions → Migrate inline policies to managed.',
                            remediation_tr=f'{username} için satır içi politikaları yönetilen politikalara dönüştürün. IAM Konsol → Kullanıcılar → {username} → İzinler → Satır içi politikaları yönetilen politikalara taşıyın.',
                            details={'inline_policies': inline_policies},
                        ))
                except Exception:
                    pass
    except Exception as exc:
        findings.append(not_available('iam_inline_policies', SERVICE, str(exc)))
    return findings


def _as_list(val):
    if isinstance(val, list):
        return val
    return [val]
