"""
Advice Module — Assessment Engine
Reads cached data from SecOps, MapInventory, and FinOps modules.
Produces a consolidated WAFR-based assessment report per AWS profile.
"""

import time
import threading
import boto3
from datetime import date, timedelta
from botocore.exceptions import ProfileNotFound, NoCredentialsError

from modules.secops import cache as secops_cache
from modules.mapinventory import cache as mapinv_cache
from . import cache as advice_cache
from .wafr_knowledge import (
    PILLARS, WAFR_CONTROLS, SERVICE_ADVICE_RULES,
    COST_ADVICE_TEMPLATES, RESOURCE_ADVICE_TEMPLATES, map_risk,
)

# Module-level progress tracker
_assess_progress = {}

CE_REGION = 'us-east-1'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_prerequisites(profile: str) -> dict:
    """Check if required module scans exist for the given profile."""
    secops_data, secops_age = secops_cache.load_scan(profile)
    mapinv_data, mapinv_age = mapinv_cache.load_scan(profile)

    missing = []
    available = {}

    if not secops_data:
        missing.append('SecOps')
    else:
        available['secops'] = {
            'age_seconds': secops_age,
            'scan_time': secops_data.get('scan_time', ''),
            'score': secops_data.get('summary', {}).get('score', 0),
        }

    if not mapinv_data:
        missing.append('MapInventory')
    else:
        meta = mapinv_data.get('metadata', {})
        available['mapinventory'] = {
            'age_seconds': mapinv_age,
            'scan_time': meta.get('timestamp', ''),
            'resource_count': meta.get('resource_count', 0),
        }

    # FinOps is optional (CE may not be accessible)
    available['finops'] = {'status': 'live_fetch'}

    return {
        'ready': len(missing) == 0,
        'missing': missing,
        'available': available,
    }


def run_assessment(profile: str, regions: list = None) -> dict:
    """
    Run a consolidated WAFR assessment for the given profile.
    Reads SecOps + MapInventory caches and fetches FinOps data live.
    """
    started = time.time()
    total_steps = 6
    _assess_progress[profile] = {'step': 'authenticating', 'completed': 0, 'total': total_steps}

    # 1. Authenticate
    try:
        session = boto3.Session(profile_name=profile)
        sts = session.client('sts', region_name=CE_REGION)
        identity = sts.get_caller_identity()
        account_id = identity.get('Account', 'unknown')
    except (ProfileNotFound, NoCredentialsError) as exc:
        _assess_progress.pop(profile, None)
        return {'status': 'error', 'error': str(exc)}
    except Exception as exc:
        _assess_progress.pop(profile, None)
        return {'status': 'error', 'error': str(exc)}

    _update_progress(profile, 'loading_secops', 1, total_steps)

    # 2. Load SecOps data
    secops_data, _ = secops_cache.load_scan(profile)
    if not secops_data:
        _assess_progress.pop(profile, None)
        return {'status': 'error', 'error': 'SecOps scan data not found. Run SecOps scan first.'}

    _update_progress(profile, 'loading_mapinventory', 2, total_steps)

    # 3. Load MapInventory data
    mapinv_data, _ = mapinv_cache.load_scan(profile)
    if not mapinv_data:
        _assess_progress.pop(profile, None)
        return {'status': 'error', 'error': 'MapInventory scan data not found. Run MapInventory scan first.'}

    _update_progress(profile, 'loading_finops', 3, total_steps)

    # 4. Fetch FinOps data (live, optional)
    finops_data = _fetch_finops_data(session)

    _update_progress(profile, 'analyzing', 4, total_steps)

    # 5. Run WAFR analysis
    service_assessments = _analyze_all(secops_data, mapinv_data, finops_data, regions)

    _update_progress(profile, 'summarizing', 5, total_steps)

    # 6. Compute summary
    summary = _compute_summary(service_assessments)
    pillar_scores = _compute_pillar_scores(service_assessments)

    elapsed = round(time.time() - started, 1)

    results = {
        'status': 'ok',
        'profile': profile,
        'account_id': account_id,
        'assessment_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'elapsed_seconds': elapsed,
        'regions': regions or [],
        'data_sources': {
            'secops': {
                'scan_time': secops_data.get('scan_time', ''),
                'total_findings': secops_data.get('summary', {}).get('total', 0),
                'score': secops_data.get('summary', {}).get('score', 0),
            },
            'mapinventory': {
                'scan_time': mapinv_data.get('metadata', {}).get('timestamp', ''),
                'resource_count': mapinv_data.get('metadata', {}).get('resource_count', 0),
            },
            'finops': {
                'available': finops_data is not None,
                'total_cost': finops_data.get('total_cost', 0) if finops_data else 0,
            },
        },
        'summary': summary,
        'pillar_scores': pillar_scores,
        'services': service_assessments,
    }

    # Cache result
    advice_cache.save_assessment(profile, results)
    _update_progress(profile, 'done', total_steps, total_steps)
    _assess_progress.pop(profile, None)

    return results


