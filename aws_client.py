"""
AWS FinOps Dashboard — AWS Client
All boto3 calls: Cost Explorer, EC2, Budgets, STS
Cost Explorer API endpoint is always us-east-1 (AWS constraint).
Cost data returned covers all regions/services.
"""

import boto3
import configparser
import os
import calendar
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import re

CE_REGION = 'us-east-1'

# Centralized profile name validation — used by all modules
_PROFILE_RE = re.compile(r'^[\w\-\.@\+/: ]{1,128}$')

def validate_profile(name):
    """Validate AWS profile name against allowed characters. Used by all modules."""
    return bool(name and _PROFILE_RE.match(name))

MAX_THREAD_WORKERS = 10

# ---------------------------------------------------------------------------
# Demo Mode — mask real profile names and account IDs for screenshots
# Set SCANBOX_DEMO=1 environment variable to activate
# ---------------------------------------------------------------------------
DEMO_MODE = os.environ.get('SCANBOX_DEMO', '') == '1'
_demo_map = {}       # real_name → masked_name
_demo_acct_map = {}  # real_account_id → masked_account_id
_demo_counter = [0]

def _demo_profile(real_name):
    """Map real profile name to client1-management, client2-management, etc."""
    if not DEMO_MODE:
        return real_name
    if real_name not in _demo_map:
        _demo_counter[0] += 1
        _demo_map[real_name] = f'client{_demo_counter[0]}-management'
    return _demo_map[real_name]

def _demo_account(real_id):
    """Map real account ID to 11111111111, 22222222222, etc."""
    if not DEMO_MODE or not real_id:
        return real_id
    if real_id not in _demo_acct_map:
        n = len(_demo_acct_map) + 1
        _demo_acct_map[real_id] = str(n) * 11
    return _demo_acct_map[real_id]

# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

# Ensure logs directory exists
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'), exist_ok=True)

# Audit logger for FinOps API access
_audit_logger = logging.getLogger('finops.audit')
_audit_handler = logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'finops_audit.log'))
_audit_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
_audit_logger.addHandler(_audit_handler)
_audit_logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Simple TTL cache for Cost Explorer API results (5 minute default)
# ---------------------------------------------------------------------------

_ce_cache = {}
_CE_CACHE_TTL = 300  # seconds


def _cache_key(fn_name, *args, **kwargs):
    """Generate a cache key from function name and arguments."""
    key_parts = [fn_name] + [str(a) for a in args]
    key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return ':'.join(key_parts)


def _cache_get(key):
    """Get cached result if not expired."""
    if key in _ce_cache:
        result, ts = _ce_cache[key]
        if time.time() - ts < _CE_CACHE_TTL:
            return result
        del _ce_cache[key]
    return None


def get_cache_age(key):
    """Return cache age in seconds for a key, or None if not cached."""
    if key in _ce_cache:
        _, ts = _ce_cache[key]
        return round(time.time() - ts)
    return None


def _cache_set(key, value):
    """Store result in cache."""
    _ce_cache[key] = (value, time.time())


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _months_ago(today, months):
    """Calculate a date N months before today, returning the 1st of that month.
    Uses proper calendar math instead of day approximation.
    """
    m = today.month - months
    y = today.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return today.replace(year=y, month=m, day=1)


def _friendly_error(msg: str) -> str:
    """Return a user-friendly error message for common AWS auth issues."""
    m = msg.lower()
    if 'token' in m and ('expired' in m or 'refresh' in m):
        return f'SSO token expired — run: aws sso login --profile <name>  ({msg})'
    if 'sso' in m and 'login' in m:
        return f'SSO login required — run: aws sso login --profile <name>  ({msg})'
    if 'credentialretrievalerror' in m or 'unable to locate credentials' in m:
        return f'No credentials found for this profile — check ~/.aws/config  ({msg})'
    if 'accessdenied' in m or 'not authorized' in m:
        return f'Access denied — ensure ce:GetCostAndUsage permission is granted  ({msg})'
    return msg


# ---------------------------------------------------------------------------
# Profile Discovery
# ---------------------------------------------------------------------------

