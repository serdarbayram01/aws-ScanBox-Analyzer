"""SecOps — ECS Checks: privileged containers, secrets in env, Container Insights."""
from .base import make_finding, not_available

SERVICE = 'ECS'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('ecs_regions', SERVICE, str(exc))]

    for region in regions:
        ecs = session.client('ecs', region_name=region)

        # — Clusters: Container Insights —
        try:
            cluster_arns = []
            paginator = ecs.get_paginator('list_clusters')
            for page in paginator.paginate():
                cluster_arns.extend(page.get('clusterArns', []))

            for batch_start in range(0, len(cluster_arns), 100):
                batch = cluster_arns[batch_start:batch_start + 100]
                clusters = ecs.describe_clusters(
                    clusters=batch,
                    include=['SETTINGS'],
                )['clusters']
                for cluster in clusters:
                    cname = cluster.get('clusterName', cluster.get('clusterArn', 'unknown'))
                    carn  = cluster.get('clusterArn', cname)
                    settings = {s['name']: s['value'] for s in cluster.get('settings', [])}
                    insights_on = settings.get('containerInsights', 'disabled') == 'enabled'
                    findings.append(make_finding(
                        id=f'ecs_insights_{cname}_{region}',
                        title=f'ECS Container Insights enabled: {cname}',
                        title_tr=f'ECS Container Insights aktif: {cname}',
                        description=f'ECS cluster {cname} in {region} should have Container Insights enabled for monitoring.',
                        description_tr=f'{region} bölgesindeki ECS kümesi {cname} için izleme amacıyla Container Insights etkinleştirilmelidir.',
                        severity='LOW', status='PASS' if insights_on else 'FAIL',
                        service=SERVICE, resource_id=carn,
                        resource_type='AWS::ECS::Cluster', region=region,
                        frameworks={'WAFR': {'pillar': 'Operational Excellence', 'controls': ['OPS07']}},
                        remediation=f'ECS Console → {cname} → Update cluster → Container Insights → Enabled.',
                        remediation_tr=f'ECS Konsol → {cname} → Kümeyi güncelle → Container Insights → Etkinleştir.',
                    ))
        except Exception as exc:
            findings.append(not_available(f'ecs_clusters_{region}', SERVICE, str(exc)))

        # — Task Definitions: privileged containers & secrets in env vars —
        try:
            td_arns = []
            paginator = ecs.get_paginator('list_task_definitions')
            for page in paginator.paginate(status='ACTIVE'):
                td_arns.extend(page.get('taskDefinitionArns', []))

            # Deduplicate to only latest revision per family
            families_seen = set()
            unique_arns = []
            for arn in reversed(td_arns):
                family = ':'.join(arn.split(':')[:-1])
                if family not in families_seen:
                    families_seen.add(family)
                    unique_arns.append(arn)

            for td_arn in unique_arns[:200]:  # cap at 200 task defs
                try:
                    td = ecs.describe_task_definition(taskDefinition=td_arn)['taskDefinition']
                    family = td.get('family', td_arn)

                    for container in td.get('containerDefinitions', []):
                        cname = container.get('name', 'unknown')

                        # Privileged mode
                        if container.get('privileged', False):
                            findings.append(make_finding(
                                id=f'ecs_privileged_{family}_{cname}_{region}',
                                title=f'ECS task definition has privileged container: {family}/{cname}',
                                title_tr=f'ECS görev tanımında ayrıcalıklı container: {family}/{cname}',
                                description=f'Container {cname} in task definition {family} runs in privileged mode, giving it root-level access to the host.',
                                description_tr=f'{family} görev tanımındaki {cname} container\'ı ayrıcalıklı modda çalışıyor; bu ona ana sunucuya kök seviyesinde erişim sağlıyor.',
                                severity='HIGH', status='FAIL',
                                service=SERVICE, resource_id=td_arn,
                                resource_type='AWS::ECS::TaskDefinition', region=region,
                                frameworks={
                                    'CIS': ['5.4'], 'ISO27001': ['A.12.6.1'],
                                    'WAFR': {'pillar': 'Security', 'controls': ['SEC05']},
                                },
                                remediation=f'Remove privileged:true from container {cname} in task definition {family}.',
                                remediation_tr=f'{family} görev tanımındaki {cname} container\'ından privileged:true ayarını kaldırın.',
                            ))

                        # Secrets / passwords in plain environment variables
                        suspect_keys = {'password', 'secret', 'key', 'token', 'api_key', 'apikey',
                                        'passwd', 'credentials', 'private_key', 'access_key'}
                        for env in container.get('environment', []):
                            env_name = env.get('name', '').lower()
                            if any(s in env_name for s in suspect_keys):
                                findings.append(make_finding(
                                    id=f'ecs_env_secret_{family}_{cname}_{env["name"]}_{region}',
                                    title=f'ECS task definition has potential secret in env var: {family}/{cname}/{env["name"]}',
                                    title_tr=f'ECS görev tanımında env değişkeninde potansiyel gizli bilgi: {family}/{cname}/{env["name"]}',
                                    description=f'Container {cname} in {family} has an environment variable "{env["name"]}" that may contain a secret. Use Secrets Manager or SSM Parameter Store instead.',
                                    description_tr=f'{family} içindeki {cname} container\'ında gizli bilgi içerebilecek "{env["name"]}" adlı bir ortam değişkeni var. Bunun yerine Secrets Manager veya SSM Parameter Store kullanın.',
                                    severity='HIGH', status='FAIL',
                                    service=SERVICE, resource_id=td_arn,
                                    resource_type='AWS::ECS::TaskDefinition', region=region,
                                    frameworks={
                                        'CIS': ['5.4'], 'HIPAA': ['164.312(a)(2)(iv)'],
                                        'ISO27001': ['A.9.4.3'],
                                        'WAFR': {'pillar': 'Security', 'controls': ['SEC07']},
                                    },
                                    remediation=f'Replace plain env var {env["name"]} with secrets from AWS Secrets Manager or SSM Parameter Store.',
                                    remediation_tr=f'{env["name"]} düz ortam değişkenini AWS Secrets Manager veya SSM Parameter Store\'dan gizli bilgilerle değiştirin.',
                                ))
                except Exception:
                    pass
        except Exception as exc:
            findings.append(not_available(f'ecs_taskdefs_{region}', SERVICE, str(exc)))

    return findings
