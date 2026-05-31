"""SecOps — Amazon ElastiCache Checks: at-rest encryption, in-transit
TLS, AUTH token, automatic failover (Multi-AZ), automatic backups.

Covers both Redis OSS / Valkey replication groups (cluster mode disabled or
enabled) and legacy stand-alone Memcached clusters. Memcached has no native
encryption — we still surface that as a known limitation."""

from .base import make_finding, not_available

SERVICE = 'ElastiCache'


def run_checks(session, exclude_defaults=False, regions=None):
    findings = []
    if not regions:
        try:
            regions = [r['RegionName'] for r in session.client('ec2', region_name='us-east-1')
                       .describe_regions(Filters=[{'Name': 'opt-in-status',
                       'Values': ['opt-in-not-required', 'opted-in']}])['Regions']]
        except Exception as exc:
            return [not_available('elasticache_regions', SERVICE, str(exc))]

    for region in regions:
        try:
            findings += _check_region(session, region)
        except Exception as exc:
            findings.append(not_available(f'elasticache_{region}', SERVICE, str(exc)))
    return findings


def _check_region(session, region):
    findings = []
    try:
        ec = session.client('elasticache', region_name=region)
    except Exception:
        return findings

    # ----- Replication groups (Redis OSS / Valkey) -----
    try:
        rgs = []
        paginator = ec.get_paginator('describe_replication_groups')
        for page in paginator.paginate():
            rgs.extend(page.get('ReplicationGroups', []) or [])
    except Exception as exc:
        if 'AccessDenied' in str(exc):
            return findings
        rgs = []

    for rg in rgs:
        rg_id = rg.get('ReplicationGroupId', '')
        arn   = rg.get('ARN', rg_id)
        engine = (rg.get('Engine') or 'redis').lower()

        # 1) At-rest encryption
        at_rest = bool(rg.get('AtRestEncryptionEnabled'))
        kms_key = rg.get('KmsKeyId', '')
        findings.append(make_finding(
            id=f'elasticache_at_rest_encryption_{rg_id}_{region}',
            title=f'ElastiCache at-rest encryption: {rg_id}',
            title_tr=f'ElastiCache beklemede şifreleme: {rg_id}',
            description=(
                f'Replication group {rg_id} ({engine}) in {region} '
                f'{"is encrypted at rest" if at_rest else "is NOT encrypted at rest"}. '
                f'At-rest encryption protects RDB / AOF snapshots and on-disk data files.'
            ),
            description_tr=(
                f'{region} bölgesindeki çoğaltma grubu {rg_id} ({engine}), beklemede '
                f'{"şifreli" if at_rest else "ŞİFRELİ DEĞİL"}. '
                f'Beklemede şifreleme RDB / AOF snapshot\'larını ve disk veri dosyalarını korur.'
            ),
            severity='HIGH', status='PASS' if at_rest else 'FAIL',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::ElastiCache::ReplicationGroup', region=region,
            frameworks={
                'CIS':      ['2.6.1'],
                'HIPAA':    ['164.312(a)(2)(iv)'],
                'ISO27001': ['A.10.1.1'],
                'SOC2':     ['CC6.7', 'C1.2'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC08']},
            },
            remediation=(
                f'At-rest encryption cannot be modified post-creation. Create a new '
                f'replication group with AtRestEncryptionEnabled=true and migrate data.'
            ),
            remediation_tr=(
                f'Beklemede şifreleme oluşturma sonrası değiştirilemez. AtRestEncryptionEnabled=true '
                f'ile yeni bir çoğaltma grubu oluşturup verileri taşıyın.'
            ),
            details={'kms_key_id': kms_key},
        ))

        # 2) In-transit (TLS)
        in_transit = bool(rg.get('TransitEncryptionEnabled'))
        findings.append(make_finding(
            id=f'elasticache_transit_encryption_{rg_id}_{region}',
            title=f'ElastiCache in-transit encryption (TLS): {rg_id}',
            title_tr=f'ElastiCache aktarımda şifreleme (TLS): {rg_id}',
            description=(
                f'Replication group {rg_id} in-transit encryption is '
                f'{"enabled" if in_transit else "disabled"}. Without TLS, RESP/MEMCACHE '
                f'traffic between clients and cache nodes is plaintext.'
            ),
            description_tr=(
                f'Çoğaltma grubu {rg_id} aktarımda şifreleme '
                f'{"etkin" if in_transit else "devre dışı"}. TLS olmadan, istemciler ve cache '
                f'düğümleri arasındaki RESP/MEMCACHE trafiği düz metindir.'
            ),
            severity='HIGH', status='PASS' if in_transit else 'FAIL',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::ElastiCache::ReplicationGroup', region=region,
            frameworks={
                'CIS':      ['2.6.1'],
                'HIPAA':    ['164.312(e)(1)'],
                'ISO27001': ['A.13.2.3', 'A.14.1.3'],
                'SOC2':     ['CC6.7'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC09']},
            },
            remediation=(
                f'In-transit encryption cannot be toggled in place (requires snapshot + '
                f'new RG). Plan a maintenance window: snapshot → create new RG with '
                f'TransitEncryptionEnabled=true → migrate clients.'
            ),
            remediation_tr=(
                f'Aktarımda şifreleme yerinde değiştirilemez (snapshot + yeni RG gerektirir). '
                f'Bakım penceresi planlayın: snapshot → TransitEncryptionEnabled=true ile yeni RG → '
                f'istemcileri taşıyın.'
            ),
        ))

        # 3) AUTH token (Redis only)
        if 'redis' in engine or 'valkey' in engine:
            auth_on = bool(rg.get('AuthTokenEnabled'))
            findings.append(make_finding(
                id=f'elasticache_auth_token_{rg_id}_{region}',
                title=f'ElastiCache AUTH token configured: {rg_id}',
                title_tr=f'ElastiCache AUTH token yapılandırılmış: {rg_id}',
                description=(
                    f'Replication group {rg_id} AUTH token is '
                    f'{"set" if auth_on else "not set"}. Without an AUTH token, '
                    f'any client with network access can issue any command. '
                    f'IAM authentication (newer alternative) is preferred for Redis 7+.'
                ),
                description_tr=(
                    f'Çoğaltma grubu {rg_id} AUTH token '
                    f'{"belirlenmiş" if auth_on else "belirlenmemiş"}. AUTH token olmadan, '
                    f'ağ erişimi olan herhangi bir istemci herhangi bir komut çalıştırabilir. '
                    f'IAM kimlik doğrulama (yeni alternatif) Redis 7+ için tercih edilir.'
                ),
                severity='HIGH', status='PASS' if auth_on else 'FAIL',
                service=SERVICE, resource_id=arn,
                resource_type='AWS::ElastiCache::ReplicationGroup', region=region,
                frameworks={
                    'CIS':      ['2.6.1'],
                    'HIPAA':    ['164.312(a)(1)'],
                    'ISO27001': ['A.9.4.2'],
                    'SOC2':     ['CC6.1'],
                    'WAFR':     {'pillar': 'Security', 'controls': ['SEC03']},
                },
                remediation=(
                    f'ElastiCache → Redis groups → {rg_id} → Modify → set AUTH token. '
                    f'Or migrate to IAM-based authentication (Redis 7+).'
                ),
                remediation_tr=(
                    f'ElastiCache → Redis grupları → {rg_id} → Değiştir → AUTH token belirle. '
                    f'Veya IAM tabanlı kimlik doğrulamaya geçin (Redis 7+).'
                ),
            ))

        # 4) Automatic failover (Multi-AZ)
        af = rg.get('AutomaticFailover', 'disabled').lower()
        multi_az = af in ('enabled', 'enabling')
        findings.append(make_finding(
            id=f'elasticache_automatic_failover_{rg_id}_{region}',
            title=f'ElastiCache automatic failover (Multi-AZ): {rg_id}',
            title_tr=f'ElastiCache otomatik failover (Multi-AZ): {rg_id}',
            description=(
                f'Replication group {rg_id} automatic failover status: "{af}". '
                f'Without Multi-AZ, primary node failure causes downtime and requires '
                f'manual promotion of a replica.'
            ),
            description_tr=(
                f'Çoğaltma grubu {rg_id} otomatik failover durumu: "{af}". '
                f'Multi-AZ olmadan, primary düğüm arızası kesintiye neden olur ve '
                f'replikadan biri manuel olarak yükseltilmek zorundadır.'
            ),
            severity='MEDIUM', status='PASS' if multi_az else 'WARNING',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::ElastiCache::ReplicationGroup', region=region,
            frameworks={
                'ISO27001': ['A.17.2.1'],
                'SOC2':     ['A1.2'],
                'WAFR':     {'pillar': 'Reliability', 'controls': ['REL10', 'REL11']},
            },
            remediation=(
                f'ElastiCache → {rg_id} → Modify → Multi-AZ → enable. '
                f'Requires at least one replica node.'
            ),
            remediation_tr=(
                f'ElastiCache → {rg_id} → Değiştir → Multi-AZ → etkinleştir. '
                f'En az bir replika düğüm gerektirir.'
            ),
        ))

        # 5) Automatic snapshots (Redis only)
        if 'redis' in engine or 'valkey' in engine:
            retention = rg.get('SnapshotRetentionLimit', 0)
            findings.append(make_finding(
                id=f'elasticache_snapshot_retention_{rg_id}_{region}',
                title=f'ElastiCache automatic snapshots: {rg_id}',
                title_tr=f'ElastiCache otomatik snapshot: {rg_id}',
                description=(
                    f'Replication group {rg_id} snapshot retention = {retention} day(s). '
                    f'0 means automatic snapshots are disabled — no point-in-time '
                    f'recovery is possible.'
                ),
                description_tr=(
                    f'Çoğaltma grubu {rg_id} snapshot saklama = {retention} gün. '
                    f'0 değeri otomatik snapshot\'ların devre dışı olduğu anlamına gelir — '
                    f'noktasal kurtarma mümkün değildir.'
                ),
                severity='LOW', status='PASS' if retention >= 1 else 'WARNING',
                service=SERVICE, resource_id=arn,
                resource_type='AWS::ElastiCache::ReplicationGroup', region=region,
                frameworks={
                    'HIPAA':    ['164.308(a)(7)(ii)(A)'],
                    'ISO27001': ['A.12.3.1'],
                    'SOC2':     ['A1.2'],
                    'WAFR':     {'pillar': 'Reliability', 'controls': ['REL09']},
                },
                remediation=(
                    f'ElastiCache → {rg_id} → Modify → Backup retention period → '
                    f'set to >= 7 days for compliance baselines.'
                ),
                remediation_tr=(
                    f'ElastiCache → {rg_id} → Değiştir → Yedekleme saklama süresi → '
                    f'uyumluluk taban çizgileri için >= 7 gün olarak ayarlayın.'
                ),
                details={'retention_days': retention},
            ))

    # ----- Stand-alone Memcached clusters -----
    # describe_cache_clusters lists every node group; we want Memcached only
    # (Redis nodes also appear here but covered above as RGs).
    try:
        clusters = []
        paginator = ec.get_paginator('describe_cache_clusters')
        for page in paginator.paginate():
            clusters.extend(page.get('CacheClusters', []) or [])
    except Exception:
        clusters = []

    for c in clusters:
        if c.get('Engine') != 'memcached':
            continue  # redis handled above as RGs
        cid = c.get('CacheClusterId', '')
        arn = c.get('ARN', cid)
        findings.append(make_finding(
            id=f'elasticache_memcached_no_encryption_{cid}_{region}',
            title=f'ElastiCache Memcached cluster (no encryption support): {cid}',
            title_tr=f'ElastiCache Memcached cluster (şifreleme desteği yok): {cid}',
            description=(
                f'Memcached cluster {cid} in {region} cannot use at-rest or in-transit '
                f'encryption — these are Redis-only features. Sensitive data SHOULD NOT '
                f'be cached in Memcached; if required, migrate to Redis/Valkey.'
            ),
            description_tr=(
                f'{region} bölgesindeki Memcached cluster {cid}, beklemede veya aktarımda '
                f'şifreleme kullanamaz — bunlar yalnızca Redis özellikleridir. Hassas veri '
                f'Memcached\'de önbelleğe ALINMAMALIDIR; gerekirse Redis/Valkey\'e geçin.'
            ),
            severity='MEDIUM', status='WARNING',
            service=SERVICE, resource_id=arn,
            resource_type='AWS::ElastiCache::CacheCluster', region=region,
            frameworks={
                'HIPAA':    ['164.312(a)(2)(iv)', '164.312(e)(1)'],
                'ISO27001': ['A.10.1.1', 'A.13.2.3'],
                'SOC2':     ['CC6.7', 'C1.2'],
                'WAFR':     {'pillar': 'Security', 'controls': ['SEC08', 'SEC09']},
            },
            remediation=(
                f'ElastiCache → Memcached → {cid} → Inventory the keyspace; '
                f'if any sensitive data flows through it, migrate to a Redis '
                f'replication group with at-rest + in-transit encryption.'
            ),
            remediation_tr=(
                f'ElastiCache → Memcached → {cid} → Anahtar uzayını envanterleyin; '
                f'içinde hassas veri akıyorsa beklemede + aktarımda şifrelemeli '
                f'bir Redis çoğaltma grubuna geçin.'
            ),
        ))

    return findings