def _parse_sso_profiles(conf_path):
    """
    Parse ~/.aws/config line-by-line and return a set of profile names
    that have SSO configuration (sso_start_url, sso_account_id,
    sso_role_name, or sso_session keys that are NOT commented out).
    This avoids configparser quirks with '#' in URL values and
    inline comments.
    """
    SSO_KEYS = {'sso_start_url', 'sso_account_id', 'sso_role_name', 'sso_session'}
    sso_profiles = set()
    current_profile = None
    current_has_sso = False

    try:
        with open(conf_path, encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                # Skip blank lines and comment lines
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                # Section header
                if line.startswith('[') and line.endswith(']'):
                    if current_profile and current_has_sso:
                        sso_profiles.add(current_profile)
                    section = line[1:-1].strip()
                    low = section.lower()
                    if low.startswith('sso-session') or low == 'default':
                        current_profile = None
                    elif low.startswith('profile '):
                        current_profile = section[len('profile '):].strip()
                    else:
                        current_profile = section
                    current_has_sso = False
                # Key = value line
                elif '=' in line and current_profile:
                    key = line.split('=', 1)[0].strip().lower()
                    if key in SSO_KEYS:
                        current_has_sso = True
        # Handle last profile in file
        if current_profile and current_has_sso:
            sso_profiles.add(current_profile)
    except Exception:
        pass

    return sso_profiles


def get_aws_profiles():
    """
    Discover ALL named profiles from ~/.aws/credentials and ~/.aws/config.
    Includes SSO profiles, assumed-role profiles, and any other type.
    'sso-session' blocks are excluded (they are not usable as standalone profiles).
    Returns list of dicts: [{name: str, sso: bool}] sorted by name.
    """
    profiles = set()

    # --- credentials file (standard IAM key profiles) ---
    creds_path = os.path.expanduser('~/.aws/credentials')
    if os.path.exists(creds_path):
        config = configparser.ConfigParser()
        config.read(creds_path, encoding='utf-8')
        for section in config.sections():
            profiles.add(section)

    # --- config file: collect profile names ---
    conf_path = os.path.expanduser('~/.aws/config')
    if os.path.exists(conf_path):
        config = configparser.ConfigParser()
        config.read(conf_path, encoding='utf-8')
        for section in config.sections():
            if section.startswith('sso-session '):
                continue
            name = section[len('profile '):] if section.startswith('profile ') else section
            profiles.add(name)

    # --- detect SSO profiles by direct line-by-line parse ---
    sso_set = set()
    if os.path.exists(conf_path):
        sso_set = _parse_sso_profiles(conf_path)

    result = sorted(
        [{'name': p, 'sso': p in sso_set} for p in profiles],
        key=lambda x: x['name'].lower()
    )
    if DEMO_MODE:
        result = [{'name': _demo_profile(p['name']), 'sso': p['sso']} for p in result]
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ce_client(session):
    """Always create CE client in us-east-1 regardless of profile region."""
    return session.client('ce', region_name=CE_REGION)


def _projection(current_spend, elapsed_days, days_in_month):
    """Project end-of-month cost from current spend.
    Requires at least 3 days of data for reliable projection.
    Uses weighted average giving more weight to recent spending.
    """
    if elapsed_days <= 0:
        return 0.0
    if elapsed_days < 3:
        # Too few data points — return current spend as-is
        return round(current_spend, 2)
    daily_avg = current_spend / elapsed_days
    return round(daily_avg * days_in_month, 2)


ANOMALY_THRESHOLD_PCT = 20  # configurable


def _detect_anomalies(monthly_totals):
    """Detect cost anomalies using month-over-month and moving average comparison.
    Returns anomalies with severity: critical (>=100%), warning (>=THRESHOLD%).
    """
    months = sorted(monthly_totals.keys())
    if len(months) < 2:
        return []

    anomalies = []
    for i in range(1, len(months)):
        curr = monthly_totals[months[i]]
        prev = monthly_totals[months[i - 1]]

        # Skip if both are negligible
        if curr < 1.0 and prev < 1.0:
            continue

        # Handle prev=0: if curr > $10, flag as new spend
        if prev <= 0:
            if curr >= 10.0:
                anomalies.append({
                    'month': months[i],
                    'prev_month': months[i - 1],
                    'prev_cost': 0.0,
                    'curr_cost': round(curr, 2),
                    'change_pct': 100.0,
                    'severity': 'warning',
                    'type': 'new_spend',
                })
            continue

        change_pct = ((curr - prev) / prev) * 100

        # Also compare against moving average (last 3 months) if available
        ma_severity = None
        if i >= 3:
            ma = sum(monthly_totals[months[j]] for j in range(i-3, i)) / 3
            if ma > 0:
                ma_change = ((curr - ma) / ma) * 100
                if ma_change >= 100:
                    ma_severity = 'critical'
                elif ma_change >= ANOMALY_THRESHOLD_PCT:
                    ma_severity = 'warning'

        if change_pct >= ANOMALY_THRESHOLD_PCT:
            mom_severity = 'critical' if change_pct >= 100 else 'warning'
            # Use the higher severity between MoM and MA
            severity = 'critical' if (mom_severity == 'critical' or ma_severity == 'critical') else 'warning'
            anomalies.append({
                'month': months[i],
                'prev_month': months[i - 1],
                'prev_cost': round(prev, 2),
                'curr_cost': round(curr, 2),
                'change_pct': round(change_pct, 1),
                'severity': severity,
                'type': 'spike',
            })

    return anomalies


# ---------------------------------------------------------------------------
# Cost Data — Main Dashboard
# ---------------------------------------------------------------------------

def fetch_profile_costs(profile_name, months_back=13, start_date=None, end_date=None):
    """
    Fetch monthly cost breakdown by SERVICE for a single profile.
    Accepts either months_back (default) or explicit start_date/end_date (YYYY-MM-DD).
    Returns structured dict with monthly_data, service_totals, projection, anomalies.
    """
    _audit_logger.info(f'COST_QUERY profile={profile_name} months_back={months_back}')

    # Check cache
    cache_k = _cache_key('fetch_profile_costs', profile_name, months_back, start_date, end_date)
    cached = _cache_get(cache_k)
    if cached is not None:
        return cached

    try:
        session = boto3.Session(profile_name=profile_name)
        ce = _ce_client(session)

        today = datetime.utcnow()

        if start_date and end_date:
            # Normalize to month boundaries; cap end to today
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            q_start = sd.replace(day=1).strftime('%Y-%m-%d')
            q_end   = min(ed, today).strftime('%Y-%m-%d')
            if q_end <= q_start:
                q_end = today.strftime('%Y-%m-%d')
            history_start = q_start
            history_end   = q_end
        else:
            months_capped = min(months_back, 12)
            q_start = _months_ago(today, months_capped).strftime('%Y-%m-%d')
            q_end   = today.strftime('%Y-%m-%d')
            history_start = _months_ago(today, 12).strftime('%Y-%m-%d')
            history_end   = today.replace(day=1).strftime('%Y-%m-%d')

        start_date = q_start
        end_date   = q_end

        # Monthly cost by SERVICE
        resp = ce.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
        )

        # Historical totals (RECORD_TYPE: Usage vs Credit)
        # Guard: history_end must be > history_start and <= today
        if history_end <= history_start:
            history_end = today.strftime('%Y-%m-%d')
        hist_resp = ce.get_cost_and_usage(
            TimePeriod={'Start': history_start, 'End': history_end},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'RECORD_TYPE'}],
        )

        total_usage, total_credits = 0.0, 0.0
        for period in hist_resp['ResultsByTime']:
            for group in period['Groups']:
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if group['Keys'][0] == 'Credit':
                    total_credits += amount
                else:
                    total_usage += amount

        monthly_data = {}
        service_totals = {}
        monthly_totals = {}

        for period in resp['ResultsByTime']:
            month = period['TimePeriod']['Start'][:7]
            monthly_data[month] = {}
            month_total = 0.0
            for group in period['Groups']:
                service = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount >= 0.01:
                    monthly_data[month][service] = round(amount, 4)
                    service_totals[service] = service_totals.get(service, 0) + amount
                    month_total += amount
            monthly_totals[month] = month_total

        current_month = today.strftime('%Y-%m')
        current_spend = monthly_totals.get(current_month, 0.0)
        elapsed_days = today.day
        days_in_month = calendar.monthrange(today.year, today.month)[1]

        # Sort services by total cost descending
        service_totals = dict(sorted(service_totals.items(), key=lambda x: x[1], reverse=True))

        pn = _demo_profile(profile_name) if DEMO_MODE else profile_name
        result = {
            'profile': pn,
            'status': 'success',
            'monthly_data': monthly_data,
            'monthly_totals': {k: round(v, 2) for k, v in monthly_totals.items()},
            'service_totals': {k: round(v, 2) for k, v in service_totals.items()},
            'current_spend': round(current_spend, 2),
            'projection': _projection(current_spend, elapsed_days, days_in_month),
            'total_usage': round(total_usage, 2),
            'total_credits': round(total_credits, 2),
            'current_month': current_month,
            'anomalies': _detect_anomalies(monthly_totals),
        }

        _cache_set(cache_k, result)
        return result

    except Exception as exc:
        pn = _demo_profile(profile_name) if DEMO_MODE else profile_name
        return {'profile': pn, 'status': 'error', 'error': _friendly_error(str(exc))}