def get_progress(profile: str) -> dict | None:
    return _assess_progress.get(profile)


def init_progress(profile: str):
    _assess_progress[profile] = {'step': 'starting', 'completed': 0, 'total': 0}


def clear_progress(profile: str):
    _assess_progress.pop(profile, None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _update_progress(profile, step, completed, total):
    _assess_progress[profile] = {
        'step': step,
        'completed': completed,
        'total': total,
    }


def _fetch_finops_data(session):
    """Fetch cost summary from Cost Explorer (last 30 days)."""
    try:
        ce = session.client('ce', region_name=CE_REGION)
        end = date.today()
        start = end - timedelta(days=30)

        # Service-level costs
        resp = ce.get_cost_and_usage(
            TimePeriod={'Start': str(start), 'End': str(end)},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Metrics=['UnblendedCost'],
        )

        services = {}
        total_cost = 0.0
        for result in resp.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                svc_name = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount > 0:
                    services[svc_name] = services.get(svc_name, 0) + amount
                    total_cost += amount

        # Check budgets
        budgets_exist = False
        try:
            sts = session.client('sts', region_name=CE_REGION)
            account_id = sts.get_caller_identity()['Account']
            budgets_client = session.client('budgets', region_name=CE_REGION)
            budgets_resp = budgets_client.describe_budgets(AccountId=account_id)
            budgets_exist = len(budgets_resp.get('Budgets', [])) > 0
        except Exception:
            pass

        # Check for savings plans / reserved instances
        has_savings_plans = False
        try:
            sp_resp = ce.get_cost_and_usage(
                TimePeriod={'Start': str(start), 'End': str(end)},
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'RECORD_TYPE',
                        'Values': ['SavingsPlanCoveredUsage', 'SavingsPlanNegation'],
                    }
                },
                Metrics=['UnblendedCost'],
            )
            for r in sp_resp.get('ResultsByTime', []):
                for g in r.get('Groups', []):
                    if float(g['Metrics']['UnblendedCost']['Amount']) != 0:
                        has_savings_plans = True
                        break
        except Exception:
            pass

        # Top services by cost
        sorted_services = sorted(services.items(), key=lambda x: x[1], reverse=True)

        return {
            'total_cost': round(total_cost, 2),
            'services': dict(sorted_services),
            'budgets_exist': budgets_exist,
            'has_savings_plans': has_savings_plans,
            'top_services': sorted_services[:10],
            'region_distribution': _get_region_costs(ce, start, end),
        }
    except Exception:
        return None


def _get_region_costs(ce, start, end):
    """Get cost breakdown by region."""
    try:
        resp = ce.get_cost_and_usage(
            TimePeriod={'Start': str(start), 'End': str(end)},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'REGION'}],
            Metrics=['UnblendedCost'],
        )
        regions = {}
        for result in resp.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                region = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount > 0 and region:
                    regions[region] = regions.get(region, 0) + amount
        return regions
    except Exception:
        return {}


