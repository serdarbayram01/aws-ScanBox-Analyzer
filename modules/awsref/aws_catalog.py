"""Static AWS reference catalog — regions, Local Zones, services, endpoints.

This module contains zero AWS API dependencies. All data is a hand-maintained
snapshot (last reviewed 2026-05) ported from the ist-LZ-TEST Go reference
project. Update as AWS expands.
"""

# ---------------------------------------------------------------------------
# Public regions (31 entries). Each entry: code, name, geo bucket, opt-in flag.
# `lzs` lists known Local Zone AZ codes that extend the region.
# ---------------------------------------------------------------------------
AWS_REGIONS = [
    {'code': 'us-east-1',       'name': 'US East (N. Virginia)',         'geo': 'NA', 'opt_in': False,
     'lzs': ['us-east-1-atl-1a', 'us-east-1-bos-1a', 'us-east-1-chi-1a',
             'us-east-1-dfw-1a', 'us-east-1-iah-1a', 'us-east-1-mci-1a',
             'us-east-1-mia-1a', 'us-east-1-msp-1a', 'us-east-1-nyc-1a',
             'us-east-1-phl-1a']},
    {'code': 'us-east-2',       'name': 'US East (Ohio)',                'geo': 'NA', 'opt_in': False, 'lzs': []},
    {'code': 'us-west-1',       'name': 'US West (N. California)',       'geo': 'NA', 'opt_in': False, 'lzs': []},
    {'code': 'us-west-2',       'name': 'US West (Oregon)',              'geo': 'NA', 'opt_in': False,
     'lzs': ['us-west-2-den-1a', 'us-west-2-las-1a', 'us-west-2-lax-1a',
             'us-west-2-lax-1b', 'us-west-2-pdx-1a', 'us-west-2-phx-1a',
             'us-west-2-sea-1a']},
    {'code': 'ca-central-1',    'name': 'Canada (Central)',              'geo': 'NA', 'opt_in': False, 'lzs': []},
    {'code': 'ca-west-1',       'name': 'Canada (Calgary)',              'geo': 'NA', 'opt_in': True,  'lzs': []},
    {'code': 'eu-central-1',    'name': 'Europe (Frankfurt)',            'geo': 'EU', 'opt_in': False,
     'lzs': ['eu-central-1-cph-1a', 'eu-central-1-ham-1a',
             'eu-central-1-ist-1a', 'eu-central-1-waw-1a']},
    {'code': 'eu-central-2',    'name': 'Europe (Zurich)',               'geo': 'EU', 'opt_in': True,  'lzs': []},
    {'code': 'eu-west-1',       'name': 'Europe (Ireland)',              'geo': 'EU', 'opt_in': False, 'lzs': []},
    {'code': 'eu-west-2',       'name': 'Europe (London)',               'geo': 'EU', 'opt_in': False,
     'lzs': ['eu-west-2-man-1a']},
    {'code': 'eu-west-3',       'name': 'Europe (Paris)',                'geo': 'EU', 'opt_in': False, 'lzs': []},
    {'code': 'eu-north-1',      'name': 'Europe (Stockholm)',            'geo': 'EU', 'opt_in': False, 'lzs': []},
    {'code': 'eu-south-1',      'name': 'Europe (Milan)',                'geo': 'EU', 'opt_in': True,  'lzs': []},
    {'code': 'eu-south-2',      'name': 'Europe (Spain)',                'geo': 'EU', 'opt_in': True,  'lzs': []},
    {'code': 'ap-northeast-1',  'name': 'Asia Pacific (Tokyo)',          'geo': 'APAC', 'opt_in': False,
     'lzs': ['ap-northeast-1-tpe-1a']},
    {'code': 'ap-northeast-2',  'name': 'Asia Pacific (Seoul)',          'geo': 'APAC', 'opt_in': False, 'lzs': []},
    {'code': 'ap-northeast-3',  'name': 'Asia Pacific (Osaka)',          'geo': 'APAC', 'opt_in': False, 'lzs': []},
    {'code': 'ap-southeast-1',  'name': 'Asia Pacific (Singapore)',      'geo': 'APAC', 'opt_in': False,
     'lzs': ['ap-southeast-1-bkk-1a', 'ap-southeast-1-mnl-1a']},
    {'code': 'ap-southeast-2',  'name': 'Asia Pacific (Sydney)',         'geo': 'APAC', 'opt_in': False,
     'lzs': ['ap-southeast-2-akl-1a', 'ap-southeast-2-per-1a']},
    {'code': 'ap-southeast-3',  'name': 'Asia Pacific (Jakarta)',        'geo': 'APAC', 'opt_in': True,  'lzs': []},
    {'code': 'ap-southeast-4',  'name': 'Asia Pacific (Melbourne)',      'geo': 'APAC', 'opt_in': True,  'lzs': []},
    {'code': 'ap-south-1',      'name': 'Asia Pacific (Mumbai)',         'geo': 'APAC', 'opt_in': False,
     'lzs': ['ap-south-1-ccu-1a', 'ap-south-1-del-1a']},
    {'code': 'ap-south-2',      'name': 'Asia Pacific (Hyderabad)',      'geo': 'APAC', 'opt_in': True,  'lzs': []},
    {'code': 'ap-east-1',       'name': 'Asia Pacific (Hong Kong)',      'geo': 'APAC', 'opt_in': True,  'lzs': []},
    {'code': 'sa-east-1',       'name': 'South America (São Paulo)',     'geo': 'SA',   'opt_in': False,
     'lzs': ['sa-east-1-bue-1a', 'sa-east-1-lim-1a', 'sa-east-1-rio-1a']},
    {'code': 'af-south-1',      'name': 'Africa (Cape Town)',            'geo': 'AF',   'opt_in': True,  'lzs': []},
    {'code': 'me-south-1',      'name': 'Middle East (Bahrain)',         'geo': 'ME',   'opt_in': True,  'lzs': []},
    {'code': 'me-central-1',    'name': 'Middle East (UAE)',             'geo': 'ME',   'opt_in': True,  'lzs': []},
    {'code': 'il-central-1',    'name': 'Israel (Tel Aviv)',             'geo': 'ME',   'opt_in': True,  'lzs': []},
]

