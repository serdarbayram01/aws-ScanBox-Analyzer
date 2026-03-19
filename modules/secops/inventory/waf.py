"""SecOps — WAFv2 Checks: logging enabled, rules configured, associated resources."""
from .base import make_finding, not_available

SERVICE = 'WAF'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('waf_regions', SERVICE, str(exc))]

    # WAFv2 has two scopes: REGIONAL (per-region) and CLOUDFRONT (us-east-1 only)
    scopes_by_region = {r: ['REGIONAL'] for r in regions}
    if 'us-east-1' in scopes_by_region:
        scopes_by_region['us-east-1'].append('CLOUDFRONT')

    for region, scopes in scopes_by_region.items():
        waf = session.client('wafv2', region_name=region)
        for scope in scopes:
            try:
                paginator = waf.get_paginator('list_web_acls')
                for page in paginator.paginate(Scope=scope):
                    for acl in page.get('WebACLs', []):
                        acl_id   = acl['Id']
                        acl_name = acl['Name']
                        acl_arn  = acl['ARN']
                        scope_label = f'{scope.lower()}/{region}'

                        try:
                            detail = waf.get_web_acl(Id=acl_id, Name=acl_name, Scope=scope)['WebACL']
                        except Exception:
                            detail = acl

                        rules = detail.get('Rules', [])

                        # No rules → ACL is empty, provides no protection
                        findings.append(make_finding(
                            id=f'waf_rules_{acl_name}_{scope}_{region}',
                            title=f'WAF WebACL has rules configured: {acl_name} ({scope})',
                            title_tr=f'WAF WebACL kurallar yapılandırılmış: {acl_name} ({scope})',
                            description=f'WAF WebACL "{acl_name}" ({scope_label}) has {len(rules)} rule(s). An empty WebACL provides no protection.',
                            description_tr=f'WAF WebACL "{acl_name}" ({scope_label}) {len(rules)} kurala sahip. Boş bir WebACL koruma sağlamaz.',
                            severity='HIGH', status='PASS' if rules else 'FAIL',
                            service=SERVICE, resource_id=acl_arn,
                            resource_type='AWS::WAFv2::WebACL', region=region,
                            frameworks={
                                'CIS': ['2.5'], 'ISO27001': ['A.13.1.3'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC06']},
                            },
                            remediation=f'WAF Console → WebACLs → {acl_name} → Add managed rule groups (e.g. AWSManagedRulesCommonRuleSet).',
                            remediation_tr=f'WAF Konsol → WebACLs → {acl_name} → Yönetilen kural grupları ekle (ör. AWSManagedRulesCommonRuleSet).',
                            details={'rule_count': len(rules)},
                        ))

                        # Logging enabled?
                        try:
                            logging_cfg = waf.get_logging_configuration(ResourceArn=acl_arn)
                            has_logging = True
                        except waf.exceptions.WAFNonexistentItemException:
                            has_logging = False
                        except Exception:
                            has_logging = False

                        findings.append(make_finding(
                            id=f'waf_logging_{acl_name}_{scope}_{region}',
                            title=f'WAF WebACL logging enabled: {acl_name} ({scope})',
                            title_tr=f'WAF WebACL günlükleme aktif: {acl_name} ({scope})',
                            description=f'WAF WebACL "{acl_name}" ({scope_label}) should have logging enabled to track blocked requests.',
                            description_tr=f'WAF WebACL "{acl_name}" ({scope_label}), engellenen istekleri izlemek için günlükleme etkinleştirilmelidir.',
                            severity='MEDIUM', status='PASS' if has_logging else 'FAIL',
                            service=SERVICE, resource_id=acl_arn,
                            resource_type='AWS::WAFv2::WebACL', region=region,
                            frameworks={
                                'CIS': ['3.10'], 'HIPAA': ['164.312(b)'],
                                'ISO27001': ['A.12.4.1'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC04']},
                            },
                            remediation=f'WAF Console → WebACLs → {acl_name} → Logging and metrics → Enable logging (Kinesis Firehose or S3).',
                            remediation_tr=f'WAF Konsol → WebACLs → {acl_name} → Günlükleme ve metrikler → Günlüklemeyi etkinleştir (Kinesis Firehose veya S3).',
                        ))

            except Exception as exc:
                findings.append(not_available(f'waf_{scope}_{region}', SERVICE, str(exc)))

    return findings