def _analyze_all(secops_data, mapinv_data, finops_data, regions):
    """Analyze all services and produce advice items."""
    service_assessments = []

    # Extract findings by service from SecOps
    secops_findings_by_svc = {}
    for f in secops_data.get('findings', []):
        svc = f.get('service', '')
        if svc:
            secops_findings_by_svc.setdefault(svc, []).append(f)

    # Extract resources by service from MapInventory
    mapinv_resources_by_svc = {}
    for r in mapinv_data.get('resources', []):
        svc = (r.get('service', '') or '').upper()
        # Normalize common names
        svc_map = {
            'EC2': 'EC2', 'S3': 'S3', 'VPC': 'VPC', 'RDS': 'RDS',
            'IAM': 'IAM', 'LAMBDA': 'Lambda', 'EKS': 'EKS', 'ECS': 'ECS',
            'ELB': 'ELB', 'CLOUDFRONT': 'CloudFront', 'ROUTE53': 'Route53',
            'DYNAMODB': 'DynamoDB', 'SQS': 'SQS', 'SNS': 'SNS',
            'CLOUDWATCH': 'CloudWatch', 'ECR': 'ECR', 'EFS': 'EFS',
            'KMS': 'KMS', 'SECRETSMANAGER': 'SecretsManager',
            'CLOUDTRAIL': 'CloudTrail', 'GUARDDUTY': 'GuardDuty',
            'CONFIG': 'Config', 'WAF': 'WAF', 'ACM': 'ACM',
        }
        normalized = svc_map.get(svc, svc)
        mapinv_resources_by_svc.setdefault(normalized, []).append(r)

    # Get all unique services from both sources
    all_services = set(secops_findings_by_svc.keys()) | set(mapinv_resources_by_svc.keys())

    for svc in sorted(all_services):
        findings_list = secops_findings_by_svc.get(svc, [])
        resources_list = mapinv_resources_by_svc.get(svc, [])
        rules = SERVICE_ADVICE_RULES.get(svc, None)

        assessment = _analyze_service(
            svc, findings_list, resources_list, rules, finops_data
        )
        if assessment and (assessment['findings'] or assessment['recommendations'] or assessment['positive']):
            service_assessments.append(assessment)

    # Add cost-specific advice if FinOps data available
    cost_assessment = _analyze_costs(finops_data)
    if cost_assessment:
        service_assessments.append(cost_assessment)

    # Add resource-level advice from MapInventory
    resource_assessment = _analyze_resources(mapinv_data)
    if resource_assessment and (resource_assessment['findings'] or resource_assessment['recommendations']):
        service_assessments.append(resource_assessment)

    return service_assessments


def _analyze_service(svc, findings, resources, rules, finops_data):
    """Analyze a single service and produce advice."""
    assessment = {
        'service': svc,
        'category_en': rules['category_en'] if rules else svc,
        'category_tr': rules['category_tr'] if rules else svc,
        'resource_count': len(resources),
        'findings': [],
        'recommendations': [],
        'positive': [],
    }

    # Track which findings have been processed to avoid duplicates
    processed_ids = set()

    # Analyze SecOps findings
    for f in findings:
        f_id = f.get('id', '')
        if f_id in processed_ids:
            continue

        status = f.get('status', '')
        severity = f.get('severity', 'INFO')

        # PASS findings → positive
        if status == 'PASS':
            wafr_codes = _extract_wafr_from_frameworks(f)
            if not wafr_codes:
                wafr_codes = _infer_wafr_from_service(svc, f)
            assessment['positive'].append({
                'text_en': f.get('title', ''),
                'text_tr': f.get('title_tr', '') or f.get('title', ''),
                'resource_id': f.get('resource_id', ''),
                'region': f.get('region', ''),
                'wafr_codes': wafr_codes,
            })
            processed_ids.add(f_id)
            continue

        # FAIL/WARNING findings → analyze against rules
        if status in ('FAIL', 'WARNING'):
            advice = _match_finding_to_rule(f, svc, rules)
            if advice:
                # Check if similar advice already exists
                advice_key = tuple(advice.get('wafr_codes', []))
                existing = [a for a in assessment['findings']
                            if tuple(a.get('wafr_codes', [])) == advice_key
                            and a.get('text_en') == advice.get('text_en')]
                if not existing:
                    assessment['findings'].append(advice)
                    # Add corresponding recommendation
                    if advice.get('recommendation_en'):
                        rec_existing = [r for r in assessment['recommendations']
                                        if r.get('text_en') == advice['recommendation_en']]
                        if not rec_existing:
                            assessment['recommendations'].append({
                                'text_en': advice['recommendation_en'],
                                'text_tr': advice['recommendation_tr'],
                                'wafr_codes': advice['wafr_codes'],
                            })
            processed_ids.add(f_id)

    return assessment