# Convenience lookup tables built once at import time.
REGIONS_BY_CODE = {r['code']: r for r in AWS_REGIONS}
LZ_BY_REGION    = {r['code']: r['lzs'] for r in AWS_REGIONS if r['lzs']}

# ---------------------------------------------------------------------------
# 3-letter Local Zone city code → friendly city name. Ported from
# aws_regions.go lzCityNames map.
# ---------------------------------------------------------------------------
LZ_CITY_NAMES = {
    'akl': 'Auckland', 'atl': 'Atlanta', 'bkk': 'Bangkok',
    'bos': 'Boston',   'bue': 'Buenos Aires', 'ccu': 'Kolkata',
    'chi': 'Chicago',  'cph': 'Copenhagen', 'del': 'Delhi',
    'den': 'Denver',   'dfw': 'Dallas',     'ham': 'Hamburg',
    'iah': 'Houston',  'ist': 'Istanbul',   'las': 'Las Vegas',
    'lax': 'Los Angeles', 'lim': 'Lima',    'man': 'Manchester',
    'mci': 'Kansas City', 'mia': 'Miami',   'mnl': 'Manila',
    'msp': 'Minneapolis', 'nyc': 'New York', 'pdx': 'Portland',
    'per': 'Perth',    'phl': 'Philadelphia', 'phx': 'Phoenix',
    'rio': 'Rio de Janeiro', 'sea': 'Seattle', 'tpe': 'Taipei',
    'waw': 'Warsaw',
}


