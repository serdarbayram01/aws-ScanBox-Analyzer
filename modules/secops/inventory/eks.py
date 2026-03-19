"""SecOps — EKS Checks: public endpoint, control plane logging, secrets encryption,
node group IMDSv2, OIDC provider for IRSA."""
from .base import make_finding, not_available

SERVICE = 'EKS'

# All 5 EKS control plane log types that should be enabled
ALL_LOG_TYPES = {'api', 'audit', 'authenticator', 'controllerManager', 'scheduler'}


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('eks_regions', SERVICE, str(exc))]

    for region in regions:
        eks = session.client('eks', region_name=region)
        try:
            paginator = eks.get_paginator('list_clusters')
            for page in paginator.paginate():
                for cluster_name in page.get('clusters', []):
                    try:
                        cluster = eks.describe_cluster(name=cluster_name)['cluster']
                        cluster_arn = cluster.get('arn', cluster_name)
                        vpc_cfg     = cluster.get('resourcesVpcConfig', {})

                        # --- Public API endpoint ---
                        public_access = vpc_cfg.get('endpointPublicAccess', True)
                        public_cidrs  = vpc_cfg.get('publicAccessCidrs', ['0.0.0.0/0'])
                        open_to_world = '0.0.0.0/0' in public_cidrs or '::/0' in public_cidrs

                        if public_access and open_to_world:
                            sev, status = 'HIGH', 'FAIL'
                        elif public_access and not open_to_world:
                            sev, status = 'LOW', 'WARNING'
                        else:
                            sev, status = 'HIGH', 'PASS'  # private only — best

                        findings.append(make_finding(
                            id=f'eks_public_endpoint_{cluster_name}_{region}',
                            title=f'EKS API server endpoint not public: {cluster_name}',
                            title_tr=f'EKS API sunucu uç noktası herkese açık değil: {cluster_name}',
                            description=(
                                f'EKS cluster {cluster_name} in {region}: '
                                f'publicAccess={public_access}, CIDRs={public_cidrs}. '
                                f'Public API endpoints accessible from 0.0.0.0/0 expose the cluster to brute-force attacks.'
                            ),
                            description_tr=(
                                f'{region} bölgesindeki EKS kümesi {cluster_name}: '
                                f'publicAccess={public_access}, CIDRs={public_cidrs}. '
                                f'0.0.0.0/0\'dan erişilebilen genel API uç noktaları kümeyi kaba kuvvet saldırılarına maruz bırakır.'
                            ),
                            severity=sev, status=status,
                            service=SERVICE, resource_id=cluster_arn,
                            resource_type='AWS::EKS::Cluster', region=region,
                            frameworks={
                                'CIS': ['5.4.2'], 'ISO27001': ['A.13.1.3'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC05']},
                            },
                            remediation=(
                                f'EKS Console → {cluster_name} → Networking → '
                                f'Disable public access or restrict public CIDRs to known IP ranges.'
                            ),
                            remediation_tr=(
                                f'EKS Konsol → {cluster_name} → Ağ → '
                                f'Genel erişimi devre dışı bırakın veya genel CIDR\'ları bilinen IP aralıklarıyla sınırlandırın.'
                            ),
                            details={'public_access': public_access, 'public_cidrs': public_cidrs},
                        ))

                        # --- Control plane logging ---
                        enabled_log_types = set()
                        for log_cfg in cluster.get('logging', {}).get('clusterLogging', []):
                            if log_cfg.get('enabled'):
                                enabled_log_types.update(log_cfg.get('types', []))

                        missing_logs = ALL_LOG_TYPES - enabled_log_types
                        all_logs_on  = len(missing_logs) == 0

                        findings.append(make_finding(
                            id=f'eks_logging_{cluster_name}_{region}',
                            title=f'EKS control plane logging fully enabled: {cluster_name}',
                            title_tr=f'EKS kontrol düzlemi günlüğü tamamen etkin: {cluster_name}',
                            description=(
                                f'EKS cluster {cluster_name} in {region}: '
                                f'enabled={sorted(enabled_log_types)}, '
                                f'missing={sorted(missing_logs) if missing_logs else "none"}. '
                                f'All 5 log types (api, audit, authenticator, controllerManager, scheduler) should be enabled.'
                            ),
                            description_tr=(
                                f'{region} bölgesindeki EKS kümesi {cluster_name}: '
                                f'etkin={sorted(enabled_log_types)}, '
                                f'eksik={sorted(missing_logs) if missing_logs else "yok"}. '
                                f'Tüm 5 günlük türü (api, audit, authenticator, controllerManager, scheduler) etkinleştirilmelidir.'
                            ),
                            severity='MEDIUM', status='PASS' if all_logs_on else 'FAIL',
                            service=SERVICE, resource_id=cluster_arn,
                            resource_type='AWS::EKS::Cluster', region=region,
                            frameworks={
                                'CIS': ['5.1.1'], 'HIPAA': ['164.312(b)'],
                                'ISO27001': ['A.12.4.1'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC04']},
                            },
                            remediation=(
                                f'EKS Console → {cluster_name} → Observability → '
                                f'Enable all control plane log types: {sorted(missing_logs)}.'
                            ),
                            remediation_tr=(
                                f'EKS Konsol → {cluster_name} → Gözlemlenebilirlik → '
                                f'Tüm kontrol düzlemi günlük türlerini etkinleştirin: {sorted(missing_logs)}.'
                            ),
                            details={
                                'enabled': sorted(enabled_log_types),
                                'missing': sorted(missing_logs),
                            },
                        ))

                        # --- Secrets encryption (KMS) ---
                        enc_configs  = cluster.get('encryptionConfig', [])
                        secrets_enc  = any(
                            'secrets' in cfg.get('resources', []) and cfg.get('provider', {}).get('keyArn')
                            for cfg in enc_configs
                        )
                        findings.append(make_finding(
                            id=f'eks_secrets_encryption_{cluster_name}_{region}',
                            title=f'EKS secrets encrypted with KMS: {cluster_name}',
                            title_tr=f'EKS gizli bilgileri KMS ile şifreli: {cluster_name}',
                            description=f'EKS cluster {cluster_name} in {region} should encrypt Kubernetes secrets with a KMS key.',
                            description_tr=f'{region} bölgesindeki EKS kümesi {cluster_name}, Kubernetes gizli bilgilerini KMS anahtarıyla şifrelemelidir.',
                            severity='HIGH', status='PASS' if secrets_enc else 'FAIL',
                            service=SERVICE, resource_id=cluster_arn,
                            resource_type='AWS::EKS::Cluster', region=region,
                            frameworks={
                                'CIS': ['5.3.1'], 'HIPAA': ['164.312(a)(2)(iv)'],
                                'ISO27001': ['A.10.1.1'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC08']},
                            },
                            remediation=(
                                f'Enable envelope encryption for Kubernetes secrets on cluster {cluster_name} '
                                f'using a KMS customer-managed key.'
                            ),
                            remediation_tr=(
                                f'{cluster_name} kümesinde KMS müşteri yönetimli anahtar kullanarak '
                                f'Kubernetes gizli bilgileri için zarf şifrelemesini etkinleştirin.'
                            ),
                        ))

                        # --- OIDC provider for IRSA ---
                        oidc_url = cluster.get('identity', {}).get('oidc', {}).get('issuer', '')
                        oidc_ok  = bool(oidc_url)
                        findings.append(make_finding(
                            id=f'eks_oidc_{cluster_name}_{region}',
                            title=f'EKS OIDC provider configured (IRSA): {cluster_name}',
                            title_tr=f'EKS OIDC sağlayıcısı yapılandırılmış (IRSA): {cluster_name}',
                            description=(
                                f'EKS cluster {cluster_name} in {region} should have an OIDC provider '
                                f'to enable IAM Roles for Service Accounts (IRSA) instead of node-level IAM permissions.'
                            ),
                            description_tr=(
                                f'{region} bölgesindeki EKS kümesi {cluster_name}, düğüm düzeyinde IAM izinleri yerine '
                                f'Servis Hesapları için IAM Rolleri (IRSA) etkinleştirmek amacıyla OIDC sağlayıcısına sahip olmalıdır.'
                            ),
                            severity='MEDIUM', status='PASS' if oidc_ok else 'FAIL',
                            service=SERVICE, resource_id=cluster_arn,
                            resource_type='AWS::EKS::Cluster', region=region,
                            frameworks={
                                'CIS': ['5.1.2'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC03']},
                            },
                            remediation=f'Associate an IAM OIDC provider with the EKS cluster {cluster_name}.',
                            remediation_tr=f'EKS kümesi {cluster_name} ile bir IAM OIDC sağlayıcısı ilişkilendirin.',
                        ))

                        # --- Node groups: IMDSv2 ---
                        try:
                            ng_paginator = eks.get_paginator('list_nodegroups')
                            ec2_client = session.client('ec2', region_name=region)
                            for ng_page in ng_paginator.paginate(clusterName=cluster_name):
                                for ng_name in ng_page.get('nodegroups', []):
                                    try:
                                        ngd = eks.describe_nodegroup(
                                            clusterName=cluster_name, nodegroupName=ng_name
                                        )['nodegroup']
                                        ng_arn = ngd.get('nodegroupArn', ng_name)

                                        # Check IMDSv2 via launch template
                                        lt_info = ngd.get('launchTemplate', {})
                                        imdsv2_ok = False
                                        hop_ok    = False
                                        if lt_info.get('id'):
                                            try:
                                                versions = ec2_client.describe_launch_template_versions(
                                                    LaunchTemplateId=lt_info['id'],
                                                    Versions=[lt_info.get('version', '$Default')],
                                                )['LaunchTemplateVersions']
                                                for v in versions:
                                                    meta = v['LaunchTemplateData'].get('MetadataOptions', {})
                                                    imdsv2_ok = meta.get('HttpTokens') == 'required'
                                                    hop_ok    = int(meta.get('HttpPutResponseHopLimit', 2)) <= 1
                                            except Exception:
                                                pass

                                        findings.append(make_finding(
                                            id=f'eks_imdsv2_{cluster_name}_{ng_name}_{region}',
                                            title=f'EKS node group uses IMDSv2: {cluster_name}/{ng_name}',
                                            title_tr=f'EKS düğüm grubu IMDSv2 kullanıyor: {cluster_name}/{ng_name}',
                                            description=(
                                                f'Node group {ng_name} in EKS cluster {cluster_name} ({region}) '
                                                f'should enforce IMDSv2 (HttpTokens=required) to prevent SSRF-based '
                                                f'credential theft via the metadata service.'
                                            ),
                                            description_tr=(
                                                f'EKS kümesi {cluster_name} ({region}) içindeki {ng_name} düğüm grubu, '
                                                f'meta veri servisi aracılığıyla SSRF tabanlı kimlik bilgisi hırsızlığını '
                                                f'önlemek için IMDSv2 (HttpTokens=required) zorunlu kılmalıdır.'
                                            ),
                                            severity='HIGH',
                                            status='PASS' if imdsv2_ok else ('FAIL' if lt_info.get('id') else 'NOT_AVAILABLE'),
                                            service=SERVICE, resource_id=ng_arn,
                                            resource_type='AWS::EKS::Nodegroup', region=region,
                                            frameworks={
                                                'CIS': ['5.4.3'], 'ISO27001': ['A.14.2.5'],
                                                'WAFR': {'pillar': 'Security', 'controls': ['SEC05']},
                                            },
                                            remediation=(
                                                f'Update the launch template for node group {ng_name} to set '
                                                f'HttpTokens=required and HttpPutResponseHopLimit=1.'
                                            ),
                                            remediation_tr=(
                                                f'{ng_name} düğüm grubunun başlatma şablonunu '
                                                f'HttpTokens=required ve HttpPutResponseHopLimit=1 olacak şekilde güncelleyin.'
                                            ),
                                            details={'imdsv2': imdsv2_ok, 'hop_limit_ok': hop_ok},
                                        ))
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                    except Exception:
                        pass
        except Exception as exc:
            findings.append(not_available(f'eks_{region}', SERVICE, str(exc)))

    return findings
