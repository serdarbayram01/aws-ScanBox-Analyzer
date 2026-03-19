"""SecOps — CloudFront Checks: HTTPS, TLS version, access logging, WAF, origin protocol."""
from .base import make_finding, not_available

SERVICE = 'CloudFront'


def run_checks(session, exclude_defaults=False, regions=None):
    """CloudFront is a global service — called once from us-east-1."""
    findings = []
    try:
        cf = session.client('cloudfront', region_name='us-east-1')
        paginator = cf.get_paginator('list_distributions')
        distributions = []
        for page in paginator.paginate():
            dl = page.get('DistributionList', {})
            distributions.extend(dl.get('Items', []))
    except Exception as exc:
        return [not_available('cloudfront_list', SERVICE, str(exc))]

    for dist in distributions:
        dist_id  = dist.get('Id', 'unknown')
        domain   = dist.get('DomainName', dist_id)
        aliases  = dist.get('Aliases', {}).get('Items', [domain])
        name     = aliases[0] if aliases else domain
        dist_arn = f'arn:aws:cloudfront:::{dist_id}'

        default_behavior = dist.get('DefaultCacheBehavior', {})

        # --- Viewer protocol policy (HTTPS) ---
        viewer_protocol = default_behavior.get('ViewerProtocolPolicy', 'allow-all')
        https_enforced  = viewer_protocol in ('https-only', 'redirect-to-https')
        findings.append(make_finding(
            id=f'cf_https_{dist_id}',
            title=f'CloudFront enforces HTTPS: {name}',
            title_tr=f'CloudFront HTTPS zorundakılıyor: {name}',
            description=(
                f'CloudFront distribution {dist_id} ({name}) ViewerProtocolPolicy is '
                f'"{viewer_protocol}". Should be "redirect-to-https" or "https-only".'
            ),
            description_tr=(
                f'CloudFront dağıtımı {dist_id} ({name}) ViewerProtocolPolicy değeri '
                f'"{viewer_protocol}". "redirect-to-https" veya "https-only" olmalıdır.'
            ),
            severity='HIGH', status='PASS' if https_enforced else 'FAIL',
            service=SERVICE, resource_id=dist_arn,
            resource_type='AWS::CloudFront::Distribution', region='global',
            frameworks={
                'CIS': ['2.1.2'], 'HIPAA': ['164.312(e)(1)'],
                'ISO27001': ['A.14.1.2'],
                'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
            },
            remediation=f'CloudFront Console → {dist_id} → Behaviors → Edit → Viewer protocol policy → Redirect HTTP to HTTPS.',
            remediation_tr=f'CloudFront Konsol → {dist_id} → Davranışlar → Düzenle → Görüntüleyici protokol politikası → HTTP\'yi HTTPS\'ye yönlendir.',
            details={'viewer_protocol_policy': viewer_protocol},
        ))

        # --- Minimum TLS version ---
        cert = dist.get('ViewerCertificate', {})
        min_tls = cert.get('MinimumProtocolVersion', 'TLSv1')
        good_tls = min_tls in ('TLSv1.2_2021', 'TLSv1.2_2019', 'TLSv1.2_2018')
        findings.append(make_finding(
            id=f'cf_tls_{dist_id}',
            title=f'CloudFront minimum TLS 1.2: {name}',
            title_tr=f'CloudFront minimum TLS 1.2: {name}',
            description=(
                f'CloudFront distribution {dist_id} ({name}) minimum TLS version is "{min_tls}". '
                f'Should be TLSv1.2_2021 or newer to avoid known TLS vulnerabilities.'
            ),
            description_tr=(
                f'CloudFront dağıtımı {dist_id} ({name}) minimum TLS sürümü "{min_tls}". '
                f'Bilinen TLS açıklarından kaçınmak için TLSv1.2_2021 veya daha yeni olmalıdır.'
            ),
            severity='MEDIUM', status='PASS' if good_tls else 'FAIL',
            service=SERVICE, resource_id=dist_arn,
            resource_type='AWS::CloudFront::Distribution', region='global',
            frameworks={
                'CIS': ['2.1.3'], 'HIPAA': ['164.312(e)(2)(ii)'],
                'ISO27001': ['A.14.1.3'],
                'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
            },
            remediation=f'CloudFront Console → {dist_id} → General → Edit → Security policy → TLSv1.2_2021.',
            remediation_tr=f'CloudFront Konsol → {dist_id} → Genel → Düzenle → Güvenlik politikası → TLSv1.2_2021.',
            details={'min_tls': min_tls},
        ))

        # --- WAF WebACL ---
        waf_id    = dist.get('WebACLId', '')
        has_waf   = bool(waf_id)
        findings.append(make_finding(
            id=f'cf_waf_{dist_id}',
            title=f'CloudFront distribution has WAF WebACL: {name}',
            title_tr=f'CloudFront dağıtımında WAF WebACL var: {name}',
            description=(
                f'CloudFront distribution {dist_id} ({name}) should have a WAF WebACL '
                f'to protect against common web exploits (SQLi, XSS, bot attacks).'
            ),
            description_tr=(
                f'CloudFront dağıtımı {dist_id} ({name}), yaygın web açıklarına (SQLi, XSS, bot saldırıları) '
                f'karşı koruma sağlamak için bir WAF WebACL\'ye sahip olmalıdır.'
            ),
            severity='HIGH', status='PASS' if has_waf else 'FAIL',
            service=SERVICE, resource_id=dist_arn,
            resource_type='AWS::CloudFront::Distribution', region='global',
            frameworks={
                'CIS': ['2.1.4'], 'ISO27001': ['A.13.1.3'],
                'WAFR': {'pillar': 'Security', 'controls': ['SEC06']},
            },
            remediation=f'CloudFront Console → {dist_id} → General → Edit → AWS WAF web ACL → Associate a WebACL.',
            remediation_tr=f'CloudFront Konsol → {dist_id} → Genel → Düzenle → AWS WAF web ACL → Bir WebACL ilişkilendirin.',
        ))

        # --- Access logging ---
        logging_cfg = dist.get('Logging', {})
        logging_on  = bool(logging_cfg.get('Enabled', False)) or bool(logging_cfg.get('Bucket', ''))
        findings.append(make_finding(
            id=f'cf_logging_{dist_id}',
            title=f'CloudFront access logging enabled: {name}',
            title_tr=f'CloudFront erişim günlüğü aktif: {name}',
            description=(
                f'CloudFront distribution {dist_id} ({name}) should have access logging enabled '
                f'to track viewer requests for security analysis.'
            ),
            description_tr=(
                f'CloudFront dağıtımı {dist_id} ({name}), güvenlik analizi için görüntüleyici isteklerini '
                f'izlemek amacıyla erişim günlüğü etkinleştirilmelidir.'
            ),
            severity='MEDIUM', status='PASS' if logging_on else 'FAIL',
            service=SERVICE, resource_id=dist_arn,
            resource_type='AWS::CloudFront::Distribution', region='global',
            frameworks={
                'CIS': ['3.10'], 'HIPAA': ['164.312(b)'],
                'ISO27001': ['A.12.4.1'],
                'WAFR': {'pillar': 'Security', 'controls': ['SEC04']},
            },
            remediation=f'CloudFront Console → {dist_id} → General → Edit → Standard logging → On (specify S3 bucket).',
            remediation_tr=f'CloudFront Konsol → {dist_id} → Genel → Düzenle → Standart günlükleme → Açık (S3 kovası belirtin).',
        ))

        # --- Custom origin protocol (HTTP-only origins are insecure) ---
        for origin in dist.get('Origins', {}).get('Items', []):
            origin_id      = origin.get('Id', 'unknown')
            custom_origin  = origin.get('CustomOriginConfig', {})
            origin_protocol = custom_origin.get('OriginProtocolPolicy', '')
            if origin_protocol == 'http-only':
                findings.append(make_finding(
                    id=f'cf_origin_protocol_{dist_id}_{origin_id}',
                    title=f'CloudFront origin uses HTTP-only: {name}/{origin_id}',
                    title_tr=f'CloudFront kaynağı yalnızca HTTP kullanıyor: {name}/{origin_id}',
                    description=(
                        f'CloudFront distribution {dist_id} origin "{origin_id}" uses HTTP-only protocol. '
                        f'Traffic between CloudFront and the origin is unencrypted.'
                    ),
                    description_tr=(
                        f'CloudFront dağıtımı {dist_id} kaynağı "{origin_id}" yalnızca HTTP protokolü kullanıyor. '
                        f'CloudFront ile kaynak arasındaki trafik şifresiz.'
                    ),
                    severity='HIGH', status='FAIL',
                    service=SERVICE, resource_id=dist_arn,
                    resource_type='AWS::CloudFront::Distribution', region='global',
                    frameworks={
                        'CIS': ['2.1.2'], 'HIPAA': ['164.312(e)(1)'],
                        'ISO27001': ['A.14.1.2'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC09']},
                    },
                    remediation=f'Set origin protocol policy for "{origin_id}" to "https-only" or "match-viewer".',
                    remediation_tr=f'"{origin_id}" kaynağının protokol politikasını "https-only" veya "match-viewer" olarak ayarlayın.',
                    details={'origin_protocol': origin_protocol},
                ))

    return findings
