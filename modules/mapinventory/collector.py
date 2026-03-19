"""
Map Inventory — Collector Orchestrator
Runs all service collectors in parallel threads, aggregates results.
"""

import concurrent.futures
import threading
import time
import importlib
from datetime import datetime, timezone

# Per-task timeout in seconds (boto3 calls that hang longer than this are skipped)
TASK_TIMEOUT = 30
# Global scan timeout — max total duration for all tasks
GLOBAL_SCAN_TIMEOUT = 600  # 10 minutes

# Global services (called once, not per-region)
GLOBAL_SERVICES = [
    'iam', 'organizations', 'route53', 'route53domains', 'cloudfront',
    'shield', 'budgets', 'ce', 'health', 's3',
    'networkmanager', 'globalaccelerator',
]

# Service -> module name mapping (for Python reserved words / special names)
SERVICE_MODULE_MAP = {
    'lambda': 'lambda_',
    'ecr-public': 'ecr_public',
    'network-firewall': 'network_firewall',
    'vpc-lattice': 'vpc_lattice',
    'acm-pca': 'acm_pca',
    'application-autoscaling': 'applicationautoscaling',
    'redshift-serverless': 'redshiftserverless',
    'opensearch-serverless': 'opensearchserverless',
    'emr-serverless': 'emrserverless',
    'timestream-influxdb': 'timestream_influxdb',
    'resource-groups': 'resourcegroups',
    'resource-explorer': 'resourceexplorer',
    'eventbridge-scheduler': 'scheduler',
    'eventbridge-pipes': 'pipes',
    'service-quotas': 'servicequotas',
    'compute-optimizer': 'computeoptimizer',
}

# Complete list of all services to scan (150+)
ALL_SERVICES = [
    'iam', 's3', 'ec2', 'vpc', 'rds', 'lambda', 'ecs', 'eks', 'dynamodb',
    'sqs', 'sns', 'elb', 'elbv2', 'cloudfront', 'route53', 'kms', 'efs',
    'ecr', 'cloudwatch', 'wafv2', 'acm', 'cloudtrail', 'guardduty',
    'config', 'secretsmanager', 'autoscaling', 'elasticache', 'redshift',
    'emr', 'glue', 'athena', 'kinesis', 'firehose', 'stepfunctions',
    'codebuild', 'codepipeline', 'ssm', 'backup', 'organizations',
    'lightsail', 'apigateway', 'apigatewayv2', 'cognito', 'sesv2',
    'events', 'mq', 'neptune', 'docdb', 'opensearch', 'transfer',
    'apprunner', 'batch', 'cloudformation', 'logs', 'ecr-public',
    'route53domains', 'route53resolver', 'sagemaker', 'bedrock',
    'fsx', 'storagegateway', 'dlm', 'dms', 'ds',
    'directconnect', 'network-firewall', 'networkmanager',
    'globalaccelerator', 'vpc-lattice',
    'acm-pca', 'shield', 'securityhub', 'securitylake', 'macie2',
    'inspector2', 'detective', 'fms', 'accessanalyzer',
    'application-autoscaling', 'elasticbeanstalk', 'imagebuilder',
    'appconfig', 'appsync', 'amp', 'amplify', 'appflow',
    'kafka', 'memorydb', 'dax', 'keyspaces',
    'lakeformation', 'datazone', 'cleanrooms',
    'quicksight', 'grafana',
    'codedeploy', 'codeartifact',
    'eventbridge-scheduler', 'eventbridge-pipes', 'schemas',
    'mediatailor', 'mediaconvert', 'medialive', 'mediaconnect',
    'mediapackage', 'mediastore',
    'iot', 'iotsitewise', 'connect',
    'comprehend', 'textract', 'transcribe', 'translate',
    'polly', 'rekognition', 'personalize', 'frauddetector',
    'lexv2', 'kendra',
    'sso', 'servicediscovery', 'servicecatalog', 'serverlessrepo',
    'service-quotas', 'resource-groups', 'resource-explorer',
    'ram', 'compute-optimizer', 'auditmanager', 'resiliencehub',
    'synthetics', 'fis', 'xray', 'datasync',
    'mwaa', 'workspaces', 'ivs', 'gamelift', 'outposts',
    'location', 'devicefarm',
    'health', 'budgets', 'ce',
    'cloudhsmv2', 'redshift-serverless', 'opensearch-serverless',
    'emr-serverless', 'timestream-influxdb', 'dsql',
]

# Remove duplicates while preserving order
_seen = set()
SERVICES_ORDER = []
for s in ALL_SERVICES:
    if s not in _seen:
        _seen.add(s)
        SERVICES_ORDER = SERVICES_ORDER + [s]


def get_collector_function(service_name):
    """Dynamically import and return the collector function for a service."""
    module_name = SERVICE_MODULE_MAP.get(service_name, service_name.replace('-', ''))
    try:
        mod = importlib.import_module(f'.collectors.{module_name}', package='modules.mapinventory')
        func_name = f'collect_{module_name}_resources'
        return getattr(mod, func_name, None)
    except (ImportError, AttributeError):
        return None


