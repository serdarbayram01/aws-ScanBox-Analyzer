"""SecOps — Amazon OpenSearch Service Checks: at-rest encryption,
node-to-node encryption, enforce HTTPS, VPC endpoint (no public access),
fine-grained access control, audit log publishing."""

from .base import make_finding, not_available

SERVICE = 'OpenSearch'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('opensearch_regions', SERVICE, str(exc))]

    for region in regions:
        try:
            findings += _check_region(session, region)
        except Exception as exc:
            findings.append(not_available(f'opensearch_{region}', SERVICE, str(exc)))
    return findings


def _check_region(session, region):
    findings = []
    try:
        es = session.client('opensearch', region_name=region)
        domain_names = [d['DomainName']
                        for d in es.list_domain_names().get('DomainNames', []) or []]
    except Exception as exc:
        if 'AccessDenied' in str(exc):
            return findings
        return findings

    if not domain_names:
        return findings

    # describe_domains accepts up to 5 domain names per call
    domains = []
    for i in range(0, len(domain_names), 5):
        batch = domain_names[i:i + 5]
        try:
            resp = es.describe_domains(DomainNames=batch)
            domains.extend(resp.get('DomainStatusList', []) or [])
        except Exception:
            continue

    for d in domains:
        name = d.get('DomainName', '')
        arn  = d.get('ARN', name)
        ver  = d.get('EngineVersion', '?')

        # 1) Encryption at rest
        enc = d.get('EncryptionAtRestOptions') or {}
        at_rest = bool(enc.get('Enabled'))
        kms_key = enc.get('KmsKeyId', '')
        findings.append(make_finding(
            id=f'opensearch_encryption_at_rest_{name}_{region}',
            title=f'OpenSearch domain encrypted at rest: {name}',
            title_tr=f'OpenSearch domain bekleme sırasında şifreli: {name}',
            description=(
                f'Domain {name} ({ver}) in {region} '
                f'{"is encrypted at rest" if at_rest else "is NOT encrypted at rest"}. '
                f'Cluster nodes, automated snapshots, swap files, and indices all '
                f'inherit at-rest encryption from this setting.'
            ),
            description_tr=(
                f'{region} bölgesindeki domain {name} ({ver}) bekleme sırasında '
                f'{"şifreli" if at_rest else "ŞİFRELİ DEĞİL"}. '
                f'Cluster düğümleri, otomatik snapshot\'lar, swap dosyaları ve indeksler '
                f'bu ayardan beklemede şifreleme miras alır.'
            ),
            severity='HIGH', status='PASS' if at_rest else 'FAIL',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::OpenSearchService::Domain', region=region,
            frameworks={
                'CIS':      ['2.5.1'],
                'HIPAA':    ['164.312(a)(2)(iv)'],
                'ISO27001': ['A.10.1.1'],
                'SOC2':     ['CC6.7', 'C1.2'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC08']},
            },
            remediation=(
                f'OpenSearch → Domains → {name} → Actions → Modify cluster configuration → '
                f'Encryption-at-rest. NOTE: at-rest encryption requires a blue/green deployment.'
            ),
            remediation_tr=(
                f'OpenSearch → Domain\'ler → {name} → Eylemler → Cluster yapılandırmasını değiştir → '
                f'Beklemede şifreleme. NOT: beklemede şifreleme blue/green dağıtım gerektirir.'
            ),
            details={'kms_key_id': kms_key},
        ))

        # 2) Node-to-node encryption (in-cluster TLS)
        n2n = (d.get('NodeToNodeEncryptionOptions') or {}).get('Enabled', False)
        findings.append(make_finding(
            id=f'opensearch_node_to_node_encryption_{name}_{region}',
            title=f'OpenSearch node-to-node encryption: {name}',
            title_tr=f'OpenSearch düğümler arası şifreleme: {name}',
            description=(
                f'Domain {name} node-to-node encryption is '
                f'{"enabled" if n2n else "disabled"}. Without it, intra-cluster '
                f'traffic between data/master nodes is unencrypted.'
            ),
            description_tr=(
                f'Domain {name} düğümler arası şifreleme '
                f'{"etkin" if n2n else "devre dışı"}. Olmazsa veri/master düğümler arası '
                f'cluster içi trafik şifresizdir.'
            ),
            severity='HIGH', status='PASS' if n2n else 'FAIL',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::OpenSearchService::Domain', region=region,
            frameworks={
                'CIS':      ['2.5.1'],
                'HIPAA':    ['164.312(e)(1)'],
                'ISO27001': ['A.13.2.3', 'A.14.1.3'],
                'SOC2':     ['CC6.7'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC09']},
            },
            remediation=(
                f'OpenSearch → {name} → Modify → Node-to-node encryption (enable). '
                f'Requires blue/green deployment and may invalidate auto-tune presets.'
            ),
            remediation_tr=(
                f'OpenSearch → {name} → Değiştir → Düğümler arası şifreleme (etkinleştir). '
                f'Blue/green dağıtım gerektirir ve auto-tune ön ayarlarını geçersiz kılabilir.'
            ),
        ))

        # 3) Enforce HTTPS (TLS for the public/VPC endpoint)
        domain_endpoint_options = d.get('DomainEndpointOptions') or {}
        enforce_https = domain_endpoint_options.get('EnforceHTTPS', False)
        tls_policy = domain_endpoint_options.get('TLSSecurityPolicy', '')
        findings.append(make_finding(
            id=f'opensearch_https_only_{name}_{region}',
            title=f'OpenSearch enforces HTTPS-only: {name}',
            title_tr=f'OpenSearch yalnızca-HTTPS zorunda: {name}',
            description=(
                f'Domain {name} EnforceHTTPS={enforce_https}, '
                f'TLSSecurityPolicy="{tls_policy}". Modern policy is '
                f'Policy-Min-TLS-1.2-2019-07 or newer (Policy-Min-TLS-1.2-PFS-2023-10).'
            ),
            description_tr=(
                f'Domain {name} EnforceHTTPS={enforce_https}, '
                f'TLSSecurityPolicy="{tls_policy}". Modern politika '
                f'Policy-Min-TLS-1.2-2019-07 veya daha yeni (Policy-Min-TLS-1.2-PFS-2023-10).'
            ),
            severity='HIGH', status='PASS' if enforce_https else 'FAIL',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::OpenSearchService::Domain', region=region,
            frameworks={
                'CIS':      ['2.5.1'],
                'HIPAA':    ['164.312(e)(1)'],
                'ISO27001': ['A.13.2.3'],
                'SOC2':     ['CC6.7'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC09']},
            },
            remediation=(
                f'OpenSearch → {name} → Modify → Endpoint configuration → '
                f'Enable "Require HTTPS for all traffic to the domain".'
            ),
            remediation_tr=(
                f'OpenSearch → {name} → Değiştir → Endpoint yapılandırması → '
                f'"Tüm domain trafiği için HTTPS gerektir" seçeneğini etkinleştir.'
            ),
            details={'tls_policy': tls_policy},
        ))

        # 4) VPC endpoint (no public access)
        vpc_opts = d.get('VPCOptions') or {}
        in_vpc = bool(vpc_opts.get('VPCId'))
        findings.append(make_finding(
            id=f'opensearch_vpc_endpoint_{name}_{region}',
            title=f'OpenSearch in VPC (no public endpoint): {name}',
            title_tr=f'OpenSearch VPC içinde (genel endpoint yok): {name}',
            description=(
                f'Domain {name} is '
                f'{"deployed inside VPC " + (vpc_opts.get("VPCId") or "") if in_vpc else "publicly reachable"}. '
                f'Public OpenSearch endpoints rely solely on IAM/IP policies for access '
                f'— a VPC deployment removes the public attack surface entirely.'
            ),
            description_tr=(
                f'Domain {name} '
                f'{"VPC " + (vpc_opts.get("VPCId") or "") + " içine dağıtılmış" if in_vpc else "herkese açık erişilebilir"}. '
                f'Genel OpenSearch endpoint\'leri erişim için yalnızca IAM/IP politikalarına dayanır — '
                f'VPC dağıtımı genel saldırı yüzeyini tamamen ortadan kaldırır.'
            ),
            severity='HIGH', status='PASS' if in_vpc else 'FAIL',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::OpenSearchService::Domain', region=region,
            frameworks={
                'CIS':      ['2.5.2'],
                'HIPAA':    ['164.312(a)(1)'],
                'ISO27001': ['A.13.1.1', 'A.13.1.3'],
                'SOC2':     ['CC6.6', 'CC6.1'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC05']},
            },
            remediation=(
                f'Public → VPC migration requires a new domain (cannot move post-creation). '
                f'Create a new domain inside the target VPC, snapshot/restore indices.'
            ),
            remediation_tr=(
                f'Public → VPC geçişi yeni bir domain gerektirir (oluşturma sonrası taşınamaz). '
                f'Hedef VPC içinde yeni domain oluşturup snapshot/restore ile indeksleri taşıyın.'
            ),
            details={'vpc_id': vpc_opts.get('VPCId', '')},
        ))

        # 5) Fine-grained access control
        adv_sec = d.get('AdvancedSecurityOptions') or {}
        fga = adv_sec.get('Enabled', False)
        anon_auth_disabled = not adv_sec.get('AnonymousAuthEnabled', False)
        findings.append(make_finding(
            id=f'opensearch_fine_grained_access_{name}_{region}',
            title=f'OpenSearch fine-grained access control: {name}',
            title_tr=f'OpenSearch ince taneli erişim kontrolü: {name}',
            description=(
                f'Domain {name} fine-grained access control is '
                f'{"enabled" if fga else "disabled"}. FGAC adds field-level security, '
                f'document-level security, and audit logging. Anonymous auth disabled: '
                f'{anon_auth_disabled}.'
            ),
            description_tr=(
                f'Domain {name} ince taneli erişim kontrolü '
                f'{"etkin" if fga else "devre dışı"}. FGAC alan-düzeyi güvenlik, '
                f'belge-düzeyi güvenlik ve denetim günlüğü ekler. Anonim auth devre dışı: '
                f'{anon_auth_disabled}.'
            ),
            severity='MEDIUM', status='PASS' if (fga and anon_auth_disabled) else 'WARNING',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::OpenSearchService::Domain', region=region,
            frameworks={
                'ISO27001': ['A.9.4.1', 'A.9.4.2'],
                'SOC2':     ['CC6.1', 'CC6.3'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC02', 'SEC03']},
            },
            remediation=(
                f'OpenSearch → {name} → Modify → Security configuration → '
                f'Enable fine-grained access control; disable anonymous auth.'
            ),
            remediation_tr=(
                f'OpenSearch → {name} → Değiştir → Güvenlik yapılandırması → '
                f'İnce taneli erişim kontrolünü etkinleştir; anonim auth\'u devre dışı bırak.'
            ),
        ))

        # 6) Audit log publishing
        log_pub = d.get('LogPublishingOptions') or {}
        audit_logs = log_pub.get('AUDIT_LOGS', {})
        audit_on = audit_logs.get('Enabled', False)
        findings.append(make_finding(
            id=f'opensearch_audit_logs_{name}_{region}',
            title=f'OpenSearch audit logs enabled: {name}',
            title_tr=f'OpenSearch denetim günlükleri etkin: {name}',
            description=(
                f'Domain {name} audit log publishing is '
                f'{"enabled" if audit_on else "disabled"}. Audit logs record '
                f'authentication attempts, index changes, and document accesses '
                f'— essential for forensic investigation and PCI/HIPAA compliance.'
            ),
            description_tr=(
                f'Domain {name} denetim günlüğü yayını '
                f'{"etkin" if audit_on else "devre dışı"}. Denetim günlükleri '
                f'kimlik doğrulama denemeleri, indeks değişiklikleri ve belge erişimlerini kaydeder '
                f'— adli inceleme ve PCI/HIPAA uyumluluğu için gereklidir.'
            ),
            severity='MEDIUM', status='PASS' if audit_on else 'WARNING',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::OpenSearchService::Domain', region=region,
            frameworks={
                'CIS':      ['2.5.3'],
                'HIPAA':    ['164.312(b)'],
                'ISO27001': ['A.12.4.1', 'A.12.4.3'],
                'SOC2':     ['CC7.2', 'CC4.1'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC04']},
            },
            remediation=(
                f'OpenSearch → {name} → Logs → Audit logs → Enable → '
                f'CloudWatch Logs destination. Requires fine-grained access control.'
            ),
            remediation_tr=(
                f'OpenSearch → {name} → Günlükler → Denetim günlükleri → Etkinleştir → '
                f'CloudWatch Logs hedefi. İnce taneli erişim kontrolü gerektirir.'
            ),
        ))

    return findings