# ---------------------------------------------------------------------------
# Generic Local Zone services catalog. Based on the ist-LZ-TEST Go reference
# (Istanbul LZ verified live), generalised to apply to any current-generation
# Local Zone. AWS keeps LZ service support roughly consistent across LZs:
# data-plane services (EC2, EBS, VPC, ALB, ECS/EKS data plane) work, control
# plane stays in the parent region, several services are region-only.
#
# Each entry: category, service, status (supported|partial|unsupported), notes.
# Notes use {city} placeholder which is substituted with the LZ's friendly
# city name (or 'this LZ' as fallback).
# ---------------------------------------------------------------------------
LZ_SERVICE_CATALOG = [
    # Compute
    {'category': 'Compute',  'service': 'Amazon EC2',                 'status': 'supported',   'notes': 'c7i and m7i families — verified live'},
    {'category': 'Compute',  'service': 'EC2 Auto Scaling',           'status': 'supported',   'notes': ''},
    {'category': 'Compute',  'service': 'Amazon ECS data plane',      'status': 'supported',   'notes': 'control plane in parent region'},
    {'category': 'Compute',  'service': 'Amazon EKS data plane',      'status': 'supported',   'notes': 'control plane in parent region'},
    {'category': 'Compute',  'service': 'AWS Lambda',                 'status': 'unsupported', 'notes': 'region-only; callable from LZ'},
    # Storage
    {'category': 'Storage',  'service': 'Amazon EBS (gp2/gp3/io1)',   'status': 'supported',   'notes': 'local volumes attached to LZ EC2'},
    {'category': 'Storage',  'service': 'Amazon S3',                  'status': 'unsupported', 'notes': 'regional only; LZ workloads cross the LZ↔region link'},
    {'category': 'Storage',  'service': 'Amazon EFS',                 'status': 'unsupported', 'notes': 'not available in {city} LZ'},
    {'category': 'Storage',  'service': 'Amazon FSx for Windows',     'status': 'unsupported', 'notes': 'not available in {city} LZ'},
    # Networking
    {'category': 'Networking', 'service': 'Amazon VPC',               'status': 'supported',   'notes': 'subnets, ENIs, EIPs, IGW, route tables'},
    {'category': 'Networking', 'service': 'Application Load Balancer','status': 'supported',   'notes': 'LZ-aware ALB'},
    {'category': 'Networking', 'service': 'Network Load Balancer',    'status': 'partial',     'notes': 'limited LZ availability'},
    {'category': 'Networking', 'service': 'Managed NAT Gateway',      'status': 'unsupported', 'notes': 'use a NAT instance'},
    {'category': 'Networking', 'service': 'AWS Direct Connect',       'status': 'supported',   'notes': 'via parent region; no LZ-direct DX'},
    {'category': 'Networking', 'service': 'AWS Transit Gateway',      'status': 'unsupported', 'notes': 'regional resource only'},
    {'category': 'Networking', 'service': 'VPC Endpoints (Interface)','status': 'partial',     'notes': 'limited service set in LZ'},
    # Containers
    {'category': 'Containers', 'service': 'Amazon ECR',               'status': 'supported',   'notes': 'image pull works; data path varies'},
    # Database
    {'category': 'Database',   'service': 'Amazon RDS',               'status': 'unsupported', 'notes': 'regional only; can be reached from LZ workloads'},
    {'category': 'Database',   'service': 'Amazon ElastiCache',       'status': 'unsupported', 'notes': 'not in {city} LZ'},
    {'category': 'Database',   'service': 'Amazon DynamoDB',          'status': 'unsupported', 'notes': 'regional only; callable from LZ'},
    # Security & Identity
    {'category': 'Security & Identity', 'service': 'AWS KMS',         'status': 'unsupported', 'notes': 'regional only; callable from LZ'},
    {'category': 'Security & Identity', 'service': 'AWS STS',         'status': 'unsupported', 'notes': 'regional only; callable from LZ'},
    {'category': 'Security & Identity', 'service': 'AWS Secrets Manager','status': 'unsupported','notes':'regional only; callable from LZ'},
    {'category': 'Security & Identity', 'service': 'AWS IAM',         'status': 'unsupported', 'notes': 'global control plane'},
    # Observability
    {'category': 'Observability', 'service': 'Amazon CloudWatch',     'status': 'unsupported', 'notes': 'regional only; metrics/logs ship to region'},
    {'category': 'Observability', 'service': 'AWS Systems Manager (SSM)','status':'unsupported','notes':'regional only; agent in LZ phones home'},
    # AI/ML
    {'category': 'AI/ML',      'service': 'Amazon Bedrock',           'status': 'unsupported', 'notes': 'regional only; LLM inference at parent region'},
]

# Generic LZ instance type offerings. AWS standardised current-gen LZs on the
# c7i / m7i families (Sapphire Rapids). Specific LZs may have different
# subsets — call DescribeInstanceTypeOfferings with real credentials to verify.
LZ_INSTANCE_TYPES_DEFAULT = [
    'c7i.large',  'c7i.xlarge',  'c7i.2xlarge',  'c7i.4xlarge',  'c7i.8xlarge',
    'c7i.12xlarge', 'c7i.16xlarge', 'c7i.24xlarge', 'c7i.48xlarge',
    'c7i.metal-24xl', 'c7i.metal-48xl',
    'm7i.large',  'm7i.xlarge',  'm7i.2xlarge',  'm7i.4xlarge',  'm7i.8xlarge',
    'm7i.12xlarge', 'm7i.16xlarge', 'm7i.24xlarge', 'm7i.48xlarge',
    'm7i.metal-24xl', 'm7i.metal-48xl',
]


def lz_city(lz_code: str) -> str:
    """Return the friendly city name for an LZ code, or 'this' if unknown.
        eu-central-1-ist-1a → 'Istanbul'
        unknown             → 'this'
    """
    parts = lz_code.split('-')
    if len(parts) >= 5:
        return LZ_CITY_NAMES.get(parts[3], 'this')
    return 'this'


def _norm_service_key(s: str) -> str:
    """Normalise a service name for fuzzy dedup between hand-curated entries,
    SERVICE_CATALOG entries, and the AWS regional-services JSON.

        'Amazon EBS (gp2/gp3/io1)'                      -> 'ebs'
        'Amazon ECS data plane'                         -> 'ecs'
        'Amazon ECS'                                    -> 'ecs'
        'Amazon Elastic Container Service (ECS)'        -> 'ecs'   ← abbrev
        'Amazon Simple Notification Service (SNS)'      -> 'sns'   ← abbrev
        'AWS Lambda'                                    -> 'lambda'
    """
    import re
    # If the name ends in "(ABBR)" where ABBR is an UPPERCASE acronym, treat
    # the acronym as canonical so "Amazon Simple Notification Service (SNS)"
    # collapses to the same key as "Amazon SNS".
    m = re.search(r'\(\s*([A-Z][A-Z0-9 ]*)\s*\)\s*$', s)
    if m:
        return m.group(1).strip().lower()
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s).strip().lower()
    s = re.sub(r'\s+data\s+plane\s*$', '', s)
    s = re.sub(r'^(amazon|aws)\s+', '', s)
    return s