def get_enabled_regions(session):
    """Get list of enabled regions for the account."""
    try:
        ec2 = session.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions(
            Filters=[{'Name': 'opt-in-status', 'Values': ['opt-in-not-required', 'opted-in']}]
        )['Regions']
        return sorted([r['RegionName'] for r in regions])
    except Exception:
        # Fallback common regions
        return ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                'eu-west-1', 'eu-west-2', 'eu-central-1',
                'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1']


def _get_active_services_from_ce(session):
    """Query Cost Explorer to find services with non-zero spend in last 30 days.
    Returns a set of lowercase service name keywords, or None if CE unavailable."""
    try:
        from datetime import date, timedelta
        ce = session.client('ce', region_name='us-east-1')
        end = date.today()
        start = end - timedelta(days=30)
        resp = ce.get_cost_and_usage(
            TimePeriod={'Start': str(start), 'End': str(end)},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Metrics=['UnblendedCost'],
        )
        active = set()
        for result in resp.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount > 0:
                    active.add(group['Keys'][0].lower())
        return active
    except Exception:
        return None  # CE unavailable, scan everything


# Map our collector service names to CE service name keywords for smart filtering
_COLLECTOR_TO_CE_KEYWORDS = {
    'rds': ['relational database', 'aurora'],
    'lambda': ['lambda'],
    'ecs': ['elastic container service', 'fargate'],
    'eks': ['elastic kubernetes'],
    'dynamodb': ['dynamodb'],
    'sqs': ['simple queue'],
    'sns': ['simple notification'],
    'elb': ['elastic load'],
    'elbv2': ['elastic load'],
    'cloudfront': ['cloudfront'],
    'elasticache': ['elasticache'],
    'redshift': ['redshift'],
    'emr': ['elastic mapreduce', 'emr'],
    'glue': ['glue'],
    'kinesis': ['kinesis'],
    'sagemaker': ['sagemaker'],
    'opensearch': ['opensearch', 'elasticsearch'],
    'neptune': ['neptune'],
    'docdb': ['documentdb'],
    'kafka': ['managed streaming', 'msk'],
    'memorydb': ['memorydb'],
    'fsx': ['fsx'],
    'workspaces': ['workspaces'],
    'lightsail': ['lightsail'],
    'apprunner': ['app runner'],
    'batch': ['batch'],
    'mq': ['amazon mq'],
    'transfer': ['transfer'],
    'bedrock': ['bedrock'],
    'mediaconvert': ['mediaconvert'],
    'medialive': ['medialive'],
}

# Core services always scanned regardless of CE data
_ALWAYS_SCAN_SERVICES = {
    'iam', 's3', 'ec2', 'vpc', 'kms', 'cloudtrail', 'guardduty', 'config',
    'cloudwatch', 'organizations', 'route53', 'acm', 'secretsmanager',
    'ssm', 'backup', 'health', 'budgets', 'ce', 'logs',
    'securityhub', 'accessanalyzer', 'route53domains', 'shield',
}


