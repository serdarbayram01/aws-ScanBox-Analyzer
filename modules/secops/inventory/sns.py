"""SecOps — SNS Checks: KMS encryption, open topic policies."""
import json
from .base import make_finding, not_available

SERVICE = 'SNS'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('sns_regions', SERVICE, str(exc))]

    for region in regions:
        sns = session.client('sns', region_name=region)
        try:
            paginator = sns.get_paginator('list_topics')
            for page in paginator.paginate():
                for topic in page.get('Topics', []):
                    arn = topic['TopicArn']
                    name = arn.split(':')[-1]
                    try:
                        attrs = sns.get_topic_attributes(TopicArn=arn)['Attributes']

                        # KMS encryption
                        kms_id = attrs.get('KmsMasterKeyId', '')
                        findings.append(make_finding(
                            id=f'sns_encryption_{name}_{region}',
                            title=f'SNS topic KMS encryption enabled: {name}',
                            title_tr=f'SNS konusu KMS şifrelemesi aktif: {name}',
                            description=f'SNS topic {name} in {region} should use a KMS key for server-side encryption.',
                            description_tr=f'{region} bölgesindeki SNS konusu {name}, sunucu taraflı şifreleme için KMS anahtarı kullanmalıdır.',
                            severity='MEDIUM', status='PASS' if kms_id else 'FAIL',
                            service=SERVICE, resource_id=arn,
                            resource_type='AWS::SNS::Topic', region=region,
                            frameworks={
                                'HIPAA': ['164.312(a)(2)(iv)'],
                                'ISO27001': ['A.10.1.1'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC08']},
                            },
                            remediation=f'SNS Console → {name} → Edit → Encryption → Enable KMS encryption.',
                            remediation_tr=f'SNS Konsol → {name} → Düzenle → Şifreleme → KMS şifrelemesini etkinleştir.',
                        ))

                        # Open access policy (wildcard principal)
                        policy_str = attrs.get('Policy', '')
                        if policy_str:
                            try:
                                policy = json.loads(policy_str)
                                for stmt in policy.get('Statement', []):
                                    principal = stmt.get('Principal', '')
                                    effect    = stmt.get('Effect', '')
                                    if effect == 'Allow' and (
                                        principal == '*' or principal == {'AWS': '*'}
                                    ):
                                        findings.append(make_finding(
                                            id=f'sns_public_policy_{name}_{region}',
                                            title=f'SNS topic has public access policy: {name}',
                                            title_tr=f'SNS konusu herkese açık erişim politikasına sahip: {name}',
                                            description=f'SNS topic {name} in {region} allows publish/subscribe from any AWS principal.',
                                            description_tr=f'{region} bölgesindeki SNS konusu {name}, herhangi bir AWS müdürünün yayınlamasına/abone olmasına izin veriyor.',
                                            severity='HIGH', status='FAIL',
                                            service=SERVICE, resource_id=arn,
                                            resource_type='AWS::SNS::Topic', region=region,
                                            frameworks={
                                                'CIS': ['1.22'], 'ISO27001': ['A.9.4.1'],
                                                'WAFR': {'pillar': 'Security', 'controls': ['SEC03']},
                                            },
                                            remediation=f'SNS Console → {name} → Access policy → Restrict to specific principals.',
                                            remediation_tr=f'SNS Konsol → {name} → Erişim politikası → Belirli müdürlerle sınırlandırın.',
                                        ))
                                        break
                            except Exception:
                                pass

                    except Exception:
                        pass
        except Exception as exc:
            findings.append(not_available(f'sns_{region}', SERVICE, str(exc)))

    return findings