def fetch_all_profiles_costs(profile_names, months_back=13):
    """Fetch costs for multiple profiles in parallel."""
    # In demo mode, resolve masked names back to real names for API calls
    if DEMO_MODE:
        reverse_map = {v: k for k, v in _demo_map.items()}
        real_names = [reverse_map.get(p, p) for p in profile_names]
    else:
        real_names = profile_names

    _audit_logger.info(f'MULTI_COST_QUERY profiles={real_names}')
    results = []
    with ThreadPoolExecutor(max_workers=min(len(real_names), MAX_THREAD_WORKERS)) as executor:
        futures = {executor.submit(fetch_profile_costs, p, months_back): p for p in real_names}
        for future in as_completed(futures):
            results.append(future.result())

    # In demo mode, mask profile names and account IDs in results
    if DEMO_MODE:
        for r in results:
            if 'profile' in r:
                r['profile'] = _demo_profile(r['profile'])
            if 'account_id' in r:
                r['account_id'] = _demo_account(r['account_id'])
    return results


# ---------------------------------------------------------------------------
# Service Detail
# ---------------------------------------------------------------------------

def fetch_service_detail(profile_name, service_name, months_back=6):
    """
    Monthly + daily cost for a specific service in a specific profile.
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        ce = _ce_client(session)

        today = datetime.utcnow()
        end_date = today.strftime('%Y-%m-%d')
        start_monthly = _months_ago(today, months_back).strftime('%Y-%m-%d')
        start_daily = today.replace(day=1).strftime('%Y-%m-%d')

        filter_expr = {'Dimensions': {'Key': 'SERVICE', 'Values': [service_name]}}

        monthly_resp = ce.get_cost_and_usage(
            TimePeriod={'Start': start_monthly, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            Filter=filter_expr,
        )

        daily_resp = ce.get_cost_and_usage(
            TimePeriod={'Start': start_daily, 'End': end_date},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            Filter=filter_expr,
        )

        monthly = {}
        for period in monthly_resp['ResultsByTime']:
            month = period['TimePeriod']['Start'][:7]
            amount = float(period['Total']['UnblendedCost']['Amount'])
            monthly[month] = round(amount, 2)

        daily = {}
        for period in daily_resp['ResultsByTime']:
            day = period['TimePeriod']['Start']
            amount = float(period['Total']['UnblendedCost']['Amount'])
            daily[day] = round(amount, 4)

        result = {
            'profile': _demo_profile(profile_name) if DEMO_MODE else profile_name,
            'service': service_name,
            'status': 'success',
            'monthly': monthly,
            'daily': daily,
        }
        return result

    except Exception as exc:
        pn = _demo_profile(profile_name) if DEMO_MODE else profile_name
        return {'profile': pn, 'service': service_name, 'status': 'error', 'error': str(exc)}


# ---------------------------------------------------------------------------
# Region Distribution
# ---------------------------------------------------------------------------

def fetch_credits(profile_name):
    """
    Fetch credit usage history via CE RECORD_TYPE=Credit.
    CE returns credits as negative amounts; we store them as positive.
    Full credit details (name, issued amount, expiration) are only available
    in the AWS Billing Console — not accessible via public boto3 API.
    """
    _audit_logger.info(f'CREDITS_QUERY profile={profile_name}')
    try:
        session = boto3.Session(profile_name=profile_name)
        ce = _ce_client(session)
        today = datetime.utcnow()

        end_date = today.strftime('%Y-%m-%d')
        start_12m = _months_ago(today, 12).strftime('%Y-%m-%d')

        # Monthly credit totals
        resp = ce.get_cost_and_usage(
            TimePeriod={'Start': start_12m, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            Filter={'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit']}},
        )

        monthly_credits = {}
        for period in resp['ResultsByTime']:
            month = period['TimePeriod']['Start'][:7]
            amount = float(period['Total']['UnblendedCost']['Amount'])
            if amount != 0:
                monthly_credits[month] = round(abs(amount), 2)

        current_month = today.strftime('%Y-%m')
        prev_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        total_used = round(sum(monthly_credits.values()), 2)
        current_credits = monthly_credits.get(current_month, 0)

        # Status: active if credits applied this month or last month
        if not monthly_credits:
            status_type = 'none'
        elif current_credits > 0 or monthly_credits.get(prev_month, 0) > 0:
            status_type = 'active'
        else:
            status_type = 'exhausted'

        last_credit_month = max(monthly_credits.keys()) if monthly_credits else None

        # Try to get per-subscription breakdown (subscription = individual credit)
        credit_items = []
        try:
            sub_resp = ce.get_cost_and_usage(
                TimePeriod={'Start': start_12m, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                Filter={'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit']}},
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SUBSCRIPTION_ID'}],
            )
            sub_totals = {}
            sub_monthly = {}
            for period in sub_resp['ResultsByTime']:
                month = period['TimePeriod']['Start'][:7]
                for group in period['Groups']:
                    sub_id = group['Keys'][0]
                    amount = abs(float(group['Metrics']['UnblendedCost']['Amount']))
                    if amount > 0:
                        sub_totals[sub_id] = sub_totals.get(sub_id, 0) + amount
                        if sub_id not in sub_monthly:
                            sub_monthly[sub_id] = {}
                        sub_monthly[sub_id][month] = round(amount, 2)

            # Determine per-credit status
            for sub_id, total in sub_totals.items():
                s_monthly = sub_monthly.get(sub_id, {})
                is_active = s_monthly.get(current_month, 0) > 0 or s_monthly.get(prev_month, 0) > 0
                sorted_months = sorted(s_monthly.keys())
                first_month = sorted_months[0] if sorted_months else None
                last_month  = sorted_months[-1] if sorted_months else None
                credit_items.append({
                    'id': sub_id,
                    'total_used': round(total, 2),
                    'monthly': s_monthly,
                    'active': is_active,
                    'first_used': first_month,
                    'last_used': last_month,
                })
            credit_items.sort(key=lambda x: x['total_used'], reverse=True)
        except Exception:
            pass  # SUBSCRIPTION_ID grouping may not be available for all accounts

        return {
            'status': 'success',
            'status_type': status_type,          # 'active' | 'exhausted' | 'none'
            'monthly_credits': monthly_credits,  # {month: amount_applied}
            'total_used': total_used,
            'current_month_credits': current_credits,
            'last_credit_month': last_credit_month,
            'credit_items': credit_items,        # per-subscription breakdown (if available)
        }

    except Exception as exc:
        return {'status': 'error', 'error': _friendly_error(str(exc))}


def fetch_cost_report(profile_name, granularity='DAILY', start_date=None, end_date=None):
    """
    Cost breakdown by SERVICE with DAILY / WEEKLY / MONTHLY granularity.
    Returns period columns + service rows for the cross-tab table.
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        ce = _ce_client(session)
        today = datetime.utcnow()

        if not start_date:
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
        if not end_date:
            end_date = today.strftime('%Y-%m-%d')

        # CE end date must not be today for DAILY (use tomorrow boundary)
        resp = ce.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity=granularity,
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
        )

        periods = []
        service_data = {}   # {service: {period_start: amount}}
        period_totals = {}  # {period_start: total}

        for period in resp['ResultsByTime']:
            p_start = period['TimePeriod']['Start']
            p_end   = period['TimePeriod']['End']
            periods.append({'start': p_start, 'end': p_end})
            period_totals[p_start] = 0.0

            for group in period['Groups']:
                svc    = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount <= 0:
                    continue
                if svc not in service_data:
                    service_data[svc] = {}
                service_data[svc][p_start] = round(amount, 4)
                period_totals[p_start] = round(period_totals.get(p_start, 0) + amount, 4)

        service_totals = {
            svc: round(sum(v for v in service_data[svc].values()), 2)
            for svc in service_data
        }
        sorted_svcs = sorted(service_totals, key=lambda x: service_totals[x], reverse=True)
        total_cost  = round(sum(service_totals.values()), 2)

        days = max((datetime.strptime(end_date, '%Y-%m-%d') -
                    datetime.strptime(start_date, '%Y-%m-%d')).days, 1)
        avg_daily = round(total_cost / days, 2)

        return {
            'status':        'success',
            'granularity':   granularity,
            'periods':       periods,
            'period_totals': {p['start']: round(period_totals.get(p['start'], 0), 2) for p in periods},
            'services': [
                {
                    'name':      svc,
                    'total':     service_totals[svc],
                    'by_period': service_data[svc],
                }
                for svc in sorted_svcs
            ],
            'total_cost':     total_cost,
            'avg_daily_cost': avg_daily,
            'service_count':  len(sorted_svcs),
        }

    except Exception as exc:
        return {'status': 'error', 'error': _friendly_error(str(exc))}