# Map lz_scope → (default status, default note). Used to fill in services
# that exist in SERVICE_CATALOG but were never hand-curated in
# LZ_SERVICE_CATALOG so the LZ catalog table can show *every* AWS service.
_LZ_SCOPE_TO_STATUS = {
    'lz-data-plane': ('supported',   'data-plane available in LZ'),
    'lz-link-local': ('supported',   'link-local (IMDS) inside EC2'),
    'regional':      ('unsupported', 'regional only; callable from LZ'),
    'global':        ('unsupported', 'global control plane'),
}

# Normalise category labels — SERVICE_CATALOG and LZ_SERVICE_CATALOG drifted
# slightly (Network vs Networking, etc.). One canonical name per category.
_CATEGORY_CANONICAL = {
    'Network':                       'Networking',
    'Internal':                      'Networking',
    'AI/ML':                         'AI / ML',
    'Observability':                 'Observability & Management',
    'Security & Identity':           'Security & Identity',
}


def _infer_category(name: str) -> str:
    """Best-effort category inference from a service display name. Used when
    the AWS regional-services JSON adds services we don't have in our static
    catalog. Pattern-based — covers the ~190 services AWS publishes."""
    n = (name or '').lower()
    def _any(keywords):
        return any(k in n for k in keywords)

    if _any(['ec2', 'fargate', 'lambda', 'batch', 'wavelength', 'outposts',
             'app runner', 'auto scaling', 'lightsail', 'compute optimizer',
             'parallelcluster', 'serverless application repository']):
        return 'Compute'
    if _any(['ecr', 'ecs', 'eks', 'kubernetes', 'container', 'app2container',
             'app mesh', 'proton']):
        return 'Containers'
    if _any(['s3 ', 's3-', 's3$', 'ebs', 'efs', 'fsx', 'glacier', 'backup',
             'snow ', 'snowball', 'snowmobile', 'snowcone', 'datasync',
             'storage gateway', 'storage', 'simple storage', 'file cache']):
        return 'Storage'
    if _any(['rds', 'aurora', 'dynamodb', 'elasticache', 'memorydb',
             'documentdb', 'neptune', 'timestream', 'qldb', 'keyspaces',
             'database']):
        return 'Database'
    if _any(['vpc', 'route 53', 'cloudfront', 'direct connect', 'transit gateway',
             'load balanc', 'global accelerator', 'cloud map', 'privatelink',
             'private link', 'network firewall', 'site-to-site vpn',
             'client vpn', 'app mesh']):
        return 'Networking'
    if _any(['iam', 'kms', 'secrets manager', 'single sign-on', ' sso',
             'cognito', 'identity', 'detective', 'inspector', 'macie',
             'guardduty', 'security hub', 'cloudhsm', 'audit manager',
             'shield', 'waf', 'firewall manager', 'certificate manager',
             'private certificate', 'verified access', 'verified permissions',
             'resource access manager', 'security lake', 'artifact',
             'directory service', 'ad connector', 'simple ad', 'managed microsoft ad']):
        return 'Security & Identity'
    if _any(['cloudwatch', 'cloudtrail', 'config', 'x-ray', 'health dashboard',
             'service catalog', 'license manager', 'grafana', 'prometheus',
             'opensearch', 'control tower', 'launch wizard',
             'systems manager', 'fleet manager', 'application discovery',
             'application migration', 'mainframe modernization',
             'migration hub', 'observability']):
        return 'Observability & Management'
    if _any(['sagemaker', 'sage maker', 'bedrock', 'comprehend', 'rekognition',
             'transcribe', 'translate', 'polly', 'lex', 'forecast', 'kendra',
             'personalize', 'textract', 'augmented ai', 'monitron',
             'lookout', 'panorama', 'codeguru', 'codewhisperer', 'q ',
             'mechanical turk', 'fraud detector', 'healthimaging',
             'healthlake', 'omics', 'deepracer', 'deeplens', 'deepcomposer']):
        return 'AI / ML'
    if _any(['glue', 'emr', 'athena', 'redshift', 'lake formation',
             'quicksight', 'data exchange', 'data pipeline', 'datapipeline',
             'msk', 'managed streaming', 'kinesis', 'data zone', 'datazone',
             'opensearch service', 'finspace', 'cleanroom']):
        return 'Analytics'
    if _any(['sqs', 'sns', 'eventbridge', 'amq ', 'amazon mq', ' mq ', 'ses',
             'pinpoint', 'simple email', 'message', 'notification']):
        return 'Messaging'
    if _any(['amplify', 'mobile hub', 'device farm', 'appsync', 'app sync',
             'mobile sdk']):
        return 'Mobile & Frontend'
    if _any(['workspaces', 'appstream', 'workdocs', 'workmail', 'chime',
             'connect', 'wickr', 'supply chain']):
        return 'End User & Business'
    if _any(['cloudformation', 'cdk', ' sam ', 'codecommit', 'codebuild',
             'codedeploy', 'codepipeline', 'codestar', 'codecatalyst',
             'cloud9', 'cloudshell', 'x-ray', 'fault injection',
             'application composer', 'beanstalk', 'opsworks']):
        return 'Developer Tools'
    if _any(['marketplace', 'organizations', 'budget', 'cost explorer',
             'pricing', 'billing', 'savings plan', 'reserved',
             'support center', 'trusted advisor', 'service quotas',
             'license manager', 'tax settings']):
        return 'Management & Governance'
    if _any(['iot', 'freertos', 'greengrass', 'sitewise', 'fleetwise',
             'twin maker', 'twinmaker', 'roboMaker', 'robomaker']):
        return 'IoT & Robotics'
    if _any(['media live', 'medialive', 'mediaconvert', 'mediastore',
             'mediapackage', 'mediatailor', 'elemental', 'nimble studio',
             'ivs', 'interactive video', 'kinesis video']):
        return 'Media Services'
    if _any(['gamelift', 'open 3d', 'lumberyard']):
        return 'Game Tech'
    if _any(['ground station', 'satellite']):
        return 'Satellite'
    if _any(['quantum', 'braket']):
        return 'Quantum'
    if _any(['app config', 'appconfig', 'cloud directory', 'cloudendure',
             'data lifecycle', 'dms', 'database migration',
             'global network', 'mainframe']):
        return 'Management & Governance'
    return 'Other'