def _match_finding_to_rule(finding, svc, rules):
    """Match a SecOps finding to a WAFR advice rule."""
    if not rules:
        # No specific rules for this service, use generic advice
        severity = finding.get('severity', 'INFO')
        return {
            'text_en': finding.get('title', ''),
            'text_tr': finding.get('title_tr', '') or finding.get('title', ''),
            'risk': map_risk(severity),
            'wafr_codes': _extract_wafr_from_frameworks(finding),
            'resource_id': finding.get('resource_id', ''),
            'region': finding.get('region', ''),
            'recommendation_en': finding.get('remediation', ''),
            'recommendation_tr': finding.get('remediation_tr', '') or finding.get('remediation', ''),
        }

    # Try matching rules in order (first match wins except fallback)
    for rule in rules.get('rules', []):
        try:
            if rule['match'](finding):
                finding_en = rule.get('finding_en') or finding.get('title', '')
                finding_tr = rule.get('finding_tr') or finding.get('title_tr', '') or finding.get('title', '')
                severity = finding.get('severity', 'INFO')
                risk = rule.get('risk', map_risk(severity))

                return {
                    'text_en': finding_en,
                    'text_tr': finding_tr,
                    'risk': risk,
                    'wafr_codes': rule.get('wafr', []),
                    'resource_id': finding.get('resource_id', ''),
                    'region': finding.get('region', ''),
                    'recommendation_en': rule.get('recommendation_en', ''),
                    'recommendation_tr': rule.get('recommendation_tr', ''),
                }
        except Exception:
            continue

    return None


def _extract_wafr_from_frameworks(finding):
    """Extract WAFR codes from SecOps finding frameworks field."""
    wafr = finding.get('frameworks', {}).get('WAFR', {})
    if not wafr:
        return []
    controls = wafr.get('controls', [])
    return controls if controls else []


# Service → primary WAFR pillar codes (fallback when findings have no explicit WAFR)
_SERVICE_PILLAR_MAP = {
    'IAM':             ['SEC01', 'SEC02'],
    'S3':              ['SEC07', 'REL09'],
    'EC2':             ['PERF01', 'REL05', 'COST06'],
    'VPC':             ['SEC05', 'REL02'],
    'CloudTrail':      ['SEC04', 'OPS03'],
    'GuardDuty':       ['SEC04'],
    'RDS':             ['REL09', 'PERF02'],
    'KMS':             ['SEC08'],
    'Lambda':          ['PERF03', 'COST06', 'SUS02'],
    'Config':          ['OPS07', 'SEC04'],
    'SecretsManager':  ['SEC02'],
    'DynamoDB':        ['REL09', 'PERF02'],
    'SQS':             ['REL05'],
    'SNS':             ['OPS08'],
    'ECS':             ['PERF03', 'OPS05'],
    'EKS':             ['PERF03', 'OPS05', 'REL05'],
    'ELB':             ['REL05', 'PERF01'],
    'CloudFront':      ['PERF04', 'SEC09'],
    'CloudWatch':      ['OPS08', 'REL06'],
    'WAF':             ['SEC06'],
    'Route53':         ['REL01'],
    'ACM':             ['SEC09'],
    'ECR':             ['SEC07'],
    'EFS':             ['REL09'],
}


def _infer_wafr_from_service(svc, finding=None):
    """Infer WAFR codes from service name when the finding lacks explicit codes."""
    return _SERVICE_PILLAR_MAP.get(svc, ['SEC01'])


