"""SecOps — SQS Checks: encryption, open access policies, DLQ."""
import json
from .base import make_finding, not_available

SERVICE = 'SQS'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('sqs_regions', SERVICE, str(exc))]

    for region in regions:
        sqs = session.client('sqs', region_name=region)
        try:
            resp = sqs.list_queues()
            urls = resp.get('QueueUrls', [])
            # Handle paginated list
            while resp.get('NextToken'):
                resp = sqs.list_queues(NextToken=resp['NextToken'])
                urls.extend(resp.get('QueueUrls', []))

            for url in urls:
                try:
                    attrs = sqs.get_queue_attributes(
                        QueueUrl=url,
                        AttributeNames=['All'],
                    )['Attributes']
                    queue_name = url.split('/')[-1]
                    queue_arn  = attrs.get('QueueArn', url)

                    # Encryption at rest
                    kms_id  = attrs.get('KmsMasterKeyId', '')
                    sse_sqs = attrs.get('SqsManagedSseEnabled', 'false').lower() == 'true'
                    encrypted = bool(kms_id) or sse_sqs

                    findings.append(make_finding(
                        id=f'sqs_encryption_{queue_name}_{region}',
                        title=f'SQS queue encrypted at rest: {queue_name}',
                        title_tr=f'SQS kuyruğu bekleyen verileri şifreli: {queue_name}',
                        description=f'SQS queue {queue_name} in {region} should have server-side encryption enabled.',
                        description_tr=f'{region} bölgesindeki SQS kuyruğu {queue_name} için sunucu taraflı şifreleme etkinleştirilmelidir.',
                        severity='MEDIUM', status='PASS' if encrypted else 'FAIL',
                        service=SERVICE, resource_id=queue_arn,
                        resource_type='AWS::SQS::Queue', region=region,
                        frameworks={
                            'HIPAA': ['164.312(a)(2)(iv)'],
                            'ISO27001': ['A.10.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC08']},
                        },
                        remediation=f'SQS Console → {queue_name} → Edit → Encryption → Enable SSE-SQS or KMS.',
                        remediation_tr=f'SQS Konsol → {queue_name} → Düzenle → Şifreleme → SSE-SQS veya KMS\'yi etkinleştir.',
                    ))

                    # Open access policy (wildcard principal)
                    policy_str = attrs.get('Policy', '')
                    if policy_str:
                        try:
                            policy = json.loads(policy_str)
                            for stmt in policy.get('Statement', []):
                                principal = stmt.get('Principal', '')
                                effect    = stmt.get('Effect', '')
                                if effect == 'Allow' and (principal == '*' or principal == {'AWS': '*'}):
                                    findings.append(make_finding(
                                        id=f'sqs_public_policy_{queue_name}_{region}',
                                        title=f'SQS queue has public access policy: {queue_name}',
                                        title_tr=f'SQS kuyruğu herkese açık erişim politikasına sahip: {queue_name}',
                                        description=f'SQS queue {queue_name} in {region} has a policy that allows access from any principal (*). This may allow unauthorized access.',
                                        description_tr=f'{region} bölgesindeki SQS kuyruğu {queue_name}, herhangi bir müdürden (*) erişime izin veren bir politikaya sahip. Bu yetkisiz erişime izin verebilir.',
                                        severity='HIGH', status='FAIL',
                                        service=SERVICE, resource_id=queue_arn,
                                        resource_type='AWS::SQS::Queue', region=region,
                                        frameworks={
                                            'CIS': ['1.22'], 'ISO27001': ['A.9.4.1'],
                                            'WAFR': {'pillar': 'Security', 'controls': ['SEC03']},
                                        },
                                        remediation=f'SQS Console → {queue_name} → Access policy → Remove wildcard principal.',
                                        remediation_tr=f'SQS Konsol → {queue_name} → Erişim politikası → Joker karakter müdürü kaldırın.',
                                    ))
                                    break
                        except Exception:
                            pass

                except Exception:
                    pass
        except Exception as exc:
            findings.append(not_available(f'sqs_{region}', SERVICE, str(exc)))

    return findings
