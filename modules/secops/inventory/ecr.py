"""SecOps — ECR Checks: image scan on push, lifecycle policy, public repos."""
from .base import make_finding, not_available

SERVICE = 'ECR'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('ecr_regions', SERVICE, str(exc))]

    for region in regions:
        ecr = session.client('ecr', region_name=region)
        try:
            paginator = ecr.get_paginator('describe_repositories')
            for page in paginator.paginate():
                for repo in page.get('repositories', []):
                    repo_name = repo['repositoryName']
                    repo_arn  = repo['repositoryArn']
                    visibility = repo.get('imageTagMutability', 'MUTABLE')

                    # Image scanning on push
                    scan_cfg     = repo.get('imageScanningConfiguration', {})
                    scan_on_push = scan_cfg.get('scanOnPush', False)
                    findings.append(make_finding(
                        id=f'ecr_scan_on_push_{repo_name}_{region}',
                        title=f'ECR image scan on push enabled: {repo_name}',
                        title_tr=f'ECR görüntü taraması push\'ta etkin: {repo_name}',
                        description=f'ECR repository {repo_name} in {region} should have scan on push enabled to detect vulnerabilities in container images.',
                        description_tr=f'{region} bölgesindeki ECR deposu {repo_name}, container görüntülerindeki güvenlik açıklarını tespit etmek için push taraması etkinleştirilmelidir.',
                        severity='HIGH', status='PASS' if scan_on_push else 'FAIL',
                        service=SERVICE, resource_id=repo_arn,
                        resource_type='AWS::ECR::Repository', region=region,
                        frameworks={
                            'CIS': ['5.1'], 'ISO27001': ['A.12.6.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC06']},
                        },
                        remediation=f'ECR Console → Repositories → {repo_name} → Edit → Scan on push → Enabled.',
                        remediation_tr=f'ECR Konsol → Depolar → {repo_name} → Düzenle → Push\'ta tara → Etkin.',
                    ))

                    # Image tag immutability
                    findings.append(make_finding(
                        id=f'ecr_immutable_tags_{repo_name}_{region}',
                        title=f'ECR image tag immutability enabled: {repo_name}',
                        title_tr=f'ECR görüntü etiketi değişmezliği etkin: {repo_name}',
                        description=f'ECR repository {repo_name} in {region} has {visibility} tags. Immutable tags prevent image tag overwriting.',
                        description_tr=f'{region} bölgesindeki ECR deposu {repo_name}, {visibility} etiketlere sahip. Değişmez etiketler görüntü etiketi üzerine yazmayı önler.',
                        severity='MEDIUM', status='PASS' if visibility == 'IMMUTABLE' else 'FAIL',
                        service=SERVICE, resource_id=repo_arn,
                        resource_type='AWS::ECR::Repository', region=region,
                        frameworks={
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC06']},
                        },
                        remediation=f'ECR Console → Repositories → {repo_name} → Edit → Tag immutability → Enabled.',
                        remediation_tr=f'ECR Konsol → Depolar → {repo_name} → Düzenle → Etiket değişmezliği → Etkin.',
                    ))

                    # Lifecycle policy
                    try:
                        ecr.get_lifecycle_policy(repositoryName=repo_name)
                        has_lifecycle = True
                    except ecr.exceptions.LifecyclePolicyNotFoundException:
                        has_lifecycle = False
                    except Exception:
                        has_lifecycle = False

                    findings.append(make_finding(
                        id=f'ecr_lifecycle_{repo_name}_{region}',
                        title=f'ECR repository has lifecycle policy: {repo_name}',
                        title_tr=f'ECR deposunun yaşam döngüsü politikası var: {repo_name}',
                        description=f'ECR repository {repo_name} in {region} should have a lifecycle policy to remove old/unused images and reduce costs.',
                        description_tr=f'{region} bölgesindeki ECR deposu {repo_name}, eski/kullanılmayan görüntüleri kaldırmak ve maliyetleri azaltmak için yaşam döngüsü politikasına sahip olmalıdır.',
                        severity='LOW', status='PASS' if has_lifecycle else 'FAIL',
                        service=SERVICE, resource_id=repo_arn,
                        resource_type='AWS::ECR::Repository', region=region,
                        frameworks={
                            'WAFR': {'pillar': 'Cost Optimization', 'controls': ['COST07']},
                        },
                        remediation=f'ECR Console → Repositories → {repo_name} → Lifecycle policy → Create a policy to expire untagged images after 30 days.',
                        remediation_tr=f'ECR Konsol → Depolar → {repo_name} → Yaşam döngüsü politikası → Etiketsiz görüntüleri 30 gün sonra sona erdirecek bir politika oluşturun.',
                    ))

        except Exception as exc:
            findings.append(not_available(f'ecr_{region}', SERVICE, str(exc)))

    # --- Public ECR (global) ---
    try:
        ecr_public = session.client('ecr-public', region_name='us-east-1')
        pub_paginator = ecr_public.get_paginator('describe_repositories')
        for page in pub_paginator.paginate():
            for repo in page.get('repositories', []):
                repo_name = repo['repositoryName']
                repo_arn  = repo['repositoryArn']
                findings.append(make_finding(
                    id=f'ecr_public_repo_{repo_name}',
                    title=f'ECR public repository exists: {repo_name}',
                    title_tr=f'ECR genel deposu mevcut: {repo_name}',
                    description=f'Public ECR repository {repo_name} is publicly accessible. Ensure it intentionally contains public images.',
                    description_tr=f'Genel ECR deposu {repo_name} herkese açık. Kasıtlı olarak genel görüntüler içerdiğinden emin olun.',
                    severity='MEDIUM', status='WARNING',
                    service=SERVICE, resource_id=repo_arn,
                    resource_type='AWS::ECR::PublicRepository', region='us-east-1',
                    frameworks={
                        'ISO27001': ['A.9.4.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC06']},
                    },
                    remediation='Verify that public ECR repository contents are intentional and do not contain sensitive images.',
                    remediation_tr='Genel ECR deposu içeriklerinin kasıtlı olduğunu ve hassas görüntüler içermediğini doğrulayın.',
                ))
    except Exception:
        pass

    return findings