def collect_all(session, account_id, services=None, regions=None,
                max_workers=40, progress_callback=None, exclude_defaults=True,
                smart_scan=True):
    """
    Run all service collectors in parallel.
    If smart_scan=True (default), queries CE to skip unused services.

    Returns:
        dict with 'metadata', 'resources', and 'scan_errors' keys
    """
    if regions is None:
        regions = get_enabled_regions(session)

    target_services = services or SERVICES_ORDER

    # Smart scan: filter to only services active in Cost Explorer
    skipped_by_ce = []
    if smart_scan and services is None:
        active_ce = _get_active_services_from_ce(session)
        if active_ce is not None:
            filtered = []
            for svc in target_services:
                if svc in _ALWAYS_SCAN_SERVICES or svc in GLOBAL_SERVICES:
                    filtered.append(svc)
                elif svc in _COLLECTOR_TO_CE_KEYWORDS:
                    keywords = _COLLECTOR_TO_CE_KEYWORDS[svc]
                    if any(kw in ce_name for kw in keywords for ce_name in active_ce):
                        filtered.append(svc)
                    else:
                        skipped_by_ce.append(svc)
                else:
                    # No CE mapping — include by default
                    filtered.append(svc)
            target_services = filtered
    # Filter to only services that have a collector
    valid_services = [s for s in target_services if get_collector_function(s) is not None]
    # Services without a collector
    no_collector = [s for s in target_services if get_collector_function(s) is None]

    import queue as _queue

    _result_queue = _queue.Queue()  # thread-safe, no lock needed for put/get
    _completed = [0]
    _completed_lock = threading.Lock()
    start_time = time.time()

    # Error tracking per service
    _service_errors = {}
    _service_success = set()

    # Build task list
    tasks = []
    for svc in valid_services:
        if svc in GLOBAL_SERVICES:
            tasks.append((svc, None))
        else:
            for region in regions:
                tasks.append((svc, region))

    total_tasks = len(tasks)

    def run_one(svc, region):
        func = get_collector_function(svc)
        if func is None:
            return [], None
        try:
            resources = func(session, region, account_id)
            return resources or [], None
        except Exception as exc:
            error_type = type(exc).__name__
            error_msg = str(exc)[:200]
            return [], {'region': region or 'global', 'error': error_msg, 'type': error_type}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for svc, region in tasks:
            future = executor.submit(run_one, svc, region)
            future_map[future] = (svc, region)

        # Global timeout: don't let entire scan exceed GLOBAL_SCAN_TIMEOUT
        try:
            for future in concurrent.futures.as_completed(future_map, timeout=GLOBAL_SCAN_TIMEOUT):
                svc, region = future_map[future]
                try:
                    # No per-future timeout — as_completed only yields done futures
                    resources, error_info = future.result()
                    # Queue results lock-free (thread-safe queue)
                    if resources:
                        _result_queue.put(('resources', svc, resources))
                    if error_info:
                        _result_queue.put(('error', svc, error_info))
                except Exception:
                    _result_queue.put(('error', svc, {
                        'region': region or 'global',
                        'error': 'Task execution error',
                        'type': 'Unknown',
                    }))
                # Update progress (lightweight lock, only counter)
                with _completed_lock:
                    _completed[0] += 1
                    count = _completed[0]
                if progress_callback:
                    progress_callback(svc, f'Completed {region or "global"}', count, total_tasks)
        except concurrent.futures.TimeoutError:
            # Global timeout reached — mark remaining tasks as timed out
            with _completed_lock:
                done_count = _completed[0]
            remaining = total_tasks - done_count
            if remaining > 0 and progress_callback:
                progress_callback('timeout', f'{remaining} tasks timed out', done_count, total_tasks)
            for future, (svc, region) in future_map.items():
                if not future.done():
                    future.cancel()
                    _result_queue.put(('error', svc, {
                        'region': region or 'global',
                        'error': f'Global scan timeout ({GLOBAL_SCAN_TIMEOUT}s)',
                        'type': 'TimeoutError',
                    }))

    # Drain queue into lists (single-threaded, no lock needed)
    all_resources = []
    while not _result_queue.empty():
        item_type, svc, data = _result_queue.get_nowait()
        if item_type == 'resources':
            all_resources.extend(data)
            _service_success.add(svc)
        elif item_type == 'error':
            _service_errors.setdefault(svc, []).append(data)

    # Filter defaults if requested
    if exclude_defaults:
        all_resources = [r for r in all_resources if not r.get('is_default', False)]

    # Build metadata — single pass over all_resources
    duration = round(time.time() - start_time, 2)
    services_found = set()
    service_counts = {}
    region_counts = {}
    type_counts = {}
    for r in all_resources:
        svc = r.get('service', 'unknown')
        reg = r.get('region', 'unknown')
        rtype = f"{svc}/{r.get('type', 'unknown')}"
        services_found.add(svc)
        service_counts[svc] = service_counts.get(svc, 0) + 1
        region_counts[reg] = region_counts.get(reg, 0) + 1
        type_counts[rtype] = type_counts.get(rtype, 0) + 1

    # Build scan_errors summary
    # failed_services = services that had errors in ALL regions (no resources found)
    failed_services = []
    partial_services = []
    for svc, errors in _service_errors.items():
        if svc in _service_success:
            # Had errors in some regions but got resources from others
            partial_services.append({
                'service': svc,
                'errors': errors,
                'status': 'partial',
            })
        else:
            # Failed in all attempted regions, no resources
            failed_services.append({
                'service': svc,
                'errors': errors,
                'status': 'failed',
            })

    # Services with no collector
    skipped_services = [{'service': s, 'status': 'no_collector'} for s in no_collector]

    # Services with zero resources and zero errors (access OK but nothing found)
    empty_services = [
        s for s in valid_services
        if s not in _service_success and s not in _service_errors
    ]

    scan_stats = {
        'total_services': len(target_services),
        'scanned_services': len(valid_services),
        'services_with_resources': len(services_found),
        'failed_services_count': len(failed_services),
        'partial_services_count': len(partial_services),
        'skipped_services_count': len(skipped_services),
        'empty_services_count': len(empty_services),
        'failed_services': failed_services,
        'partial_services': partial_services,
        'skipped_services': skipped_services,
        'empty_services': empty_services,
        'total_tasks': total_tasks,
        'total_errors': sum(len(e) for e in _service_errors.values()),
    }

    metadata = {
        'account_id': account_id,
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'scan_duration_seconds': duration,
        'services_scanned': len(valid_services),
        'services_scanned_list': valid_services,
        'services_with_resources': len(services_found),
        'regions_scanned': len(regions),
        'regions_scanned_list': regions,
        'resource_count': len(all_resources),
        'exclude_defaults': exclude_defaults,
        'service_counts': service_counts,
        'region_counts': region_counts,
        'type_counts': type_counts,
        'skipped_by_ce': skipped_by_ce,
    }

    return {
        'metadata': metadata,
        'resources': all_resources,
        'scan_stats': scan_stats,
    }
