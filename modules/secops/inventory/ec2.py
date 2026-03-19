"""
SecOps — EC2 Checks
Security groups (0.0.0.0/0 + ::/0 SSH/RDP/all), EBS default encryption, IMDSv2.
"""

from .base import make_finding, not_available

SERVICE = 'EC2'

# Both IPv4 and IPv6 open-to-world CIDRs
_OPEN_CIDR_CONFIGS = [
    # (range_key, cidr_key, open_cidr, id_suffix, display_cidr)
    ('IpRanges',   'CidrIp',   '0.0.0.0/0', '',    '0.0.0.0/0'),
    ('Ipv6Ranges', 'CidrIpv6', '::/0',       '_v6', '::/0'),
]


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = _get_regions(session)
        except Exception as exc:
            return [not_available('ec2_regions', SERVICE, str(exc))]

    for region in regions:
        ec2 = session.client('ec2', region_name=region)
        try:
            findings += _check_ebs_encryption(ec2, region)
            findings += _check_security_groups(ec2, region, exclude_defaults)
            findings += _check_imdsv2(ec2, region)
            findings += _check_public_amis(ec2, region)
        except Exception as exc:
            findings.append(not_available(f'ec2_{region}', SERVICE, str(exc)))
    return findings


def _get_regions(session):
    ec2 = session.client('ec2', region_name='us-east-1')
    return [r['RegionName'] for r in ec2.describe_regions(
        Filters=[{'Name': 'opt-in-status', 'Values': ['opt-in-not-required', 'opted-in']}]
    )['Regions']]