def lz_services_catalog(lz_code: str, regional_services: list = None) -> list:
    """Return the Local Zone services catalog with notes localised to the LZ's
    city. Three layers, merged in priority order:

      1. Hand-curated `LZ_SERVICE_CATALOG` entries (most accurate; nuanced
         supported/partial/unsupported status + bespoke notes).
      2. Auto-derived from `SERVICE_CATALOG` (status derived from lz_scope).
      3. (NEW) Auto-derived from AWS's public regional-services list — every
         service AWS publishes in the LZ's parent region (~190 services).
         These default to `unsupported` with "regional only; callable from LZ".

    Pass `regional_services` (a list of service display names available in the
    parent region) to enable layer 3. Without it, only layers 1+2 (≈40 rows).
    """
    city = lz_city(lz_code)

    out = []
    seen = set()
    # 1) Hand-curated entries (preserve nuance / exact notes)
    for e in LZ_SERVICE_CATALOG:
        entry = dict(e)
        entry['notes']    = (entry.get('notes') or '').replace('{city}', city)
        entry['category'] = _CATEGORY_CANONICAL.get(entry['category'], entry['category'])
        entry['source']   = 'curated'
        out.append(entry)
        seen.add(_norm_service_key(entry['service']))

    # 2) Auto-derived for every other service in the main internal catalog
    for svc in SERVICE_CATALOG:
        key = _norm_service_key(svc['name'])
        if key in seen:
            continue
        status, note = _LZ_SCOPE_TO_STATUS.get(svc['lz_scope'], ('unsupported', ''))
        cat = svc.get('category', 'Other')
        cat = _CATEGORY_CANONICAL.get(cat, cat)
        out.append({
            'category': cat,
            'service':  svc['name'],
            'status':   status,
            'notes':    note,
            'source':   'derived',
        })
        seen.add(key)

    # 3) AWS regional-services JSON — every AWS service published in the
    #    LZ's parent region. Default to unsupported (LZ workloads call them
    #    over the LZ↔region link).
    if regional_services:
        for name in regional_services:
            key = _norm_service_key(name)
            if key in seen:
                continue
            out.append({
                'category': _infer_category(name),
                'service':  name,
                'status':   'unsupported',
                'notes':    'regional only; callable from LZ',
                'source':   'aws-rt',
            })
            seen.add(key)

    return out


def lz_pretty(lz_az: str, parent_region: str) -> str:
    """Friendly label for a Local Zone AZ.
        eu-central-1-ist-1a → "Istanbul Local Zone (eu-central-1 · AZ a)"
    Mirrors lzPretty() in aws_regions.go.
    """
    rest = lz_az.removeprefix(parent_region + '-') if lz_az.startswith(parent_region + '-') else lz_az
    parts = rest.split('-', 1)
    if len(parts) < 2:
        return f'Local Zone ({parent_region})'
    code, az_part = parts
    city = LZ_CITY_NAMES.get(code, code.upper())
    az_letter = az_part[-1] if az_part else ''
    if az_letter:
        return f'{city} Local Zone ({parent_region} · AZ {az_letter})'
    return f'{city} Local Zone ({parent_region})'