# Services that are global / marketplace / SaaS — always report under us-east-1
# but don't represent actual regional infrastructure usage.
_GLOBAL_LIKE_KEYWORDS = {
    'Route 53', 'CloudFront', 'WAF', 'Shield', 'Global Accelerator',
    'IAM', 'Organizations', 'Cost Explorer', 'Budgets', 'Support',
    'Marketplace', 'Contract', 'ManagedServices', 'MongoDB Atlas',
    'Savings Plans', 'Tax', 'SaaS', 'Subscription',
}


def _is_global_service(service_name):
    """Check if a service is global/marketplace (not tied to a specific region)."""
    sn = service_name.lower()
    for kw in _GLOBAL_LIKE_KEYWORDS:
        if kw.lower() in sn:
            return True
    return False


def fetch_region_distribution(profile_name, months_back=3, start_date=None, end_date=None):
    """Cost breakdown by AWS Region for the given profile.
    Separates actual regional costs from global/marketplace services
    that report under us-east-1 but aren't real regional infrastructure.
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        ce = _ce_client(session)

        today = datetime.utcnow()
        if start_date and end_date:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            start_date = sd.replace(day=1).strftime('%Y-%m-%d')
            end_date   = min(ed, today).strftime('%Y-%m-%d')
            if end_date <= start_date:
                end_date = today.strftime('%Y-%m-%d')
        else:
            end_date   = today.strftime('%Y-%m-%d')
            start_date = _months_ago(today, months_back).strftime('%Y-%m-%d')

        # Query by REGION + SERVICE to separate global/marketplace from real regional
        resp = ce.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'REGION'},
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ],
        )

        region_totals = {}
        monthly_by_region = {}
        global_services_total = {}      # service → total cost
        global_services_monthly = {}    # month → {service → cost}

        for period in resp['ResultsByTime']:
            month = period['TimePeriod']['Start'][:7]
            if month not in monthly_by_region:
                monthly_by_region[month] = {}
            if month not in global_services_monthly:
                global_services_monthly[month] = {}

            for group in period['Groups']:
                region = group['Keys'][0] or 'Global'
                service = group['Keys'][1]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount < 0.01:
                    continue

                # Check if this is a global/marketplace service reporting under us-east-1
                # Also treat the empty-region "Global" entries as global
                is_global = (region == 'us-east-1' and _is_global_service(service)) or region in ('Global', 'global', '')

                if is_global:
                    cat = 'Global / Marketplace'
                    global_services_total[service] = global_services_total.get(service, 0) + amount
                    global_services_monthly[month][service] = round(
                        global_services_monthly[month].get(service, 0) + amount, 2)
                    # Add to region_totals under the unified global category
                    region_totals[cat] = region_totals.get(cat, 0) + amount
                    monthly_by_region[month][cat] = round(
                        monthly_by_region[month].get(cat, 0) + amount, 2)
                else:
                    region_totals[region] = region_totals.get(region, 0) + amount
                    monthly_by_region[month][region] = round(
                        monthly_by_region[month].get(region, 0) + amount, 2)

        region_totals = dict(sorted(region_totals.items(), key=lambda x: x[1], reverse=True))

        return {
            'status': 'success',
            'region_totals': {k: round(v, 2) for k, v in region_totals.items()},
            'monthly_by_region': monthly_by_region,
            'global_services': {k: round(v, 2) for k, v in
                                sorted(global_services_total.items(), key=lambda x: x[1], reverse=True)},
        }

    except Exception as exc:
        return {'status': 'error', 'error': _friendly_error(str(exc))}


# ---------------------------------------------------------------------------
# Budget Tracking
# ---------------------------------------------------------------------------

def fetch_budgets(profile_name):
    """Fetch AWS Budgets for the given profile."""
    _audit_logger.info(f'BUDGET_QUERY profile={profile_name}')
    try:
        session = boto3.Session(profile_name=profile_name)
        sts = session.client('sts')
        account_id = sts.get_caller_identity()['Account']

        budgets_client = session.client('budgets', region_name='us-east-1')
        resp = budgets_client.describe_budgets(AccountId=account_id)

        budgets = []
        for b in resp.get('Budgets', []):
            try:
                limit = float(b['BudgetLimit']['Amount'])
                actual = float(b.get('CalculatedSpend', {}).get('ActualSpend', {}).get('Amount', 0))
                forecasted = float(b.get('CalculatedSpend', {}).get('ForecastedSpend', {}).get('Amount', 0))
                budgets.append({
                    'name': b['BudgetName'],
                    'type': b['BudgetType'],
                    'limit': round(limit, 2),
                    'actual': round(actual, 2),
                    'forecasted': round(forecasted, 2),
                    'pct_used': round((actual / limit * 100) if limit > 0 else 0, 1),
                    'unit': b['BudgetLimit']['Unit'],
                })
            except (KeyError, ValueError):
                continue

        aid = _demo_account(account_id) if DEMO_MODE else account_id
        return {'status': 'success', 'budgets': budgets, 'account_id': aid}

    except Exception as exc:
        return {'status': 'error', 'error': _friendly_error(str(exc))}


# ---------------------------------------------------------------------------
# EC2 Inventory
# ---------------------------------------------------------------------------

def _fetch_ec2_for_region(session, region):
    """Fetch EC2 instances for one region, including attached EBS volumes."""
    try:
        ec2 = session.client('ec2', region_name=region)
        resp = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped']}]
        )

        # Collect all volume IDs to fetch details in one call
        all_volume_ids = []
        instances_raw = []
        for reservation in resp['Reservations']:
            for inst in reservation['Instances']:
                instances_raw.append(inst)
                for bdm in inst.get('BlockDeviceMappings', []):
                    vol_id = bdm.get('Ebs', {}).get('VolumeId')
                    if vol_id:
                        all_volume_ids.append(vol_id)

        # Batch fetch volume details (size, type) — single API call
        vol_details = {}
        if all_volume_ids:
            try:
                vol_resp = ec2.describe_volumes(VolumeIds=all_volume_ids)
                for vol in vol_resp.get('Volumes', []):
                    vol_details[vol['VolumeId']] = {
                        'size_gb': vol.get('Size', 0),
                        'type': vol.get('VolumeType', ''),
                        'encrypted': vol.get('Encrypted', False),
                    }
            except Exception:
                pass  # volume details are optional

        # Batch fetch instance type specs (vCPU, RAM) — single API call
        type_specs = {}
        unique_types = list({inst['InstanceType'] for inst in instances_raw})
        if unique_types:
            try:
                # describe_instance_types accepts max 100 per call
                for i in range(0, len(unique_types), 100):
                    batch = unique_types[i:i+100]
                    it_resp = ec2.describe_instance_types(InstanceTypes=batch)
                    for it in it_resp.get('InstanceTypes', []):
                        type_specs[it['InstanceType']] = {
                            'vcpu': it.get('VCpuInfo', {}).get('DefaultVCpus', 0),
                            'ram_gb': round(it.get('MemoryInfo', {}).get('SizeInMiB', 0) / 1024, 1),
                        }
            except Exception:
                pass  # instance type details are optional

        instances = []
        for inst in instances_raw:
            tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])}
            untagged = 'Name' not in tags and 'Environment' not in tags and 'env' not in tags

            # Build EBS disk list
            disks = []
            total_disk_gb = 0
            for bdm in inst.get('BlockDeviceMappings', []):
                vol_id = bdm.get('Ebs', {}).get('VolumeId')
                if not vol_id:
                    continue
                vd = vol_details.get(vol_id, {})
                size = vd.get('size_gb', 0)
                total_disk_gb += size
                disks.append({
                    'volume_id': vol_id,
                    'device': bdm.get('DeviceName', ''),
                    'size_gb': size,
                    'type': vd.get('type', ''),
                    'encrypted': vd.get('encrypted', False),
                })

            specs = type_specs.get(inst['InstanceType'], {})
            instances.append({
                'id': inst['InstanceId'],
                'type': inst['InstanceType'],
                'state': inst['State']['Name'],
                'region': region,
                'name': tags.get('Name', '-'),
                'environment': tags.get('Environment', tags.get('env', '-')),
                'untagged': untagged,
                'launch_time': inst['LaunchTime'].isoformat() if 'LaunchTime' in inst else '-',
                'vcpu': specs.get('vcpu', 0),
                'ram_gb': specs.get('ram_gb', 0),
                'disk_count': len(disks),
                'total_disk_gb': total_disk_gb,
                'disks': disks,
            })
        return instances
    except Exception:
        return []


def fetch_ec2_inventory(profile_name):
    """Fetch EC2 inventory across all enabled regions in parallel."""
    _audit_logger.info(f'EC2_INVENTORY profile={profile_name}')
    try:
        session = boto3.Session(profile_name=profile_name)

        # Get enabled regions
        ec2_global = session.client('ec2', region_name='us-east-1')
        regions_resp = ec2_global.describe_regions(AllRegions=False)
        regions = [r['RegionName'] for r in regions_resp['Regions']]

        all_instances = []
        with ThreadPoolExecutor(max_workers=min(len(regions), MAX_THREAD_WORKERS)) as executor:
            futures = [executor.submit(_fetch_ec2_for_region, session, r) for r in regions]
            for future in as_completed(futures):
                all_instances.extend(future.result())

        running = [i for i in all_instances if i['state'] == 'running']
        stopped = [i for i in all_instances if i['state'] == 'stopped']
        untagged = [i for i in all_instances if i['untagged']]

        return {
            'status': 'success',
            'instances': all_instances,
            'summary': {
                'total': len(all_instances),
                'running': len(running),
                'stopped': len(stopped),
                'untagged': len(untagged),
            },
        }

    except Exception as exc:
        return {'status': 'error', 'error': _friendly_error(str(exc))}
