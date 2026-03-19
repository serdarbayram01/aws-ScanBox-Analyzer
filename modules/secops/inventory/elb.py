"""SecOps — ELB / ALB / NLB Checks: HTTPS, access logging, HTTP→HTTPS redirect."""
from .base import make_finding, not_available

SERVICE = 'ELB'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('elb_regions', SERVICE, str(exc))]

    for region in regions:
        elb = session.client('elbv2', region_name=region)
        try:
            paginator = elb.get_paginator('describe_load_balancers')
            for page in paginator.paginate():
                for lb in page.get('LoadBalancers', []):
                    lb_arn  = lb['LoadBalancerArn']
                    lb_name = lb.get('LoadBalancerName', lb_arn)
                    lb_type = lb.get('Type', 'application')  # application | network | gateway
                    scheme  = lb.get('Scheme', '')  # internet-facing | internal

                    # Access logging
                    try:
                        attrs_resp = elb.describe_load_balancer_attributes(LoadBalancerArn=lb_arn)
                        attrs = {a['Key']: a['Value'] for a in attrs_resp.get('Attributes', [])}
                        logging_enabled = attrs.get('access_logs.s3.enabled', 'false') == 'true'
                    except Exception:
                        logging_enabled = False
                        attrs = {}

                    findings.append(make_finding(
                        id=f'elb_access_logs_{lb_name}_{region}',
                        title=f'ELB access logging enabled: {lb_name}',
                        title_tr=f'ELB erişim günlüğü aktif: {lb_name}',
                        description=f'Load balancer {lb_name} in {region} should have access logging enabled to S3.',
                        description_tr=f'{region} bölgesindeki {lb_name} yük dengeleyicisi için S3\'e erişim günlüğü etkinleştirilmelidir.',
                        severity='MEDIUM', status='PASS' if logging_enabled else 'FAIL',
                        service=SERVICE, resource_id=lb_arn,
                        resource_type='AWS::ElasticLoadBalancingV2::LoadBalancer', region=region,
                        frameworks={
                            'CIS': ['3.10'], 'HIPAA': ['164.312(b)'],
                            'ISO27001': ['A.12.4.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']},
                        },
                        remediation=f'ELB Console → {lb_name} → Attributes → Access logs → Enable (specify S3 bucket).',
                        remediation_tr=f'ELB Konsol → {lb_name} → Özellikler → Erişim günlükleri → Etkinleştir (S3 kovası belirtin).',
                    ))

                    # Deletion protection
                    deletion_protection = attrs.get('deletion_protection.enabled', 'false') == 'true'
                    findings.append(make_finding(
                        id=f'elb_deletion_protection_{lb_name}_{region}',
                        title=f'ELB deletion protection enabled: {lb_name}',
                        title_tr=f'ELB silme koruması aktif: {lb_name}',
                        description=f'Load balancer {lb_name} in {region} should have deletion protection enabled.',
                        description_tr=f'{region} bölgesindeki {lb_name} yük dengeleyicisi için silme koruması etkinleştirilmelidir.',
                        severity='LOW', status='PASS' if deletion_protection else 'WARNING',
                        service=SERVICE, resource_id=lb_arn,
                        resource_type='AWS::ElasticLoadBalancingV2::LoadBalancer', region=region,
                        frameworks={'WAFR': {'pillar': 'Reliability', 'controls': ['REL09']}},
                        remediation=f'ELB Console → {lb_name} → Attributes → Deletion protection → Enable.',
                        remediation_tr=f'ELB Konsol → {lb_name} → Özellikler → Silme koruması → Etkinleştir.',
                    ))

                    # HTTPS listener check (only for internet-facing ALBs)
                    if lb_type == 'application' and scheme == 'internet-facing':
                        try:
                            listeners_resp = elb.describe_listeners(LoadBalancerArn=lb_arn)
                            listeners = listeners_resp.get('Listeners', [])
                            has_https = any(l.get('Protocol') == 'HTTPS' for l in listeners)
                            has_http  = any(l.get('Protocol') == 'HTTP'  for l in listeners)

                            if not has_https:
                                findings.append(make_finding(
                                    id=f'elb_https_{lb_name}_{region}',
                                    title=f'ALB has no HTTPS listener: {lb_name}',
                                    title_tr=f'ALB HTTPS dinleyicisi yok: {lb_name}',
                                    description=f'Internet-facing ALB {lb_name} in {region} has no HTTPS listener. All traffic is unencrypted.',
                                    description_tr=f'{region} bölgesindeki internete açık ALB {lb_name} HTTPS dinleyicisine sahip değil. Tüm trafik şifresiz.',
                                    severity='HIGH', status='FAIL',
                                    service=SERVICE, resource_id=lb_arn,
                                    resource_type='AWS::ElasticLoadBalancingV2::LoadBalancer', region=region,
                                    frameworks={
                                        'CIS': ['2.1.2'], 'HIPAA': ['164.312(e)(1)'],
                                        'ISO27001': ['A.14.1.2'],
                                        'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
                                    },
                                    remediation=f'Add an HTTPS listener with an ACM certificate to {lb_name}.',
                                    remediation_tr=f'{lb_name}\'e ACM sertifikasıyla bir HTTPS dinleyicisi ekleyin.',
                                ))
                            elif has_http:
                                # HTTP listener exists — check if it redirects to HTTPS
                                http_listeners = [l for l in listeners if l.get('Protocol') == 'HTTP']
                                redirects = 0
                                for hl in http_listeners:
                                    for action in hl.get('DefaultActions', []):
                                        if action.get('Type') == 'redirect':
                                            redir = action.get('RedirectConfig', {})
                                            if redir.get('Protocol') == 'HTTPS':
                                                redirects += 1
                                if redirects < len(http_listeners):
                                    findings.append(make_finding(
                                        id=f'elb_http_redirect_{lb_name}_{region}',
                                        title=f'ALB HTTP listener missing HTTPS redirect: {lb_name}',
                                        title_tr=f'ALB HTTP dinleyicisinde HTTPS yönlendirmesi eksik: {lb_name}',
                                        description=f'ALB {lb_name} in {region} has an HTTP listener that does not redirect to HTTPS.',
                                        description_tr=f'{region} bölgesindeki ALB {lb_name} HTTPS\'ye yönlendirme yapmayan bir HTTP dinleyicisine sahip.',
                                        severity='MEDIUM', status='FAIL',
                                        service=SERVICE, resource_id=lb_arn,
                                        resource_type='AWS::ElasticLoadBalancingV2::LoadBalancer', region=region,
                                        frameworks={
                                            'CIS': ['2.1.2'], 'HIPAA': ['164.312(e)(1)'],
                                            'ISO27001': ['A.14.1.2'],
                                            'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
                                        },
                                        remediation=f'Configure HTTP listener on {lb_name} to redirect (301) to HTTPS.',
                                        remediation_tr=f'{lb_name} üzerindeki HTTP dinleyicisini HTTPS\'ye (301) yönlendirme yapacak şekilde yapılandırın.',
                                    ))
                        except Exception:
                            pass

        except Exception as exc:
            findings.append(not_available(f'elb_{region}', SERVICE, str(exc)))

    return findings
