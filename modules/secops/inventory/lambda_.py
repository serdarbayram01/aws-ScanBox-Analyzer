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
            frameworks={'CIS': ['2.4'], 'HIPAA': ['164.312(a)(1)'],
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
                frameworks={'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.9.4.3'],
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
                frameworks={'HIPAA': ['164.312(a)(1)'], 'ISO27001': ['A.9.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                remediation='Set function URL auth type to AWS_IAM or remove the URL.',
                remediation_tr='Fonksiyon URL kimlik doğrulama türünü AWS_IAM olarak ayarlayın veya URL\'yi kaldırın.',
            ))
    except lmb.exceptions.ResourceNotFoundException:
        pass
    except Exception:
        pass

    return findings