def _analyze_costs(finops_data):
    """Produce cost optimization advice from FinOps data."""
    if not finops_data:
        return None

    assessment = {
        'service': 'CostOptimization',
        'category_en': 'Cost Optimization',
        'category_tr': 'Maliyet Optimizasyonu',
        'resource_count': 0,
        'findings': [],
        'recommendations': [],
        'positive': [],
    }

    # Check budgets
    if not finops_data.get('budgets_exist'):
        tpl = COST_ADVICE_TEMPLATES['no_budget']
        assessment['findings'].append({
            'text_en': tpl['finding_en'],
            'text_tr': tpl['finding_tr'],
            'risk': tpl['risk'],
            'wafr_codes': tpl['wafr'],
            'resource_id': '',
            'region': 'global',
        })
        assessment['recommendations'].append({
            'text_en': tpl['recommendation_en'],
            'text_tr': tpl['recommendation_tr'],
            'wafr_codes': tpl['wafr'],
        })
    else:
        assessment['positive'].append({
            'text_en': 'AWS Budgets are configured for cost monitoring.',
            'text_tr': 'Maliyet izleme icin AWS Budgets yapilandirilmistir.',
            'resource_id': '', 'region': 'global',
            'wafr_codes': ['COST02'],
        })

    # Check savings plans
    if not finops_data.get('has_savings_plans'):
        tpl = COST_ADVICE_TEMPLATES['no_savings_plan']
        assessment['findings'].append({
            'text_en': tpl['finding_en'],
            'text_tr': tpl['finding_tr'],
            'risk': tpl['risk'],
            'wafr_codes': tpl['wafr'],
            'resource_id': '',
            'region': 'global',
        })
        assessment['recommendations'].append({
            'text_en': tpl['recommendation_en'],
            'text_tr': tpl['recommendation_tr'],
            'wafr_codes': tpl['wafr'],
        })

    # Check multi-region usage
    region_dist = finops_data.get('region_distribution', {})
    if len(region_dist) > 2:
        tpl = COST_ADVICE_TEMPLATES['multi_region_cost']
        regions_str = ', '.join(sorted(region_dist.keys()))
        assessment['findings'].append({
            'text_en': f'{tpl["finding_en"]} Active regions: {regions_str}.',
            'text_tr': f'{tpl["finding_tr"]} Aktif bolgeler: {regions_str}.',
            'risk': tpl['risk'],
            'wafr_codes': tpl['wafr'],
            'resource_id': '',
            'region': 'global',
        })
        assessment['recommendations'].append({
            'text_en': tpl['recommendation_en'],
            'text_tr': tpl['recommendation_tr'],
            'wafr_codes': tpl['wafr'],
        })

    # Top cost service info
    total = finops_data.get('total_cost', 0)
    if total > 0:
        top = finops_data.get('top_services', [])[:5]
        top_str_en = ', '.join([f'{s[0]}: ${s[1]:.2f}' for s in top])
        top_str_tr = ', '.join([f'{s[0]}: ${s[1]:.2f}' for s in top])
        assessment['findings'].append({
            'text_en': f'Monthly cloud spend: ${total:.2f}. Top services: {top_str_en}.',
            'text_tr': f'Aylik bulut harcamasi: ${total:.2f}. En yuksek servisler: {top_str_tr}.',
            'risk': 'LOW',
            'wafr_codes': ['COST03'],
            'resource_id': '',
            'region': 'global',
        })

    return assessment