def parent_region(s: str) -> str:
    """Strip an AZ letter or LZ suffix to return the parent region code.
        eu-central-1-ist-1a  → eu-central-1
        eu-central-1a        → eu-central-1
        eu-central-1         → eu-central-1
    """
    import re
    m = re.match(r'^([a-z]{2}-[a-z]+-\d+)', s)
    return m.group(1) if m else s


# ---------------------------------------------------------------------------
# AWS service catalog. Each service has:
#   - id            — short slug
#   - name          — display name
#   - category      — Compute / Storage / Network / Database / AI/ML / etc.
#   - endpoint      — DNS host (region template '{region}'); None for global
#   - port          — TCP port (almost always 443; IMDS uses 80)
#   - lz_scope      — 'lz-data-plane' | 'lz-link-local' | 'regional' | 'global'
#                     Determines availability inside Local Zones:
#                       lz-data-plane → runs locally in LZ (EC2, ELB, EBS)
#                       lz-link-local → only from inside LZ host (IMDS)
#                       regional      → callable from LZ but data plane in
#                                       parent region (S3, RDS, KMS, ...)
#                       global        → IAM, STS-global, Route53
#   - description_en / description_tr — short bilingual blurbs
# ---------------------------------------------------------------------------
SERVICE_CATALOG = [
    # Compute
    {'id': 'ec2',            'name': 'Amazon EC2',
     'category': 'Compute',  'endpoint': 'ec2.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'lz-data-plane',
     'description_en': 'Elastic Compute Cloud — virtual machines.',
     'description_tr': 'Elastic Compute Cloud — sanal makineler.'},
    {'id': 'autoscaling',    'name': 'EC2 Auto Scaling',
     'category': 'Compute',  'endpoint': 'autoscaling.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'lz-data-plane',
     'description_en': 'Automatic EC2 fleet scaling.',
     'description_tr': 'Otomatik EC2 filo ölçeklendirme.'},
    {'id': 'ecs',            'name': 'Amazon ECS',
     'category': 'Compute',  'endpoint': 'ecs.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'lz-data-plane',
     'description_en': 'Container orchestration — data plane LZ-local, control plane regional.',
     'description_tr': 'Konteyner orkestrasyon — veri düzlemi LZ-yerel, kontrol düzlemi bölgesel.'},
    {'id': 'eks',            'name': 'Amazon EKS',
     'category': 'Compute',  'endpoint': 'eks.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'lz-data-plane',
     'description_en': 'Managed Kubernetes — data plane LZ-local, control plane regional.',
     'description_tr': 'Yönetimli Kubernetes — veri düzlemi LZ-yerel, kontrol düzlemi bölgesel.'},
    {'id': 'lambda',         'name': 'AWS Lambda',
     'category': 'Compute',  'endpoint': 'lambda.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Serverless functions — region-only; callable from LZ workloads.',
     'description_tr': 'Sunucusuz fonksiyonlar — yalnızca bölgesel; LZ\'den çağrılabilir.'},
    {'id': 'batch',          'name': 'AWS Batch',
     'category': 'Compute',  'endpoint': 'batch.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Batch job scheduling.',
     'description_tr': 'Toplu iş zamanlama.'},

    # Storage
    {'id': 'ebs',            'name': 'Amazon EBS',
     'category': 'Storage',  'endpoint': 'ec2.{region}.amazonaws.com',  # EBS uses EC2 API
     'port': 443, 'lz_scope': 'lz-data-plane',
     'description_en': 'Block storage volumes for EC2 — LZ-local volumes available.',
     'description_tr': 'EC2 için blok depolama — LZ-yerel volume\'lar mevcut.'},
    {'id': 's3',             'name': 'Amazon S3',
     'category': 'Storage',  'endpoint': 's3.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Object storage — regional; LZ workloads cross the LZ↔region link.',
     'description_tr': 'Nesne depolama — bölgesel; LZ iş yükleri LZ↔bölge bağlantısını kullanır.'},
    {'id': 's3-dualstack',   'name': 'Amazon S3 (Dual-stack)',
     'category': 'Storage',  'endpoint': 's3.dualstack.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'IPv4/IPv6 dual-stack S3 endpoint.',
     'description_tr': 'IPv4/IPv6 çift-yığın S3 endpoint\'i.'},
    {'id': 'efs',            'name': 'Amazon EFS',
     'category': 'Storage',  'endpoint': 'elasticfilesystem.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Elastic File System — regional; not in most LZs.',
     'description_tr': 'Elastic File System — bölgesel; çoğu LZ\'de yok.'},
    {'id': 'fsx',            'name': 'Amazon FSx',
     'category': 'Storage',  'endpoint': 'fsx.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Managed file systems (Windows, Lustre, NetApp ONTAP).',
     'description_tr': 'Yönetimli dosya sistemleri (Windows, Lustre, NetApp ONTAP).'},

    # Network
    {'id': 'elb',            'name': 'Elastic Load Balancing',
     'category': 'Network',  'endpoint': 'elasticloadbalancing.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'lz-data-plane',
     'description_en': 'ALB and NLB — ALB is LZ-aware; NLB partial in LZs.',
     'description_tr': 'ALB ve NLB — ALB LZ-uyumlu; NLB LZ\'lerde kısmen.'},
    {'id': 'vpc',            'name': 'Amazon VPC',
     'category': 'Network',  'endpoint': 'ec2.{region}.amazonaws.com',  # VPC uses EC2 API
     'port': 443, 'lz_scope': 'lz-data-plane',
     'description_en': 'Virtual Private Cloud — subnets, ENIs, EIPs, IGWs, route tables.',
     'description_tr': 'Sanal Özel Bulut — subnet\'ler, ENI\'ler, EIP\'ler, IGW\'ler, route table\'lar.'},
    {'id': 'route53',        'name': 'Amazon Route 53',
     'category': 'Network',  'endpoint': 'route53.amazonaws.com',  # global endpoint
     'port': 443, 'lz_scope': 'global',
     'description_en': 'DNS — global control plane.',
     'description_tr': 'DNS — küresel kontrol düzlemi.'},
    {'id': 'cloudfront',     'name': 'Amazon CloudFront',
     'category': 'Network',  'endpoint': 'cloudfront.amazonaws.com',  # global
     'port': 443, 'lz_scope': 'global',
     'description_en': 'Global CDN — edge locations worldwide.',
     'description_tr': 'Küresel CDN — dünyaca uç noktalar.'},
    {'id': 'directconnect',  'name': 'AWS Direct Connect',
     'category': 'Network',  'endpoint': 'directconnect.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Dedicated network — LZs via parent region.',
     'description_tr': 'Adanmış ağ — LZ\'ler ana bölge üzerinden.'},
    {'id': 'transit-gateway','name': 'AWS Transit Gateway',
     'category': 'Network',  'endpoint': 'ec2.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Regional network hub — not in LZs.',
     'description_tr': 'Bölgesel ağ hub\'ı — LZ\'lerde yok.'},

    # Database
    {'id': 'rds',            'name': 'Amazon RDS',
     'category': 'Database', 'endpoint': 'rds.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Managed relational databases — regional only.',
     'description_tr': 'Yönetimli ilişkisel veritabanları — yalnızca bölgesel.'},
    {'id': 'dynamodb',       'name': 'Amazon DynamoDB',
     'category': 'Database', 'endpoint': 'dynamodb.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'NoSQL document/key-value store — regional, callable from LZs.',
     'description_tr': 'NoSQL belge/anahtar-değer depolama — bölgesel, LZ\'den çağrılabilir.'},
    {'id': 'elasticache',    'name': 'Amazon ElastiCache',
     'category': 'Database', 'endpoint': 'elasticache.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Managed Redis / Memcached — regional.',
     'description_tr': 'Yönetimli Redis / Memcached — bölgesel.'},
    {'id': 'aurora',         'name': 'Amazon Aurora',
     'category': 'Database', 'endpoint': 'rds.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'MySQL/PostgreSQL-compatible cloud DB.',
     'description_tr': 'MySQL/PostgreSQL uyumlu bulut DB.'},

    # Containers
    {'id': 'ecr',            'name': 'Amazon ECR',
     'category': 'Containers', 'endpoint': 'api.ecr.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Container image registry. Pulls work; data path varies.',
     'description_tr': 'Konteyner imaj kayıt defteri. Pull çalışır; veri yolu değişir.'},
    {'id': 'ecr-dkr',        'name': 'Amazon ECR (Docker)',
     'category': 'Containers', 'endpoint': 'dkr.ecr.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Docker-compatible ECR endpoint for image pulls.',
     'description_tr': 'İmaj çekmek için Docker-uyumlu ECR endpoint\'i.'},

    # Security & Identity
    {'id': 'iam',            'name': 'AWS IAM',
     'category': 'Security & Identity', 'endpoint': 'iam.amazonaws.com',  # global
     'port': 443, 'lz_scope': 'global',
     'description_en': 'Identity and Access Management — global control plane.',
     'description_tr': 'Kimlik ve Erişim Yönetimi — küresel kontrol düzlemi.'},
    {'id': 'sts',            'name': 'AWS STS',
     'category': 'Security & Identity', 'endpoint': 'sts.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Security Token Service — regional endpoints.',
     'description_tr': 'Security Token Service — bölgesel endpoint\'ler.'},
    {'id': 'kms',            'name': 'AWS KMS',
     'category': 'Security & Identity', 'endpoint': 'kms.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Key Management Service — regional.',
     'description_tr': 'Anahtar Yönetim Servisi — bölgesel.'},
    {'id': 'secretsmanager', 'name': 'AWS Secrets Manager',
     'category': 'Security & Identity', 'endpoint': 'secretsmanager.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Managed secret rotation and retrieval.',
     'description_tr': 'Yönetimli sır rotasyonu ve erişimi.'},

    # Messaging
    {'id': 'sqs',            'name': 'Amazon SQS',
     'category': 'Messaging', 'endpoint': 'sqs.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Simple Queue Service.',
     'description_tr': 'Basit Kuyruk Servisi.'},
    {'id': 'sns',            'name': 'Amazon SNS',
     'category': 'Messaging', 'endpoint': 'sns.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Simple Notification Service.',
     'description_tr': 'Basit Bildirim Servisi.'},
    {'id': 'eventbridge',    'name': 'Amazon EventBridge',
     'category': 'Messaging', 'endpoint': 'events.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Event bus and rule-based routing.',
     'description_tr': 'Olay otobüsü ve kural tabanlı yönlendirme.'},

    # Observability
    {'id': 'cloudwatch',     'name': 'Amazon CloudWatch',
     'category': 'Observability', 'endpoint': 'monitoring.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Metrics and alarms — LZ resources ship to parent region.',
     'description_tr': 'Metrikler ve alarmlar — LZ kaynakları ana bölgeye gönderir.'},
    {'id': 'cwlogs',         'name': 'CloudWatch Logs',
     'category': 'Observability', 'endpoint': 'logs.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Centralised application logs.',
     'description_tr': 'Merkezi uygulama günlükleri.'},
    {'id': 'ssm',            'name': 'AWS Systems Manager',
     'category': 'Observability', 'endpoint': 'ssm.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Operations management — regional.',
     'description_tr': 'Operasyon yönetimi — bölgesel.'},

    # AI/ML
    {'id': 'bedrock',        'name': 'Amazon Bedrock',
     'category': 'AI/ML',    'endpoint': 'bedrock.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Foundation model API — regional inference.',
     'description_tr': 'Foundation model API\'si — bölgesel çıkarım.'},
    {'id': 'bedrock-runtime', 'name': 'Bedrock Runtime',
     'category': 'AI/ML',    'endpoint': 'bedrock-runtime.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Real-time model invocation endpoint.',
     'description_tr': 'Gerçek zamanlı model çağırma endpoint\'i.'},
    {'id': 'sagemaker',      'name': 'Amazon SageMaker',
     'category': 'AI/ML',    'endpoint': 'api.sagemaker.{region}.amazonaws.com',
     'port': 443, 'lz_scope': 'regional',
     'description_en': 'Managed ML platform — regional.',
     'description_tr': 'Yönetimli ML platformu — bölgesel.'},

    # Link-local (LZ workloads only — won't probe from a generic host)
    {'id': 'imds',           'name': 'IMDS (Instance Metadata)',
     'category': 'Internal', 'endpoint': '169.254.169.254',
     'port': 80, 'lz_scope': 'lz-link-local',
     'description_en': 'Instance Metadata Service — accessible only from EC2/LZ instances.',
     'description_tr': 'Instance Metadata Servisi — yalnızca EC2/LZ instance\'larından erişilebilir.'},
]