def _check_ebs_encryption(ec2, region):
    try:
        enabled = ec2.get_ebs_encryption_by_default()['EbsEncryptionByDefault']
        return [make_finding(
            id=f'ec2_ebs_default_encryption_{region}',
            title=f'EBS default encryption enabled: {region}',
            title_tr=f'EBS varsayılan şifreleme aktif: {region}',
            description=f'EBS volumes in {region} should be encrypted by default.',
            description_tr=f'{region} bölgesindeki EBS birimleri varsayılan olarak şifrelenmelidir.',
            severity='HIGH', status='PASS' if enabled else 'FAIL',
            service=SERVICE, resource_id=region,
            resource_type='AWS::EC2::EBSEncryptionByDefault', region=region,
            frameworks={'CIS': ['2.2.1'], 'HIPAA': ['164.312(a)(2)(iv)'], 'ISO27001': ['A.10.1.1'],
                        'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
            remediation=f'EC2 Console ({region}) → Settings → EBS Encryption → Enable.',
            remediation_tr=f'EC2 Konsol ({region}) → Ayarlar → EBS Şifreleme → Etkinleştir.',
        )]
    except Exception as exc:
        return [not_available(f'ec2_ebs_encryption_{region}', SERVICE, str(exc))]


def _check_security_groups(ec2, region, exclude_defaults):
    findings = []
    try:
        paginator = ec2.get_paginator('describe_security_groups')
        for page in paginator.paginate():
            for sg in page['SecurityGroups']:
                sg_id      = sg['GroupId']
                sg_name    = sg.get('GroupName', sg_id)
                is_default = sg_name == 'default'

                if exclude_defaults and is_default:
                    continue

                for perm in sg.get('IpPermissions', []):
                    from_port = perm.get('FromPort', -1)
                    to_port   = perm.get('ToPort', -1)
                    proto     = perm.get('IpProtocol', '-1')

                    for range_key, cidr_key, open_cidr, id_sfx, cidr_disp in _OPEN_CIDR_CONFIGS:
                        for ip_range in perm.get(range_key, []):
                            if ip_range.get(cidr_key) != open_cidr:
                                continue

                            # SSH (22)
                            if _port_in_range(22, from_port, to_port, proto):
                                findings.append(make_finding(
                                    id=f'ec2_sg_ssh_{sg_id}_{region}{id_sfx}',
                                    title=f'Security group allows SSH from {cidr_disp}: {sg_name}',
                                    title_tr=f'Güvenlik grubu {cidr_disp} üzerinden SSH\'ye izin veriyor: {sg_name}',
                                    description=f'SG {sg_id} in {region} allows inbound SSH (port 22) from {cidr_disp}.',
                                    description_tr=f'{region} bölgesindeki {sg_id} SG, {cidr_disp} adresinden gelen SSH (port 22) bağlantısına izin veriyor.',
                                    severity='CRITICAL', status='FAIL',
                                    service=SERVICE, resource_id=sg_id,
                                    resource_type='AWS::EC2::SecurityGroup',
                                    resource_name=sg_name, region=region,
                                    is_default_resource=is_default,
                                    frameworks={'CIS': ['5.2'], 'ISO27001': ['A.13.1.1'],
                                                'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                                    remediation=f'Remove SSH (22) from {cidr_disp} — restrict to specific IPs or a bastion host.',
                                    remediation_tr=f'{cidr_disp} üzerinden SSH (22) kuralını kaldırın — belirli IP\'lere veya bastion sunucusuna kısıtlayın.',
                                ))

                            # RDP (3389)
                            if _port_in_range(3389, from_port, to_port, proto):
                                findings.append(make_finding(
                                    id=f'ec2_sg_rdp_{sg_id}_{region}{id_sfx}',
                                    title=f'Security group allows RDP from {cidr_disp}: {sg_name}',
                                    title_tr=f'Güvenlik grubu {cidr_disp} üzerinden RDP\'ye izin veriyor: {sg_name}',
                                    description=f'SG {sg_id} in {region} allows inbound RDP (port 3389) from {cidr_disp}.',
                                    description_tr=f'{region} bölgesindeki {sg_id} SG, {cidr_disp} adresinden gelen RDP (port 3389) bağlantısına izin veriyor.',
                                    severity='CRITICAL', status='FAIL',
                                    service=SERVICE, resource_id=sg_id,
                                    resource_type='AWS::EC2::SecurityGroup',
                                    resource_name=sg_name, region=region,
                                    is_default_resource=is_default,
                                    frameworks={'CIS': ['5.3'], 'ISO27001': ['A.13.1.1'],
                                                'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                                    remediation=f'Remove RDP (3389) from {cidr_disp} — restrict to specific IPs.',
                                    remediation_tr=f'{cidr_disp} üzerinden RDP (3389) kuralını kaldırın — belirli IP\'lere kısıtlayın.',
                                ))

                            # All traffic (protocol -1)
                            if proto == '-1':
                                findings.append(make_finding(
                                    id=f'ec2_sg_all_{sg_id}_{region}{id_sfx}',
                                    title=f'Security group allows all traffic from {cidr_disp}: {sg_name}',
                                    title_tr=f'Güvenlik grubu {cidr_disp} üzerinden tüm trafiğe izin veriyor: {sg_name}',
                                    description=f'SG {sg_id} in {region} allows all inbound traffic from {cidr_disp}.',
                                    description_tr=f'{region} bölgesindeki {sg_id} SG, {cidr_disp} adresinden gelen tüm trafiğe izin veriyor.',
                                    severity='CRITICAL', status='FAIL',
                                    service=SERVICE, resource_id=sg_id,
                                    resource_type='AWS::EC2::SecurityGroup',
                                    resource_name=sg_name, region=region,
                                    is_default_resource=is_default,
                                    frameworks={'CIS': ['5.1'], 'ISO27001': ['A.13.1.1'],
                                                'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                                    remediation=f'Restrict inbound rules — never allow all traffic from {cidr_disp}.',
                                    remediation_tr=f'Gelen kuralları kısıtlayın — {cidr_disp} üzerinden tüm trafiğe asla izin vermeyin.',
                                ))

                # --- Egress: unrestricted outbound ---
                for eperm in sg.get('IpPermissionsEgress', []):
                    eproto = eperm.get('IpProtocol', '')
                    if eproto != '-1':
                        continue
                    for range_key, cidr_key, open_cidr, id_sfx, cidr_disp in _OPEN_CIDR_CONFIGS:
                        for ip_range in eperm.get(range_key, []):
                            if ip_range.get(cidr_key) == open_cidr:
                                findings.append(make_finding(
                                    id=f'ec2_sg_egress_all_{sg_id}_{region}{id_sfx}',
                                    title=f'Security group allows all outbound traffic to {cidr_disp}: {sg_name}',
                                    title_tr=f'Güvenlik grubu {cidr_disp} adresine tüm giden trafiğe izin veriyor: {sg_name}',
                                    description=f'SG {sg_id} in {region} allows unrestricted egress to {cidr_disp}.',
                                    description_tr=f'{region} bölgesindeki {sg_id} SG, {cidr_disp} adresine kısıtlamasız giden trafiğe izin veriyor.',
                                    severity='MEDIUM', status='WARNING',
                                    service=SERVICE, resource_id=sg_id,
                                    resource_type='AWS::EC2::SecurityGroup',
                                    resource_name=sg_name, region=region,
                                    is_default_resource=is_default,
                                    frameworks={'CIS': ['5.4'], 'ISO27001': ['A.13.1.1'],
                                                'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                                    remediation=f'Restrict egress rules on {sg_id} — limit outbound to required ports/destinations only.',
                                    remediation_tr=f'{sg_id} giden kurallarını kısıtlayın — giden trafiği yalnızca gerekli portlar/hedeflerle sınırlayın.',
                                ))

    except Exception as exc:
        findings.append(not_available(f'ec2_sg_{region}', SERVICE, str(exc)))
    return findings


def _check_imdsv2(ec2, region):
    findings = []
    try:
        paginator = ec2.get_paginator('describe_instances')
        for page in paginator.paginate(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped']}]
        ):
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    iid    = instance['InstanceId']
                    meta   = instance.get('MetadataOptions', {})
                    imdsv2 = meta.get('HttpTokens') == 'required'
                    name   = next((t['Value'] for t in instance.get('Tags', [])
                                   if t['Key'] == 'Name'), iid)
                    findings.append(make_finding(
                        id=f'ec2_imdsv2_{iid}_{region}',
                        title=f'IMDSv2 enforced: {name}',
                        title_tr=f'IMDSv2 zorunlu: {name}',
                        description=f'Instance {iid} should use IMDSv2 (HttpTokens=required) to prevent SSRF.',
                        description_tr=f'{iid} instance\'ı SSRF saldırılarını önlemek için IMDSv2 (HttpTokens=required) kullanmalıdır.',
                        severity='HIGH', status='PASS' if imdsv2 else 'FAIL',
                        service=SERVICE, resource_id=iid,
                        resource_type='AWS::EC2::Instance',
                        resource_name=name, region=region,
                        frameworks={'CIS': ['5.6'], 'ISO27001': ['A.13.1.1'],
                                    'WAFR': {'pillar': 'Security', 'controls': ['SEC05']}},
                        remediation=f'EC2 Console → {iid} → Actions → Modify instance metadata → Set HttpTokens=required.',
                        remediation_tr=f'EC2 Konsol → {iid} → Eylemler → Instance meta verilerini değiştir → HttpTokens=required ayarlayın.',
                    ))
    except Exception as exc:
        findings.append(not_available(f'ec2_imdsv2_{region}', SERVICE, str(exc)))
    return findings


def _check_public_amis(ec2, region):
    """Check for self-owned AMIs that are publicly shared."""
    findings = []
    try:
        images = ec2.describe_images(Owners=['self']).get('Images', [])
        for img in images:
            ami_id = img['ImageId']
            ami_name = img.get('Name', ami_id)
            is_public = img.get('Public', False)
            if is_public:
                findings.append(make_finding(
                    id=f'ec2_public_ami_{ami_id}_{region}',
                    title=f'Public AMI detected: {ami_name}',
                    title_tr=f'Genel AMI tespit edildi: {ami_name}',
                    description=f'AMI {ami_id} in {region} is publicly shared. This may expose sensitive data or configurations.',
                    description_tr=f'{region} bölgesindeki {ami_id} AMI\'si herkese açık paylaşılıyor. Bu hassas veri veya yapılandırmaları açığa çıkarabilir.',
                    severity='HIGH', status='FAIL',
                    service=SERVICE, resource_id=ami_id,
                    resource_type='AWS::EC2::Image',
                    resource_name=ami_name, region=region,
                    frameworks={'CIS': ['2.2.2'], 'HIPAA': ['164.312(a)(1)'], 'ISO27001': ['A.13.1.3'],
                                'WAFR': {'pillar': 'Security', 'controls': ['SEC06']}},
                    remediation=f'EC2 Console → AMIs → {ami_id} → Actions → Edit AMI permissions → Set to Private.',
                    remediation_tr=f'EC2 Konsol → AMI\'ler → {ami_id} → Eylemler → AMI izinlerini düzenle → Özel olarak ayarlayın.',
                ))
    except Exception as exc:
        findings.append(not_available(f'ec2_public_ami_{region}', SERVICE, str(exc)))
    return findings


def _port_in_range(port, from_port, to_port, proto):
    if proto == '-1':
        return True
    if proto not in ('tcp', 'udp', '6', '17'):
        return False
    try:
        return int(from_port) <= port <= int(to_port)
    except (TypeError, ValueError):
        return False
