"""SecOps — VPC Checks: default VPC, flow logs, default SG."""
from .base import make_finding, not_available
SERVICE = 'VPC'

def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('vpc_regions', SERVICE, str(exc))]
    for region in regions:
        ec2 = session.client('ec2', region_name=region)
        try:
            findings += _check_default_vpc(ec2, region, exclude_defaults)
            findings += _check_flow_logs(ec2, region)
            findings += _check_default_sg(ec2, region, exclude_defaults)
            findings += _check_gateway_endpoints(ec2, region)
            findings += _check_unused_security_groups(ec2, region)
        except Exception as exc:
            findings.append(not_available(f'vpc_{region}', SERVICE, str(exc)))
    return findings


def _check_default_vpc(ec2, region, exclude_defaults):
    try:
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])['Vpcs']
        if not vpcs:
            return [make_finding(
                id=f'vpc_no_default_{region}', title=f'No default VPC: {region}',
                title_tr=f'Varsayılan VPC yok: {region}',
                description=f'No default VPC exists in {region} — best practice.',
                description_tr=f'{region} bölgesinde varsayılan VPC yok — iyi uygulama.',
                severity='INFO', status='PASS', service=SERVICE,
                resource_id=region, resource_type='AWS::EC2::VPC', region=region,
                frameworks={'CIS': ['5.4'], 'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                remediation='No action required.', remediation_tr='Herhangi bir işlem gerekmiyor.',
            )]
        results = []
        for vpc in vpcs:
            vid = vpc['VpcId']
            results.append(make_finding(
                id=f'vpc_default_{vid}_{region}',
                title=f'Default VPC exists: {region}',
                title_tr=f'Varsayılan VPC mevcut: {region}',
                description=f'Default VPC {vid} in {region} should be removed if not needed.',
                description_tr=f'{region} bölgesindeki varsayılan VPC {vid} gerekmiyorsa kaldırılmalıdır.',
                severity='LOW', status='WARNING',
                service=SERVICE, resource_id=vid, resource_type='AWS::EC2::VPC',
                region=region, is_default_resource=True,
                frameworks={'CIS': ['5.4'], 'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                remediation='Delete the default VPC if no resources depend on it.',
                remediation_tr='Hiçbir kaynak bağımlı değilse varsayılan VPC\'yi silin.',
            ))
        return results
    except Exception as exc:
        return [not_available(f'vpc_default_{region}', SERVICE, str(exc))]


def _check_flow_logs(ec2, region):
    findings = []
    try:
        vpcs = ec2.describe_vpcs()['Vpcs']
        logs = ec2.describe_flow_logs()['FlowLogs']
        logged_vpcs = {fl['ResourceId'] for fl in logs if fl.get('FlowLogStatus') == 'ACTIVE'}
        for vpc in vpcs:
            vid = vpc['VpcId']
            enabled = vid in logged_vpcs
            findings.append(make_finding(
                id=f'vpc_flow_logs_{vid}_{region}',
                title=f'VPC flow logs enabled: {vid}',
                title_tr=f'VPC akış günlükleri aktif: {vid}',
                description=f'VPC {vid} in {region} should have flow logs enabled for network monitoring.',
                description_tr=f'{region} bölgesindeki VPC {vid} ağ izleme için akış günlüklerine sahip olmalıdır.',
                severity='MEDIUM', status='PASS' if enabled else 'FAIL',
                service=SERVICE, resource_id=vid, resource_type='AWS::EC2::VPC',
                region=region,
                frameworks={'CIS': ['5.1'], 'HIPAA': ['164.312(b)'], 'ISO27001': ['A.12.4.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC04']}},
                remediation=f'EC2 Console → VPCs → {vid} → Flow logs → Create flow log.',
                remediation_tr=f'EC2 Konsol → VPC\'ler → {vid} → Akış günlükleri → Akış günlüğü oluştur.',
            ))
    except Exception as exc:
        findings.append(not_available(f'vpc_flow_logs_{region}', SERVICE, str(exc)))
    return findings


def _check_default_sg(ec2, region, exclude_defaults):
    findings = []
    try:
        sgs = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': ['default']}])['SecurityGroups']
        for sg in sgs:
            sgid = sg['GroupId']
            has_rules = bool(sg.get('IpPermissions') or sg.get('IpPermissionsEgress'))
            if exclude_defaults:
                continue
            findings.append(make_finding(
                id=f'vpc_default_sg_{sgid}_{region}',
                title=f'Default SG restricts all traffic: {sgid}',
                title_tr=f'Varsayılan SG tüm trafiği kısıtlıyor: {sgid}',
                description=f'Default security group {sgid} in {region} should have no inbound/outbound rules.',
                description_tr=f'{region} bölgesindeki varsayılan güvenlik grubu {sgid} gelen/giden kural içermemelidir.',
                severity='MEDIUM', status='FAIL' if has_rules else 'PASS',
                service=SERVICE, resource_id=sgid, resource_type='AWS::EC2::SecurityGroup',
                region=region, is_default_resource=True,
                frameworks={'CIS': ['5.5'], 'ISO27001': ['A.13.1.1'],
                            'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                remediation='Remove all inbound/outbound rules from the default security group.',
                remediation_tr='Varsayılan güvenlik grubundaki tüm gelen/giden kuralları kaldırın.',
            ))
    except Exception as exc:
        findings.append(not_available(f'vpc_default_sg_{region}', SERVICE, str(exc)))
    return findings


def _check_gateway_endpoints(ec2, region):
    """Check if VPCs have S3 and DynamoDB gateway endpoints (free)."""
    findings = []
    try:
        vpcs = ec2.describe_vpcs()['Vpcs']
        endpoints = ec2.describe_vpc_endpoints(
            Filters=[{'Name': 'vpc-endpoint-type', 'Values': ['Gateway']}]
        ).get('VpcEndpoints', [])

        # Build a map: vpc_id -> set of service names with gateway endpoints
        vpc_endpoint_services = {}
        for ep in endpoints:
            vid = ep.get('VpcId', '')
            svc = ep.get('ServiceName', '')
            vpc_endpoint_services.setdefault(vid, set()).add(svc)

        for vpc in vpcs:
            vid = vpc['VpcId']
            ep_services = vpc_endpoint_services.get(vid, set())

            for gw_service, gw_label in [('s3', 'S3'), ('dynamodb', 'DynamoDB')]:
                has_endpoint = any(gw_service in svc.lower() for svc in ep_services)
                findings.append(make_finding(
                    id=f'vpc_gateway_endpoint_{gw_service}_{vid}_{region}',
                    title=f'VPC {gw_label} gateway endpoint: {vid}',
                    title_tr=f'VPC {gw_label} gateway endpoint: {vid}',
                    description=(
                        f'VPC {vid} in {region} {"has" if has_endpoint else "does not have"} '
                        f'a {gw_label} gateway endpoint. Gateway endpoints are free and keep '
                        f'traffic within the AWS network, reducing NAT Gateway costs.'
                    ),
                    description_tr=(
                        f'{region} bölgesindeki VPC {vid} {gw_label} gateway endpoint\'e '
                        f'{"sahip" if has_endpoint else "sahip değil"}. Gateway endpoint\'ler '
                        f'ücretsizdir ve trafiği AWS ağı içinde tutarak NAT Gateway maliyetlerini azaltır.'
                    ),
                    severity='LOW' if not has_endpoint else 'INFO',
                    status='PASS' if has_endpoint else 'WARNING',
                    service=SERVICE, resource_id=vid, resource_type='AWS::EC2::VPCEndpoint',
                    region=region,
                    frameworks={
                        'CIS': ['5.6'], 'ISO27001': ['A.13.1.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC05', 'COST04']},
                    },
                    remediation=(
                        f'VPC Console → Endpoints → Create endpoint → '
                        f'com.amazonaws.{region}.{gw_service} → Gateway → Select VPC {vid}.'
                    ),
                    remediation_tr=(
                        f'VPC Konsol → Endpoint\'ler → Endpoint oluştur → '
                        f'com.amazonaws.{region}.{gw_service} → Gateway → VPC {vid} seçin.'
                    ),
                ))
    except Exception as exc:
        findings.append(not_available(f'vpc_gateway_endpoints_{region}', SERVICE, str(exc)))
    return findings


def _check_unused_security_groups(ec2, region):
    """Check for security groups not attached to any ENI (except default SGs)."""
    findings = []
    try:
        sgs = ec2.describe_security_groups()['SecurityGroups']
        enis = ec2.describe_network_interfaces()['NetworkInterfaces']

        # Collect all SG IDs referenced by any ENI
        used_sg_ids = set()
        for eni in enis:
            for group in eni.get('Groups', []):
                used_sg_ids.add(group['GroupId'])

        for sg in sgs:
            sgid = sg['GroupId']
            sg_name = sg.get('GroupName', '')
            vpc_id = sg.get('VpcId', '')

            # Skip default security groups — they cannot be deleted
            if sg_name == 'default':
                continue

            is_used = sgid in used_sg_ids
            if not is_used:
                findings.append(make_finding(
                    id=f'vpc_unused_sg_{sgid}_{region}',
                    title=f'Unused security group: {sg_name} ({sgid})',
                    title_tr=f'Kullanılmayan güvenlik grubu: {sg_name} ({sgid})',
                    description=(
                        f'Security group {sg_name} ({sgid}) in VPC {vpc_id}, region {region} '
                        f'is not attached to any network interface. Unused security groups '
                        f'increase attack surface complexity and should be removed.'
                    ),
                    description_tr=(
                        f'VPC {vpc_id}, {region} bölgesindeki güvenlik grubu {sg_name} ({sgid}) '
                        f'hiçbir ağ arayüzüne bağlı değil. Kullanılmayan güvenlik grupları '
                        f'saldırı yüzeyi karmaşıklığını artırır ve kaldırılmalıdır.'
                    ),
                    severity='LOW', status='WARNING',
                    service=SERVICE, resource_id=sgid, resource_type='AWS::EC2::SecurityGroup',
                    resource_name=sg_name, region=region,
                    frameworks={
                        'CIS': ['5.5'], 'HIPAA': ['164.312(a)(1)'], 'ISO27001': ['A.13.1.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC05']},
                    },
                    remediation=(
                        f'EC2 Console → Security Groups → {sgid} → Actions → Delete security group. '
                        f'Verify no resources reference this SG in launch templates or scaling configs first.'
                    ),
                    remediation_tr=(
                        f'EC2 Konsol → Güvenlik Grupları → {sgid} → İşlemler → Güvenlik grubunu sil. '
                        f'Önce hiçbir kaynağın bu SG\'yi başlatma şablonları veya ölçeklendirme yapılandırmalarında '
                        f'referans almadığını doğrulayın.'
                    ),
                ))
    except Exception as exc:
        findings.append(not_available(f'vpc_unused_sg_{region}', SERVICE, str(exc)))
    return findings