def services_for_region(region_code: str, include_lz_link_local: bool = False) -> list:
    """Return service catalog entries with rendered endpoint host for the
    given region. `include_lz_link_local` controls whether the IMDS-style
    link-local entries are included (typically False for public reference)."""
    out = []
    parent = parent_region(region_code)
    for svc in SERVICE_CATALOG:
        if svc['lz_scope'] == 'lz-link-local' and not include_lz_link_local:
            continue
        ep = svc['endpoint']
        if '{region}' in ep:
            ep = ep.format(region=parent)
        out.append({
            **svc,
            'endpoint':   ep,
            'is_global':  svc['lz_scope'] == 'global',
            'is_regional': svc['lz_scope'] in ('regional', 'lz-data-plane'),
        })
    return out


def all_region_entries(include_lzs: bool = True) -> list:
    """Flatten regions + LZ children into a single list of {code, name, type,
    parent, endpoint} suitable for the Region Matrix. Each row's S3 endpoint
    is used as a stable, public TCP probe target."""
    rows = []
    for r in AWS_REGIONS:
        rows.append({
            'code':     r['code'],
            'name':     r['name'],
            'type':     'region',
            'geo':      r['geo'],
            'opt_in':   r['opt_in'],
            'parent':   None,
            'endpoint': f"s3.{r['code']}.amazonaws.com",
        })
        if include_lzs:
            for lz in r.get('lzs', []):
                rows.append({
                    'code':     lz,
                    'name':     lz_pretty(lz, r['code']),
                    'type':     'local-zone',
                    'geo':      r['geo'],
                    'opt_in':   r['opt_in'],
                    'parent':   r['code'],
                    # LZs share the parent region's S3 endpoint — they don't
                    # have their own. This matches the Go reference behaviour.
                    'endpoint': f"s3.{r['code']}.amazonaws.com",
                })
    return rows
