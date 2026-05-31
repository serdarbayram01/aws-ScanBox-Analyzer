"""SecOps — Lambda Checks: public URLs, deprecated runtimes, env secret hints."""
import re
from .base import make_finding, not_available
SERVICE = 'Lambda'

DEPRECATED_RUNTIMES = {'python2.7', 'python3.6', 'python3.7', 'nodejs10.x', 'nodejs12.x',
                        'ruby2.5', 'java8', 'dotnetcore2.1', 'dotnetcore3.1', 'go1.x'}
SECRET_HINTS = re.compile(r'(password|secret|key|token|api_key|apikey|passwd|pwd|credential)',
                           re.IGNORECASE)

def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('lambda_regions', SERVICE, str(exc))]

    for region in regions:
        lmb = session.client('lambda', region_name=region)
        try:
            paginator = lmb.get_paginator('list_functions')
            for page in paginator.paginate():
                for fn in page['Functions']:
                    findings += _check_function(lmb, fn, region)
        except Exception as exc:
            findings.append(not_available(f'lambda_{region}', SERVICE, str(exc)))
    return findings


def _check_function(lmb, fn, region):
    findings = []
    name    = fn['FunctionName']
    arn     = fn['FunctionArn']
    runtime = fn.get('Runtime', '')

    # Deprecated runtime
    if runtime in DEPRECATED_RUNTIMES:
        findings.append(make_finding(
            id=f'lambda_runtime_{name}_{region}',
            title=f'Lambda deprecated runtime: {name}',
            title_tr=f'Lambda eski runtime: {name}',
            description=f'Function {name} uses deprecated runtime {runtime}.',
            description_tr=f'{name} fonksiyonu kullanımdan kaldırılmış {runtime} runtime\'ını kullanıyor.',
            severity='HIGH', status='FAIL',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::Lambda::Function', region=region,
            frameworks={
                        'SOC2': ['CC7.1', 'CC8.1'],'CIS': ['2.4'], 'HIPAA': ['164.312(a)(1)'],
                        'ISO27001': ['A.12.6.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
            remediation=f'Update function {name} to a supported runtime.',
            remediation_tr=f'{name} fonksiyonunu desteklenen bir runtime\'a güncelleyin.',
            details={'runtime': runtime},
        ))

    # Env variable secret hints
    env_vars = fn.get('Environment', {}).get('Variables', {})
    for key in env_vars:
        if SECRET_HINTS.search(key):
            findings.append(make_finding(
                id=f'lambda_env_secret_{name}_{key}_{region}',
                title=f'Lambda env variable may contain secret: {name}/{key}',
                title_tr=f'Lambda ortam değişkeni gizli bilgi içerebilir: {name}/{key}',
                description=f'Function {name} has an env variable named "{key}" that may contain a secret.',
                description_tr=f'{name} fonksiyonunda "{key}" adlı ortam değişkeni gizli bilgi içerebilir.',
                severity='HIGH', status='WARNING',
                service=SERVICE, resource_id=arn,
                resource_type='AWS::Lambda::Function', region=region,
                frameworks={
                            'SOC2': ['C1.2'],'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.9.4.3'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
                remediation='Move secrets to AWS Secrets Manager or SSM Parameter Store.',
                remediation_tr='Gizli bilgileri AWS Secrets Manager veya SSM Parameter Store\'a taşıyın.',
                details={'variable': key},
            ))

    # Public function URL
    try:
        url_config = lmb.get_function_url_config(FunctionName=name)
        auth = url_config.get('AuthType', 'NONE')
        if auth == 'NONE':
            findings.append(make_finding(
                id=f'lambda_public_url_{name}_{region}',
                title=f'Lambda function URL is public (no auth): {name}',
                title_tr=f'Lambda fonksiyon URL\'si herkese açık (kimlik doğrulama yok): {name}',
                description=f'Function {name} has a public URL with no authentication.',
                description_tr=f'{name} fonksiyonunun kimlik doğrulaması olmayan genel URL\'si var.',
                severity='HIGH', status='FAIL',
                service=SERVICE, resource_id=arn,
                resource_type='AWS::Lambda::Function', region=region,
                frameworks={
                            'SOC2': ['CC6.6'],'HIPAA': ['164.312(a)(1)'], 'ISO27001': ['A.9.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                remediation='Set function URL auth type to AWS_IAM or remove the URL.',
                remediation_tr='Fonksiyon URL kimlik doğrulama türünü AWS_IAM olarak ayarlayın veya URL\'yi kaldırın.',
            ))
    except lmb.exceptions.ResourceNotFoundException:
        pass
    except Exception:
        pass

    # Reserved concurrency — prevents resource starvation / runaway invocations
    try:
        cc = lmb.get_function_concurrency(FunctionName=name)
        reserved = cc.get('ReservedConcurrentExecutions')
        # None = unreserved (default); 0 = throttled completely (intentional kill switch)
        has_reserved = reserved is not None
    except Exception:
        has_reserved = None  # API may not be permitted on every function
    if has_reserved is not None:
        findings.append(make_finding(
            id=f'lambda_reserved_concurrency_{name}_{region}',
            title=f'Lambda reserved concurrency configured: {name}',
            title_tr=f'Lambda ayrılmış eşzamanlılık yapılandırılmış: {name}',
            description=(
                f'Function {name} {"has" if has_reserved else "does not have"} reserved '
                f'concurrency configured. Without a limit, a runaway function can exhaust '
                f'the account-wide concurrency pool and cause cascading failures.'
            ),
            description_tr=(
                f'{name} fonksiyonu için ayrılmış eşzamanlılık '
                f'{"yapılandırılmış" if has_reserved else "yapılandırılmamış"}. '
                f'Limit olmadan, kontrolden çıkmış bir fonksiyon hesap genelindeki eşzamanlılık '
                f'havuzunu tüketebilir ve zincirleme arızalara neden olabilir.'
            ),
            severity='LOW', status='PASS' if has_reserved else 'WARNING',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::Lambda::Function', region=region,
            frameworks={
                'SOC2':     ['CC7.2'],
                'ISO27001': ['A.17.2.1'],
                'WAFR':     {'pillar': 'Reliability', 'controls': ['REL07']},
            },
            remediation=(
                f'Lambda → {name} → Configuration → Concurrency → Reserve concurrency. '
                f'Set to a value that protects the account-level limit (default 1000).'
            ),
            remediation_tr=(
                f'Lambda → {name} → Yapılandırma → Eşzamanlılık → Eşzamanlılığı ayır. '
                f'Hesap düzeyindeki limiti (varsayılan 1000) koruyacak bir değere ayarlayın.'
            ),
            details={'reserved_concurrent_executions': reserved},
        ))

    # Dead-letter queue — async invocation failure capture
    dlq = fn.get('DeadLetterConfig', {}).get('TargetArn')
    findings.append(make_finding(
        id=f'lambda_dlq_{name}_{region}',
        title=f'Lambda dead-letter queue configured: {name}',
        title_tr=f'Lambda hata kuyruğu (DLQ) yapılandırılmış: {name}',
        description=(
            f'Function {name} {"has" if dlq else "does not have"} a dead-letter queue. '
            f'Without a DLQ, failed async invocations are dropped after retry attempts — '
            f'losing visibility into errors and stalling event-driven pipelines.'
        ),
        description_tr=(
            f'{name} fonksiyonunda hata kuyruğu (DLQ) '
            f'{"var" if dlq else "yok"}. '
            f'DLQ olmadan, yeniden deneme girişimlerinden sonra başarısız async çağrılar düşürülür — '
            f'hatalar üzerindeki görünürlük kaybedilir ve olay güdümlü pipeline\'lar tıkanır.'
        ),
        severity='LOW', status='PASS' if dlq else 'WARNING',
        service=SERVICE, resource_id=arn,
        resource_type='AWS::Lambda::Function', region=region,
        frameworks={
            'SOC2':     ['CC7.3'],
            'ISO27001': ['A.16.1.4'],
            'WAFR':     {'pillar': 'Reliability', 'controls': ['REL05']},
        },
        remediation=(
            f'Lambda → {name} → Configuration → Async invocation → DLQ → SQS or SNS target. '
            f'Subscribe alerting on the DLQ depth metric.'
        ),
        remediation_tr=(
            f'Lambda → {name} → Yapılandırma → Async çağrı → DLQ → SQS veya SNS hedef. '
            f'DLQ derinlik metriğine uyarı abonelik kurun.'
        ),
        details={'dlq_arn': dlq or ''},
    ))

    return findings