def _analyze_resources(mapinv_data):
    """Produce resource-level advice from MapInventory data."""
    assessment = {
        'service': 'ResourceManagement',
        'category_en': 'Resource Management & Hygiene',
        'category_tr': 'Kaynak Yonetimi ve Hijyeni',
        'resource_count': 0,
        'findings': [],
        'recommendations': [],
        'positive': [],
    }

    resources = mapinv_data.get('resources', [])
    if not resources:
        return assessment

    assessment['resource_count'] = len(resources)

    # Check for stopped instances
    stopped = [r for r in resources
               if r.get('service', '').lower() == 'ec2'
               and r.get('type', '').lower() == 'instance'
               and r.get('details', {}).get('State', {}).get('Name', '') == 'stopped']
    if stopped:
        tpl = RESOURCE_ADVICE_TEMPLATES['stopped_instances']
        count = len(stopped)
        assessment['findings'].append({
            'text_en': f'{count} stopped EC2 instance(s) detected. {tpl["finding_en"]}',
            'text_tr': f'{count} durdurulmus EC2 instance tespit edildi. {tpl["finding_tr"]}',
            'risk': tpl['risk'],
            'wafr_codes': tpl['wafr'],
            'resource_id': ', '.join([s.get('id', '') for s in stopped[:5]]),
            'region': '',
        })
        assessment['recommendations'].append({
            'text_en': tpl['recommendation_en'],
            'text_tr': tpl['recommendation_tr'],
            'wafr_codes': tpl['wafr'],
        })

    # Check for untagged resources
    untagged = [r for r in resources
                if not r.get('tags') and not r.get('is_default', False)]
    if untagged and len(untagged) > len(resources) * 0.3:
        tpl = RESOURCE_ADVICE_TEMPLATES['untagged_resources']
        pct = round(len(untagged) / len(resources) * 100)
        assessment['findings'].append({
            'text_en': f'{pct}% of resources ({len(untagged)}/{len(resources)}) lack proper tagging. {tpl["finding_en"]}',
            'text_tr': f'Kaynaklarin %{pct}\'i ({len(untagged)}/{len(resources)}) uygun etiketlemeden yoksun. {tpl["finding_tr"]}',
            'risk': tpl['risk'],
            'wafr_codes': tpl['wafr'],
            'resource_id': '',
            'region': '',
        })
        assessment['recommendations'].append({
            'text_en': tpl['recommendation_en'],
            'text_tr': tpl['recommendation_tr'],
            'wafr_codes': tpl['wafr'],
        })

    # Check for default VPC resources
    default_vpc = [r for r in resources if r.get('is_default', False)
                   and r.get('service', '').lower() in ('ec2', 'rds', 'elb')]
    if default_vpc:
        tpl = RESOURCE_ADVICE_TEMPLATES['default_vpc_resources']
        assessment['findings'].append({
            'text_en': f'{len(default_vpc)} resource(s) deployed in default VPC. {tpl["finding_en"]}',
            'text_tr': f'{len(default_vpc)} kaynak varsayilan VPC\'de dagitilmis. {tpl["finding_tr"]}',
            'risk': tpl['risk'],
            'wafr_codes': tpl['wafr'],
            'resource_id': '',
            'region': '',
        })
        assessment['recommendations'].append({
            'text_en': tpl['recommendation_en'],
            'text_tr': tpl['recommendation_tr'],
            'wafr_codes': tpl['wafr'],
        })

    return assessment


def _compute_summary(service_assessments):
    """Compute overall summary statistics."""
    total_findings = 0
    total_recommendations = 0
    total_positive = 0
    risk_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    services_analyzed = len(service_assessments)

    for svc in service_assessments:
        findings = svc.get('findings', [])
        total_findings += len(findings)
        total_recommendations += len(svc.get('recommendations', []))
        total_positive += len(svc.get('positive', []))
        for f in findings:
            risk = f.get('risk', 'LOW')
            if risk in risk_counts:
                risk_counts[risk] += 1

    return {
        'services_analyzed': services_analyzed,
        'total_findings': total_findings,
        'total_recommendations': total_recommendations,
        'total_positive': total_positive,
        'risk_counts': risk_counts,
    }


def _compute_pillar_scores(service_assessments):
    """Compute scores per WAFR pillar."""
    pillar_findings = {p: {'findings': 0, 'positive': 0, 'total': 0}
                       for p in PILLARS}

    for svc in service_assessments:
        svc_name = svc.get('service', '')

        for f in svc.get('findings', []):
            codes = f.get('wafr_codes', [])
            if not codes:
                codes = _infer_wafr_from_service(svc_name)
            assigned = set()
            for code in codes:
                ctrl = WAFR_CONTROLS.get(code, {})
                pillar = ctrl.get('pillar', '')
                if pillar in pillar_findings and pillar not in assigned:
                    pillar_findings[pillar]['findings'] += 1
                    pillar_findings[pillar]['total'] += 1
                    assigned.add(pillar)

        for p in svc.get('positive', []):
            codes = p.get('wafr_codes', [])
            if not codes:
                codes = _infer_wafr_from_service(svc_name)
            assigned = set()
            for code in codes:
                ctrl = WAFR_CONTROLS.get(code, {})
                pillar = ctrl.get('pillar', '')
                if pillar in pillar_findings and pillar not in assigned:
                    pillar_findings[pillar]['positive'] += 1
                    pillar_findings[pillar]['total'] += 1
                    assigned.add(pillar)

    scores = {}
    for pillar, data in pillar_findings.items():
        total = data['total']
        positive = data['positive']
        score = round(positive / total * 100, 1) if total > 0 else 0
        scores[pillar] = {
            'name_en': PILLARS[pillar]['name_en'],
            'name_tr': PILLARS[pillar]['name_tr'],
            'score': score,
            'findings': data['findings'],
            'positive': positive,
            'total': total,
        }

    return scores
