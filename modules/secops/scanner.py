"""
SecOps — Main Scanner / Orchestrator
Runs all inventory checks in parallel threads and returns aggregated results.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
import boto3
from datetime import date, timedelta
from botocore.exceptions import ProfileNotFound, NoCredentialsError

from .inventory import (
    iam, s3, ec2, vpc, cloudtrail, guardduty, rds, kms, lambda_, config_,
    secretsmanager, dynamodb, sqs, sns, ecs, elb, eks, cloudfront,
    cloudwatch, waf, route53, acm, ecr, efs,
)
from .inventory.base import make_finding
from . import cache

# Module-level scan progress tracker, keyed by profile name
_scan_progress = {}

# Concurrency control — prevent duplicate scans for the same profile
# Stores {profile: start_timestamp} for auto-release after 1 hour
_active_scans = {}
_active_scans_lock = threading.Lock()
_SCAN_LOCK_TIMEOUT = 3600  # 1 hour max scan duration before auto-release

# Framework definitions: control catalog for scoring labels
FRAMEWORKS = {
    'WAFR': {
        'label': 'AWS Well-Architected',
        'pillars': ['Security', 'Operational Excellence', 'Reliability',
                    'Performance Efficiency', 'Cost Optimization', 'Sustainability'],
    },
    'CIS':     {'label': 'CIS AWS Foundations Benchmark v3'},
    'HIPAA':   {'label': 'HIPAA Security Rule'},
    'ISO27001':{'label': 'ISO/IEC 27001:2022'},
}

# All services that have dedicated check modules
SERVICES_ORDER = [
    'IAM', 'S3', 'EC2', 'VPC', 'CloudTrail', 'GuardDuty', 'RDS', 'KMS',
    'Lambda', 'Config', 'SecretsManager', 'DynamoDB', 'SQS', 'SNS',
    'ECS', 'EKS', 'ELB', 'CloudFront',
    'CloudWatch', 'WAF', 'Route53', 'ACM', 'ECR', 'EFS',
]

# Severity weights for weighted risk score (CRITICAL counts 10×, INFO counts 1×)
SEV_WEIGHTS = {'CRITICAL': 10, 'HIGH': 7, 'MEDIUM': 4, 'LOW': 2, 'INFO': 1}

# ---------------------------------------------------------------------------
# Cost Explorer → canonical service name mapping
# Maps CE verbose names to our module service names (or None = no module yet)
# ---------------------------------------------------------------------------
CE_SERVICE_MAP = {
    # Covered by existing modules
    'Amazon Elastic Compute Cloud - Compute': 'EC2',
    'Amazon EC2': 'EC2',
    'EC2 - Other': 'EC2',
    'Amazon Simple Storage Service': 'S3',
    'AWS Lambda': 'Lambda',
    'Amazon Relational Database Service': 'RDS',
    'AWS Key Management Service': 'KMS',
    'AWS CloudTrail': 'CloudTrail',
    'Amazon GuardDuty': 'GuardDuty',
    'Amazon Virtual Private Cloud': 'VPC',
    'Amazon VPC': 'VPC',
    'AWS Identity and Access Management': 'IAM',
    'AWS Config': 'Config',
    # Covered by new modules
    'AWS Secrets Manager': 'SecretsManager',
    'Amazon DynamoDB': 'DynamoDB',
    'Amazon Simple Queue Service': 'SQS',
    'Amazon Simple Notification Service': 'SNS',
    'Amazon Elastic Container Service': 'ECS',
    'AWS Fargate': 'ECS',
    'Elastic Load Balancing': 'ELB',
    # Covered by new modules
    'Amazon Elastic Kubernetes Service': 'EKS',
    'Amazon CloudFront': 'CloudFront',
    'CloudFront': 'CloudFront',
    # Covered by new modules
    'Amazon CloudWatch': 'CloudWatch',
    'AWS WAF': 'WAF',
    'AWS WAFv2': 'WAF',
    'Amazon Route 53': 'Route53',
    'AWS Certificate Manager': 'ACM',
    'Amazon Elastic Container Registry': 'ECR',
    'Amazon ECR Public': 'ECR',
    'Amazon Elastic File System': 'EFS',
    # Not yet covered → will get MANUAL finding
    'Amazon API Gateway': 'APIGateway',
    'Amazon ElastiCache': 'ElastiCache',
    'Amazon OpenSearch Service': 'OpenSearch',
    'Amazon Elasticsearch Service': 'OpenSearch',
    'Amazon Kinesis': 'Kinesis',
    'Amazon Kinesis Firehose': 'Kinesis',
    'Amazon Kinesis Data Streams': 'Kinesis',
    'Amazon Redshift': 'Redshift',
    'Amazon Athena': 'Athena',
    'AWS Glue': 'Glue',
    'Amazon EMR': 'EMR',
    'Amazon SageMaker': 'SageMaker',
    'AWS CodeBuild': 'CodeBuild',
    'AWS CodePipeline': 'CodePipeline',
    'Amazon EventBridge': 'EventBridge',
    'AWS Step Functions': 'StepFunctions',
    'Amazon Cognito': 'Cognito',
    'AWS Shield': 'Shield',
    'Amazon EFS': 'EFS',
    'Amazon FSx': 'FSx',
    'Amazon WorkSpaces': 'WorkSpaces',
    'Amazon AppStream': 'AppStream',
    'AWS Direct Connect': 'DirectConnect',
    'AWS Transit Gateway': 'TransitGateway',
    'Amazon MSK': 'MSK',
    'Amazon MQ': 'MQ',
    'AWS Backup': 'Backup',
    'Amazon Inspector': 'Inspector',
    'AWS Security Hub': 'SecurityHub',
    'Amazon Macie': 'Macie',
    'AWS Systems Manager': 'SSM',
    'AWS CloudFormation': 'CloudFormation',
    'Amazon ECR Public': 'ECR',
    'Amazon Lightsail': 'Lightsail',
    'Amazon AppFlow': 'AppFlow',
    'AWS DataSync': 'DataSync',
    'Amazon Comprehend': 'Comprehend',
    'Amazon Rekognition': 'Rekognition',
    'Amazon Textract': 'Textract',
    'Amazon Translate': 'Translate',
    'Amazon Polly': 'Polly',
    'Amazon Lex': 'Lex',
    'Amazon Transcribe': 'Transcribe',
    'Amazon Personalize': 'Personalize',
    'Amazon Forecast': 'Forecast',
    'Amazon Fraud Detector': 'FraudDetector',
    'Amazon DevOps Guru': 'DevOpsGuru',
    'AWS Amplify': 'Amplify',
    'Amazon AppSync': 'AppSync',
    'Amazon Pinpoint': 'Pinpoint',
    'Amazon SES': 'SES',
    'Amazon Chime': 'Chime',
    'AWS IoT Core': 'IoT',
    'AWS Batch': 'Batch',
    'Amazon Glacier': 'S3Glacier',
    'Amazon S3 Glacier': 'S3Glacier',
    'AWS Database Migration Service': 'DMS',
    'Amazon Aurora': 'RDS',
    'Amazon Neptune': 'Neptune',
    'Amazon DocumentDB': 'DocumentDB',
    'Amazon Timestream': 'Timestream',
    'Amazon MemoryDB': 'MemoryDB',
    'Amazon QLDB': 'QLDB',
    'Amazon Managed Grafana': 'Grafana',
    'Amazon Managed Service for Prometheus': 'Prometheus',
    'Amazon Location Service': 'Location',
    'AWS Ground Station': 'GroundStation',
    'Amazon Braket': 'Braket',
}

# Services that have dedicated check modules
MODULES_WITH_CHECKS = set(SERVICES_ORDER)

# Core security services — ALWAYS scan regardless of CE usage
# These are foundational and should be enabled/checked in every account
ALWAYS_SCAN = {
    'IAM', 'S3', 'EC2', 'VPC', 'CloudTrail', 'GuardDuty',
    'Config', 'CloudWatch', 'KMS',
}

# Maps our module names to Cost Explorer service name patterns
_MODULE_TO_CE_PATTERNS = {
    'RDS':            ['Relational Database', 'Amazon Aurora'],
    'Lambda':         ['AWS Lambda'],
    'SecretsManager': ['AWS Secrets Manager'],
    'DynamoDB':       ['Amazon DynamoDB'],
    'SQS':            ['Simple Queue Service'],
    'SNS':            ['Simple Notification Service'],
    'ECS':            ['Elastic Container Service', 'AWS Fargate'],
    'EKS':            ['Elastic Kubernetes'],
    'ELB':            ['Elastic Load Balancing'],
    'CloudFront':     ['Amazon CloudFront', 'CloudFront'],
    'WAF':            ['AWS WAF'],
    'Route53':        ['Amazon Route 53'],
    'ACM':            ['AWS Certificate Manager'],
    'ECR':            ['Elastic Container Registry'],
    'EFS':            ['Elastic File System'],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_scan(profile: str, exclude_defaults: bool = False, regions: list = None) -> dict:
    """
    Execute all checks for the given AWS profile.
    Returns a dict with findings, summary, framework scores, service scores, inventory.
    Caches the result per profile.
    """
    started = time.time()

    # Concurrency control — prevent duplicate scans for the same profile
    with _active_scans_lock:
        if profile in _active_scans:
            # Auto-release stale locks older than 1 hour
            if time.time() - _active_scans[profile] > _SCAN_LOCK_TIMEOUT:
                _active_scans.pop(profile, None)
            else:
                return {'status': 'error', 'error': 'A scan is already running for this profile'}
        _active_scans[profile] = time.time()

    try:
        _scan_progress[profile] = {'service': 'authenticating', 'completed': 0, 'total': 0}
        try:
            session = boto3.Session(profile_name=profile)
            # Quick identity check
            sts = session.client('sts', region_name='us-east-1')
            identity = sts.get_caller_identity()
            account_id = identity.get('Account', 'unknown')
        except (ProfileNotFound, NoCredentialsError) as exc:
            _scan_progress.pop(profile, None)
            return {'status': 'error', 'error': str(exc)}
        except Exception as exc:
            _scan_progress.pop(profile, None)
            return {'status': 'error', 'error': str(exc)}

        # Discover active services from Cost Explorer
        _scan_progress[profile] = {'service': 'detecting active services', 'completed': 0, 'total': 24}
        active_ce_services = _get_active_ce_services(session)

        # Build module list — always scan core security + only active optional services
        all_modules = [
            ('IAM',            iam.run_checks),
            ('S3',             s3.run_checks),
            ('EC2',            ec2.run_checks),
            ('VPC',            vpc.run_checks),
            ('CloudTrail',     cloudtrail.run_checks),
            ('GuardDuty',      guardduty.run_checks),
            ('RDS',            rds.run_checks),
            ('KMS',            kms.run_checks),
            ('Lambda',         lambda_.run_checks),
            ('Config',         config_.run_checks),
            ('SecretsManager', secretsmanager.run_checks),
            ('DynamoDB',       dynamodb.run_checks),
            ('SQS',            sqs.run_checks),
            ('SNS',            sns.run_checks),
            ('ECS',            ecs.run_checks),
            ('EKS',            eks.run_checks),
            ('ELB',            elb.run_checks),
            ('CloudFront',     cloudfront.run_checks),
            ('CloudWatch',     cloudwatch.run_checks),
            ('WAF',            waf.run_checks),
            ('Route53',        route53.run_checks),
            ('ACM',            acm.run_checks),
            ('ECR',            ecr.run_checks),
            ('EFS',            efs.run_checks),
        ]

        # Filter: core services always run, optional services only if active in CE
        modules = []
        skipped = []
        for name, fn in all_modules:
            if name in ALWAYS_SCAN or name in active_ce_services:
                modules.append((name, fn))
            else:
                skipped.append(name)

        # Run all service checks in parallel
        all_findings = []
        errors       = {}
        lock         = threading.Lock()

        total_modules = len(modules)
        completed_count = [0]
        _scan_progress[profile] = {'service': 'starting', 'completed': 0, 'total': total_modules}

        def run_module(name, fn):
            try:
                result = fn(session, exclude_defaults=exclude_defaults, regions=regions or None)
                with lock:
                    all_findings.extend(result)
            except Exception as exc:
                with lock:
                    errors[name] = str(exc)
            finally:
                with lock:
                    completed_count[0] += 1
                    # Update progress tracker
                    if profile in _scan_progress:
                        _scan_progress[profile] = {
                            'service': name,
                            'completed': completed_count[0],
                            'total': total_modules,
                        }

        # Start CE unchecked-services query in parallel with module scans
        ce_future = None
        ce_executor = ThreadPoolExecutor(max_workers=1)
        ce_future = ce_executor.submit(_get_unchecked_ce_services, session, account_id)

        with ThreadPoolExecutor(max_workers=min(len(modules), 12)) as executor:
            futures = [executor.submit(run_module, name, fn) for name, fn in modules]
            for future in futures:
                future.result()  # wait for completion

        # Collect CE findings (already running in parallel)
        try:
            ce_findings = ce_future.result(timeout=30)
            all_findings.extend(ce_findings)
        except Exception:
            pass  # CE failure is non-fatal
        finally:
            ce_executor.shutdown(wait=False)

        elapsed = round(time.time() - started, 1)

        results = _aggregate(all_findings, errors, profile, account_id,
                             exclude_defaults, elapsed, skipped)

        # Cache scan result
        cache.save_scan(profile, results)

        return results
    finally:
        _scan_progress.pop(profile, None)
        with _active_scans_lock:
            _active_scans.pop(profile, None)


def get_last_scan(profile: str) -> tuple:
    """Return (results, age_seconds) from cache. results=None if no cache."""
    return cache.load_scan(profile)


def init_progress(profile: str):
    """Initialize progress tracker for a profile scan."""
    _scan_progress[profile] = {'service': 'starting', 'completed': 0, 'total': 0}


def get_progress(profile: str) -> dict | None:
    """Return current progress for a profile scan."""
    return _scan_progress.get(profile)


def clear_progress(profile: str):
    """Remove progress tracker for a profile."""
    _scan_progress.pop(profile, None)


# ---------------------------------------------------------------------------
# Cost Explorer — discover unchecked active services
# ---------------------------------------------------------------------------

def _get_active_ce_services(session) -> set:
    """Query Cost Explorer to find which services have non-zero spend in the last 30 days.
    Returns a set of our module names that are active."""
    active_modules = set()
    try:
        ce    = session.client('ce', region_name='us-east-1')
        end   = date.today()
        start = end - timedelta(days=30)
        resp  = ce.get_cost_and_usage(
            TimePeriod={'Start': str(start), 'End': str(end)},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Metrics=['UnblendedCost'],
        )

        active_ce_names = set()
        for result in resp.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                ce_name = group['Keys'][0]
                amount  = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount > 0:
                    active_ce_names.add(ce_name)

        # Map CE names to our module names
        for module_name, patterns in _MODULE_TO_CE_PATTERNS.items():
            for ce_name in active_ce_names:
                if any(pat.lower() in ce_name.lower() for pat in patterns):
                    active_modules.add(module_name)
                    break

    except Exception:
        # If CE fails, scan everything (safe fallback)
        return set(SERVICES_ORDER)

    return active_modules


def _get_unchecked_ce_services(session, account_id: str) -> list:
    """
    Query Cost Explorer for services active in the last 30 days.
    For any service that has no dedicated check module, emit one MANUAL finding.
    """
    findings = []
    try:
        ce    = session.client('ce', region_name='us-east-1')
        end   = date.today()
        start = end - timedelta(days=30)
        resp  = ce.get_cost_and_usage(
            TimePeriod={'Start': str(start), 'End': str(end)},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Metrics=['UnblendedCost'],
        )

        # Collect services with non-zero spend
        active_ce_names = set()
        for result in resp.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                ce_name = group['Keys'][0]
                amount  = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount > 0:
                    active_ce_names.add(ce_name)

        # Map to canonical names and find unchecked ones
        unchecked = {}  # canonical_name → ce_name
        for ce_name in active_ce_names:
            canonical = CE_SERVICE_MAP.get(ce_name)
            if canonical is None:
                # Not in our map at all — use a cleaned CE name
                canonical = ce_name.replace('Amazon ', '').replace('AWS ', '').replace(' ', '')[:30]
            if canonical not in MODULES_WITH_CHECKS:
                if canonical not in unchecked:
                    unchecked[canonical] = ce_name

        for canonical, ce_name in sorted(unchecked.items()):
            findings.append(make_finding(
                id=f'unchecked_service_{canonical.lower()}',
                title=f'{canonical}: No automated security checks',
                title_tr=f'{canonical}: Otomatik güvenlik kontrolü yok',
                description=(
                    f'{ce_name} is actively used in this account (detected via Cost Explorer) '
                    f'but has no automated security checks implemented. Manual review is required.'
                ),
                description_tr=(
                    f'{ce_name} bu hesapta aktif olarak kullanılıyor (Cost Explorer ile tespit edildi) '
                    f'ancak otomatik güvenlik kontrolleri uygulanmamış. Manuel inceleme gereklidir.'
                ),
                severity='INFO',
                status='MANUAL',
                service=canonical,
                resource_id=account_id,
                resource_type=f'AWS::{canonical}',
                region='global',
                frameworks={'WAFR': {'pillar': 'Security', 'controls': ['SEC01']}},
                remediation=(
                    f'Manually review the security configuration of {canonical}. '
                    f'Check IAM permissions, encryption settings, and network exposure.'
                ),
                remediation_tr=(
                    f'{canonical} servisinin güvenlik yapılandırmasını manuel olarak inceleyin. '
                    f'IAM izinlerini, şifreleme ayarlarını ve ağ erişimini kontrol edin.'
                ),
            ))

    except Exception:
        pass  # CE access failure is non-fatal

    return findings


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate(findings, errors, profile, account_id,
                exclude_defaults, elapsed, skipped=None) -> dict:

    # Apply default-resource exclusion filter
    visible = [f for f in findings
               if not (exclude_defaults and f.get('is_default_resource', False))]

    # Overall severity counts
    sev_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0}
    status_counts = {'PASS': 0, 'FAIL': 0, 'WARNING': 0, 'NOT_AVAILABLE': 0, 'MANUAL': 0}
    for f in visible:
        sev = f.get('severity', 'INFO')
        st  = f.get('status',   'NOT_AVAILABLE')
        if sev in sev_counts:   sev_counts[sev] += 1
        if st  in status_counts: status_counts[st] += 1

    total    = len(visible)
    passed   = status_counts['PASS']
    # WARNING counts as 0.5 failure in base score (less severe than FAIL)
    effective_denom = status_counts['PASS'] + status_counts['FAIL'] + status_counts['WARNING'] * 0.5
    score    = round(passed / effective_denom * 100, 1) if effective_denom else 0
    score    = min(score, 100.0)  # cap at 100
    weighted_score = _weighted_score(visible)

    # Coverage score: % of checked services vs total active (including MANUAL)
    checked_svcs = {f.get('service') for f in visible
                    if f.get('status') in ('PASS', 'FAIL', 'WARNING')}
    manual_svcs  = {f.get('service') for f in visible if f.get('status') == 'MANUAL'}
    all_active   = checked_svcs | manual_svcs
    coverage_score = round(len(checked_svcs) / len(all_active) * 100, 1) if all_active else 100

    # Per-framework scores
    framework_scores = _score_frameworks(visible)

    # Per-service scores (dynamic — include any service appearing in findings)
    service_scores = _score_services(visible)

    # Inventory counts
    inventory = _count_inventory(visible)

    # Scanned vs skipped services info
    scanned_services = sorted({f.get('service', '') for f in visible if f.get('service')})

    return {
        'status':          'ok',
        'profile':         profile,
        'account_id':      account_id,
        'scan_time':       time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'elapsed_seconds': elapsed,
        'exclude_defaults':exclude_defaults,
        'errors':          errors,
        'skipped_services': skipped or [],
        'scanned_services': scanned_services,
        'summary': {
            'total':          total,
            'score':          score,
            'weighted_score': weighted_score,
            'coverage_score': coverage_score,
            'passed':         passed,
            'failed':         status_counts['FAIL'],
            'warnings':       status_counts['WARNING'],
            'not_available':  status_counts['NOT_AVAILABLE'],
            'manual':         status_counts['MANUAL'],
            'severity':       sev_counts,
        },
        'frameworks':      framework_scores,
        'services':        service_scores,
        'inventory':       inventory,
        'findings':        visible,
    }


def _weighted_score(findings):
    """Severity-weighted compliance score.
    PASS = full weight, FAIL = full weight, WARNING = 0.5× weight in denominator.
    """
    w_pass = w_total = 0
    for f in findings:
        st = f.get('status')
        if st not in ('PASS', 'FAIL', 'WARNING'):
            continue  # skip NOT_AVAILABLE and MANUAL
        w = SEV_WEIGHTS.get(f.get('severity', 'INFO'), 1)
        if st == 'PASS':
            w_pass += w
            w_total += w
        elif st == 'FAIL':
            w_total += w
        elif st == 'WARNING':
            w_total += w * 0.5  # WARNING counts half as failure
    return round(w_pass / w_total * 100, 1) if w_total else 0


def _score_frameworks(findings):
    scores = {}
    for fw_key, fw_meta in FRAMEWORKS.items():
        if fw_key == 'WAFR':
            pillar_data = {p: {'pass': 0, 'fail': 0, 'total': 0}
                           for p in fw_meta['pillars']}
            for f in findings:
                wafr = f.get('frameworks', {}).get('WAFR', {})
                if not wafr:
                    continue
                pillar = wafr.get('pillar', '')
                if pillar not in pillar_data:
                    continue
                st = f.get('status')
                pillar_data[pillar]['total'] += 1
                if st == 'PASS':
                    pillar_data[pillar]['pass'] += 1
                elif st in ('FAIL', 'WARNING'):
                    pillar_data[pillar]['fail'] += 1

            for p, d in pillar_data.items():
                d['score'] = round(d['pass'] / d['total'] * 100, 1) if d['total'] else 0

            total_p = sum(d['pass']  for d in pillar_data.values())
            total_t = sum(d['total'] for d in pillar_data.values())
            scores['WAFR'] = {
                'label':  fw_meta['label'],
                'score':  round(total_p / total_t * 100, 1) if total_t else 0,
                'pass':   total_p,
                'total':  total_t,
                'pillars':pillar_data,
            }
        else:
            p_count = t_count = 0
            for f in findings:
                if fw_key in f.get('frameworks', {}):
                    t_count += 1
                    if f.get('status') == 'PASS':
                        p_count += 1
            scores[fw_key] = {
                'label': fw_meta['label'],
                'score': round(p_count / t_count * 100, 1) if t_count else 0,
                'pass':  p_count,
                'total': t_count,
            }
    return scores


def _score_services(findings):
    """Build service scores dynamically from findings (not from a fixed list).
    Score = PASS / (PASS + FAIL + WARNING) — excludes MANUAL/NOT_AVAILABLE from denominator.
    """
    service_data = {}
    for f in findings:
        svc = f.get('service', '')
        if not svc:
            continue
        if svc not in service_data:
            service_data[svc] = {
                'pass': 0, 'fail': 0, 'warning': 0,
                'not_available': 0, 'manual': 0, 'total': 0, 'score': 0,
            }
        service_data[svc]['total'] += 1
        st = f.get('status')
        if st == 'PASS':
            service_data[svc]['pass'] += 1
        elif st == 'FAIL':
            service_data[svc]['fail'] += 1
        elif st == 'WARNING':
            service_data[svc]['warning'] += 1
        elif st == 'NOT_AVAILABLE':
            service_data[svc]['not_available'] += 1
        elif st == 'MANUAL':
            service_data[svc]['manual'] += 1

    for svc, d in service_data.items():
        # Only score against actionable checks (exclude MANUAL + NOT_AVAILABLE)
        actionable = d['pass'] + d['fail'] + d['warning']
        d['score'] = round(d['pass'] / actionable * 100, 1) if actionable else 0

    # Return sorted: known services first (in order), then dynamic ones alphabetically
    ordered = {}
    for svc in SERVICES_ORDER:
        if svc in service_data:
            ordered[svc] = service_data[svc]
    for svc in sorted(service_data):
        if svc not in ordered:
            ordered[svc] = service_data[svc]
    return ordered


def _count_inventory(findings):
    types = {}
    for f in findings:
        rt = f.get('resource_type', '')
        if rt and rt not in types:
            types[rt] = 0
        if rt:
            types[rt] += 1
    return types
