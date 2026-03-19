"""
Topology Module — Report Generator
Generates HTML, CSV, and PDF reports from topology scan results.
"""

import os
import csv
from html import escape
from datetime import datetime
from collections import defaultdict

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


def _ts():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


TYPE_LABELS = {
    'vpc': 'VPC', 'subnet': 'Subnet', 'igw': 'Internet Gateway',
    'nat': 'NAT Gateway', 'route_table': 'Route Table', 'peering': 'VPC Peering',
    'security_group': 'Security Group', 'nacl': 'Network ACL',
    'vpc_endpoint': 'VPC Endpoint', 'eip': 'Elastic IP',
    'ec2': 'EC2 Instance', 'rds': 'RDS Instance', 'elb': 'Load Balancer',
    'lambda': 'Lambda Function', 'transit_gateway': 'Transit Gateway',
    'tgw_attachment': 'TGW Attachment', 'direct_connect': 'Direct Connect',
    'dx_gateway': 'DX Gateway', 'acm': 'ACM Certificate',
    'eks': 'EKS Cluster', 'cloudfront': 'CloudFront Distribution',
    's3': 'S3 Bucket', 'organization': 'Organization', 'org_account': 'Org Account',
    'ecs_cluster': 'ECS Cluster', 'ecs_service': 'ECS Service',
    'vpn_gateway': 'VPN Gateway', 'vpn_connection': 'VPN Connection',
    'customer_gateway': 'Customer Gateway',
    'network_firewall': 'Network Firewall',
    'hosted_zone': 'Route53 Hosted Zone',
    'api_gateway': 'API Gateway',
    'eni': 'Network Interface',
}

TYPE_ICONS = {
    'vpc': '#ff9900', 'subnet': '#1a73e8', 'igw': '#e53935', 'nat': '#43a047',
    'route_table': '#8e24aa', 'peering': '#00acc1', 'security_group': '#f4511e',
    'nacl': '#6d4c41', 'vpc_endpoint': '#546e7a', 'eip': '#fdd835',
    'ec2': '#ff9900', 'rds': '#2e7d32', 'elb': '#7b1fa2', 'lambda': '#ff6f00',
    'transit_gateway': '#d32f2f', 'tgw_attachment': '#c62828', 'direct_connect': '#1565c0',
    'dx_gateway': '#0d47a1', 'acm': '#00897b', 'eks': '#ff9900', 'cloudfront': '#7c4dff',
    's3': '#43a047', 'organization': '#ff9900', 'org_account': '#ffa726',
    'ecs_cluster': '#ff9900', 'ecs_service': '#ff6600',
    'vpn_gateway': '#8c4fff', 'vpn_connection': '#7c3aed',
    'customer_gateway': '#6d28d9',
    'network_firewall': '#dc2626',
    'hosted_zone': '#2563eb',
    'api_gateway': '#8b5cf6',
    'eni': '#6b7280',
}

# Display order for resource types in the sidebar / sections
TYPE_ORDER = [
    'vpc', 'subnet', 'igw', 'nat', 'route_table', 'security_group', 'nacl',
    'vpc_endpoint', 'eip', 'eni', 'ec2', 'ecs_cluster', 'ecs_service',
    'rds', 'elb', 'lambda', 'eks', 'api_gateway', 'network_firewall',
    's3', 'cloudfront', 'acm', 'hosted_zone', 'peering',
    'transit_gateway', 'tgw_attachment', 'direct_connect', 'dx_gateway',
    'vpn_gateway', 'vpn_connection', 'customer_gateway',
    'organization', 'org_account',
]


def _e(s):
    """HTML-escape helper."""
    return escape(str(s)) if s else ''


def generate_html(results: dict, ts: str = None) -> str:
    profile = results.get('profile', 'unknown')
    account_id = results.get('account_id', 'unknown')
    meta = results.get('metadata', {})
    resources = results.get('resources', [])
    ts = ts or _ts()
    timestamp = meta.get('timestamp', '')
    duration = meta.get('scan_duration_seconds', 0)
    total = meta.get('resource_count', 0)
    regions_count = meta.get('regions_scanned', 0)
    type_counts = meta.get('type_counts', {})

    # ── Group resources by type ──
    by_type = defaultdict(list)
    for r in resources:
        by_type[r.get('type', 'unknown')].append(r)

    # ── Group resources by VPC ──
    by_vpc = defaultdict(list)
    vpcs = {}
    for r in resources:
        if r.get('type') == 'vpc':
            vpcs[r['id']] = r
        vid = r.get('vpc_id') or r.get('id') if r.get('type') == 'vpc' else r.get('vpc_id', '')
        if vid:
            by_vpc[vid].append(r)

    # ordered types present in scan
    ordered_types = [t for t in TYPE_ORDER if t in by_type]
    for t in sorted(by_type.keys()):
        if t not in ordered_types:
            ordered_types.append(t)

    # ── Build sidebar nav links ──
    nav_links = ''
    for idx, t in enumerate(ordered_types, 1):
        label = TYPE_LABELS.get(t, t)
        count = len(by_type[t])
        color = TYPE_ICONS.get(t, '#64748b')
        nav_links += (
            f'<a class="nav-link" href="#type-{t}">'
            f'<span class="nav-dot" style="background:{color}"></span>'
            f'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
            f'{idx}. {_e(label)}</span>'
            f'<span class="count-badge">{count}</span></a>\n'
        )

    # VPC nav links
    vpc_nav = ''
    for vid, vr in sorted(vpcs.items(), key=lambda x: x[1].get('name', '')):
        vname = vr.get('name', vid)
        vcidr = vr.get('cidr', '')
        vcount = len(by_vpc.get(vid, []))
        vpc_nav += (
            f'<a class="nav-link" href="#vpc-{_e(vid)}">'
            f'<span class="nav-dot" style="background:#ff9900"></span>'
            f'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
            f'{_e(vname)}</span>'
            f'<span class="count-badge">{vcount}</span></a>\n'
        )

    # ── Summary cards ──
    vpc_count = type_counts.get('vpc', 0)
    subnet_count = type_counts.get('subnet', 0)
    sg_count = type_counts.get('security_group', 0)
    ec2_count = type_counts.get('ec2', 0)

    # ── Resource summary table rows ──
    summary_rows = ''
    for t in ordered_types:
        label = TYPE_LABELS.get(t, t)
        count = type_counts.get(t, len(by_type[t]))
        color = TYPE_ICONS.get(t, '#64748b')
        pct = round(count / total * 100, 1) if total > 0 else 0
        summary_rows += (
            f'<tr><td><span class="type-dot" style="background:{color}"></span> {_e(label)}</td>'
            f'<td style="text-align:right;font-weight:700">{count}</td>'
            f'<td style="width:140px"><span class="pillar-bar">'
            f'<span class="pillar-bar-fill" style="width:{pct}%;background:{color}"></span>'
            f'</span></td>'
            f'<td style="text-align:right;color:#64748b;font-size:9pt">{pct}%</td></tr>\n'
        )

    # ── Per-type sections ──
    type_sections = ''
    for idx, t in enumerate(ordered_types, 1):
        label = TYPE_LABELS.get(t, t)
        color = TYPE_ICONS.get(t, '#64748b')
        items = sorted(by_type[t], key=lambda r: (r.get('region', ''), r.get('name', '')))

        type_sections += f'<h2 class="section-title" id="type-{t}">{idx}. {_e(label)}</h2>\n'
        type_sections += f'<p style="font-size:10pt;color:#64748b;margin-bottom:12px">{len(items)} resource{"s" if len(items) != 1 else ""} found</p>\n'

        type_sections += '<table class="resource-table"><thead><tr>'
        type_sections += '<th>Name</th><th>ID</th><th>Region</th><th>VPC</th><th>Details</th>'
        type_sections += '</tr></thead><tbody>\n'

        for r in items:
            rid = r.get('id', '')
            rname = r.get('name', '') or rid
            region = r.get('region', '')
            vpc_id = r.get('vpc_id', '') or ''
            # Build details from notable fields
            details_parts = []
            for key in ('cidr', 'state', 'status', 'az', 'instance_type', 'engine',
                        'runtime', 'scheme', 'lb_type', 'public_ip', 'private_ip'):
                val = r.get(key)
                if val:
                    details_parts.append(f'{key}: {val}')
            details = '; '.join(details_parts[:4])

            type_sections += (
                f'<tr><td style="font-weight:600">{_e(rname)}</td>'
                f'<td class="mono">{_e(rid)}</td>'
                f'<td>{_e(region)}</td>'
                f'<td class="mono">{_e(vpc_id)}</td>'
                f'<td style="color:#64748b;font-size:9pt">{_e(details)}</td></tr>\n'
            )

        type_sections += '</tbody></table>\n'

    # ── Per-VPC sections ──
    vpc_sections = ''
    for vid in sorted(vpcs.keys(), key=lambda v: vpcs[v].get('name', '')):
        vr = vpcs[vid]
        vname = vr.get('name', vid)
        vcidr = vr.get('cidr', '')
        vregion = vr.get('region', '')
        vitems = by_vpc.get(vid, [])

        # Group VPC resources by type
        vpc_by_type = defaultdict(list)
        for r in vitems:
            vpc_by_type[r.get('type', 'unknown')].append(r)

        vpc_sections += f'<h2 class="section-title" id="vpc-{_e(vid)}">{_e(vname)}</h2>\n'
        vpc_sections += (
            f'<table class="meta-table">'
            f'<tr><td class="label">VPC ID:</td><td class="value mono">{_e(vid)}</td></tr>'
            f'<tr><td class="label">CIDR:</td><td class="value">{_e(vcidr)}</td></tr>'
            f'<tr><td class="label">Region:</td><td class="value">{_e(vregion)}</td></tr>'
            f'<tr><td class="label">Resources:</td><td class="value">{len(vitems)}</td></tr>'
            f'</table>\n'
        )

        for vt in TYPE_ORDER:
            if vt not in vpc_by_type or vt == 'vpc':
                continue
            vlabel = TYPE_LABELS.get(vt, vt)
            vcolor = TYPE_ICONS.get(vt, '#64748b')
            vt_items = sorted(vpc_by_type[vt], key=lambda r: r.get('name', ''))

            vpc_sections += (
                f'<h3 class="sub-heading" style="color:{vcolor}">'
                f'{_e(vlabel)} ({len(vt_items)})</h3>\n'
            )
            vpc_sections += '<ul class="resource-list">\n'
            for r in vt_items:
                rname = r.get('name', '') or r.get('id', '')
                extra = ''
                if r.get('cidr'):
                    extra += f' — {r["cidr"]}'
                if r.get('az'):
                    extra += f' ({r["az"]})'
                if r.get('state') or r.get('status'):
                    extra += f' [{r.get("state") or r.get("status")}]'
                vpc_sections += f'  <li><span class="type-dot" style="background:{vcolor}"></span> {_e(rname)}{_e(extra)}</li>\n'
            vpc_sections += '</ul>\n'

    # ── Build full HTML ──
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Network Topology Report — {_e(profile)}</title>
<style>
@media print {{
  body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .page-break {{ page-break-before: always; }}
  .no-print, .nav-sidebar {{ display: none !important; }}
  .main-content {{ margin-left: 0 !important; max-width: 100% !important; }}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{
  font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  font-size: 11pt; line-height: 1.6; color: #1a1a1a; background: #f1f5f9;
}}
/* ── Sticky Navigation Sidebar ── */
.nav-sidebar {{
  position: fixed; top: 0; left: 0; width: 250px; height: 100vh;
  overflow-y: auto; background: #0f1b2d; color: #cbd5e1;
  padding: 16px 0; font-size: 9pt; z-index: 100; border-right: 2px solid #ff9900;
}}
.nav-sidebar::-webkit-scrollbar {{ width: 4px; }}
.nav-sidebar::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 2px; }}
.nav-logo {{ padding: 0 16px 14px; border-bottom: 1px solid #1e3a5f; margin-bottom: 10px; }}
.nav-logo .logo-text {{ font-size: 13pt; font-weight: 800; color: #ff9900; }}
.nav-logo .logo-sub {{ font-size: 8pt; color: #64748b; margin-top: 2px; }}
.nav-section-label {{
  font-size: 7.5pt; text-transform: uppercase; letter-spacing: 1px;
  color: #475569; font-weight: 700; padding: 10px 16px 4px;
}}
.nav-link {{
  display: flex; align-items: center; gap: 8px;
  padding: 6px 16px; color: #94a3b8; text-decoration: none;
  transition: all .15s; border-left: 3px solid transparent;
  font-size: 9pt; line-height: 1.4;
}}
.nav-link:hover {{ background: #1e293b; color: #e2e8f0; border-left-color: #334155; }}
.nav-dot {{
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}}
.count-badge {{
  margin-left: auto; background: #1e3a5f; color: #94a3b8;
  font-size: 8pt; padding: 1px 6px; border-radius: 8px; font-weight: 600;
}}
/* ── Main Content ── */
.main-content {{
  margin-left: 250px; max-width: 1200px; padding: 24px 32px 60px;
  background: #fff; min-height: 100vh;
}}
@media (max-width: 900px) {{
  .nav-sidebar {{ display: none; }}
  .main-content {{ margin-left: 0; padding: 16px; }}
}}
h1 {{
  font-size: 20pt; color: #0f1b2d;
  border-bottom: 3px solid #ff9900; padding-bottom: 8px; margin-bottom: 6px;
}}
h2.section-title {{
  font-size: 16pt; color: #0f1b2d;
  margin-top: 28px; margin-bottom: 14px;
  padding-top: 12px; padding-bottom: 4px;
  border-bottom: 2px solid #e2e8f0; scroll-margin-top: 16px;
}}
h3.sub-heading {{
  font-size: 11pt; font-weight: 700; margin-top: 16px; margin-bottom: 8px;
}}
.meta-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 10pt; }}
.meta-table td {{ padding: 4px 12px 4px 0; vertical-align: top; }}
.meta-table .label {{ color: #64748b; font-weight: 600; width: 140px; }}
.meta-table .value {{ color: #0f1b2d; font-weight: 700; }}
.mono {{ font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 9.5pt; }}
.summary-grid {{
  display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px;
}}
.summary-card {{
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 6px; padding: 12px 18px;
  min-width: 110px; flex: 1; text-align: center;
}}
.summary-card .val {{ font-size: 22pt; font-weight: 800; line-height: 1.2; }}
.summary-card .lbl {{
  font-size: 8pt; color: #64748b;
  text-transform: uppercase; letter-spacing: .5px; margin-top: 2px;
}}
.val-vpc    {{ color: #ff9900; }}
.val-subnet {{ color: #1a73e8; }}
.val-sg     {{ color: #f4511e; }}
.val-ec2    {{ color: #ff9900; }}
.val-total  {{ color: #0f1b2d; }}
.val-region {{ color: #2563eb; }}
/* Summary table */
.summary-table {{
  width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 10pt;
}}
.summary-table th {{
  background: #1e3a5f; color: #fff;
  padding: 8px 12px; text-align: left; font-weight: 600;
}}
.summary-table td {{ padding: 7px 12px; border-bottom: 1px solid #e2e8f0; }}
.summary-table tr:nth-child(even) td {{ background: #f8fafc; }}
.type-dot {{
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  margin-right: 6px; vertical-align: middle;
}}
.pillar-bar {{
  display: inline-block; height: 8px; border-radius: 4px;
  background: #e2e8f0; width: 100%; vertical-align: middle;
}}
.pillar-bar-fill {{ display: block; height: 100%; border-radius: 4px; }}
/* Resource table */
.resource-table {{
  width: 100%; border-collapse: collapse; font-size: 10pt; margin-bottom: 20px;
}}
.resource-table th {{
  background: #1e3a5f; color: #fff;
  padding: 8px 12px; text-align: left; font-weight: 600; font-size: 9pt;
}}
.resource-table td {{
  padding: 6px 12px; border-bottom: 1px solid #e2e8f0;
  font-size: 9.5pt; max-width: 260px; overflow: hidden; text-overflow: ellipsis;
}}
.resource-table tr:nth-child(even) td {{ background: #f8fafc; }}
.resource-table tr:hover td {{ background: #fff7ed; }}
/* Resource list (per VPC view) */
.resource-list {{ list-style: none; padding: 0; margin: 0 0 12px 0; }}
.resource-list li {{
  margin-bottom: 4px; padding: 5px 12px;
  background: #f8fafc; border-left: 3px solid #e2e8f0;
  border-radius: 0 4px 4px 0; font-size: 10pt; line-height: 1.5;
}}
.footer {{
  margin-top: 40px; padding-top: 12px;
  border-top: 1px solid #e2e8f0;
  font-size: 9pt; color: #94a3b8; text-align: center;
}}
</style>
</head><body>

<nav class="nav-sidebar">
<div class="nav-logo">
  <div class="logo-text">ScanBox</div>
  <div class="logo-sub">Network Topology Report</div>
</div>
<div class="nav-section-label">Overview</div>
<a class="nav-link" href="#summary">Executive Summary</a>
<a class="nav-link" href="#inventory">Resource Inventory</a>
<div class="nav-section-label" style="margin-top:8px">Resource Types ({len(ordered_types)})</div>
{nav_links}
{f'<div class="nav-section-label" style="margin-top:8px">VPCs ({len(vpcs)})</div>' + vpc_nav if vpcs else ''}
</nav>

<div class="main-content">
<h1>Network Topology Report</h1>

<table class="meta-table">
  <tr><td class="label">Profile:</td><td class="value">{_e(profile)}</td></tr>
  <tr><td class="label">Account ID:</td><td class="value mono" style="color:#c2410c">{_e(account_id)}</td></tr>
  <tr><td class="label">Scan Time:</td><td class="value">{_e(timestamp)}</td></tr>
  <tr><td class="label">Duration:</td><td class="value">{duration}s</td></tr>
  <tr><td class="label">Regions Scanned:</td><td class="value">{regions_count}</td></tr>
</table>

<h2 class="section-title" id="summary">Executive Summary</h2>
<div class="summary-grid">
  <div class="summary-card"><div class="val val-vpc">{vpc_count}</div><div class="lbl">VPCs</div></div>
  <div class="summary-card"><div class="val val-subnet">{subnet_count}</div><div class="lbl">Subnets</div></div>
  <div class="summary-card"><div class="val val-sg">{sg_count}</div><div class="lbl">Security Groups</div></div>
  <div class="summary-card"><div class="val val-ec2">{ec2_count}</div><div class="lbl">EC2 Instances</div></div>
  <div class="summary-card"><div class="val val-total">{total}</div><div class="lbl">Total Resources</div></div>
  <div class="summary-card"><div class="val val-region">{regions_count}</div><div class="lbl">Regions</div></div>
</div>

<h2 class="section-title" id="inventory">Resource Inventory</h2>
<table class="summary-table">
  <thead><tr><th>Resource Type</th><th style="text-align:right">Count</th><th>Distribution</th><th style="text-align:right">%</th></tr></thead>
  <tbody>
{summary_rows}
  </tbody>
</table>

{type_sections}

{f'<div class="page-break"></div>' if vpcs else ''}
{vpc_sections}

<div class="footer">
  Generated by AWS ScanBox Analyzer — Network Topology Module — {_e(timestamp)}
</div>
</div>

<script>
// Highlight active nav link on scroll
(function() {{
  const links = document.querySelectorAll('.nav-link');
  const sections = [];
  links.forEach(a => {{
    const id = a.getAttribute('href');
    if (id && id.startsWith('#')) {{
      const el = document.querySelector(id);
      if (el) sections.push({{ el, link: a }});
    }}
  }});
  if (!sections.length) return;
  let ticking = false;
  window.addEventListener('scroll', () => {{
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {{
      let current = sections[0];
      for (const s of sections) {{
        if (s.el.getBoundingClientRect().top <= 80) current = s;
      }}
      links.forEach(l => l.classList.remove('active'));
      if (current) current.link.classList.add('active');
      ticking = false;
    }});
  }});
}})();
</script>
</body></html>"""

    fname = f'topology_{profile}_{ts}.html'
    path = os.path.join(REPORTS_DIR, fname)
    with open(path, 'w') as f:
        f.write(html)
    return path


def generate_csv(results: dict, ts: str = None) -> str:
    profile = results.get('profile', 'unknown')
    resources = results.get('resources', [])
    ts = ts or _ts()

    fname = f'topology_{profile}_{ts}.csv'
    path = os.path.join(REPORTS_DIR, fname)

    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Type', 'ID', 'Name', 'Region', 'VPC_ID', 'CIDR', 'State', 'Details'])
        for r in sorted(resources, key=lambda x: (x.get('type', ''), x.get('region', ''))):
            writer.writerow([
                TYPE_LABELS.get(r.get('type', ''), r.get('type', '')),
                r.get('id', ''),
                r.get('name', ''),
                r.get('region', ''),
                r.get('vpc_id', '') or '',
                r.get('cidr', '') or '',
                r.get('state', '') or r.get('status', '') or '',
                str({k: v for k, v in r.items() if k not in ('type', 'id', 'name', 'region', 'vpc_id', 'cidr', 'state', 'tags')})[:200],
            ])
    return path


def generate_pdf(results: dict, ts: str = None) -> str:
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        return None

    profile = results.get('profile', 'unknown')
    meta = results.get('metadata', {})
    resources = results.get('resources', [])
    ts = ts or _ts()

    fname = f'topology_{profile}_{ts}.pdf'
    path = os.path.join(REPORTS_DIR, fname)

    doc = SimpleDocTemplate(path, pagesize=landscape(A4), topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = styles['Title']
    title_style.textColor = colors.HexColor('#ff9900')
    elements.append(Paragraph(f'Network Topology Report — {profile}', title_style))
    elements.append(Spacer(1, 12))

    info = f"""Account: {meta.get('account_id','')} | Scan: {meta.get('timestamp','')} |
Resources: {meta.get('resource_count',0)} | Regions: {meta.get('regions_scanned',0)} |
Duration: {meta.get('scan_duration_seconds',0)}s"""
    elements.append(Paragraph(info, styles['Normal']))
    elements.append(Spacer(1, 20))

    # Summary table
    type_counts = meta.get('type_counts', {})
    summary_data = [['Resource Type', 'Count']]
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        summary_data.append([TYPE_LABELS.get(t, t), str(count)])

    if len(summary_data) > 1:
        t = Table(summary_data, colWidths=[200, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2638')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#ff9900')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1e3a5f')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#0d1b2a'), colors.HexColor('#152238')]),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e2e8f0')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

    # Resources table (limited to first 500 rows for PDF)
    res_data = [['Type', 'ID', 'Name', 'Region', 'VPC']]
    for r in sorted(resources, key=lambda x: (x.get('type', ''), x.get('region', '')))[:500]:
        res_data.append([
            TYPE_LABELS.get(r.get('type', ''), r.get('type', '')),
            r.get('id', '')[:30],
            r.get('name', '')[:30],
            r.get('region', ''),
            (r.get('vpc_id', '') or '')[:20],
        ])

    if len(res_data) > 1:
        t = Table(res_data, colWidths=[100, 150, 150, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2638')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#ff9900')),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1e3a5f')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#0d1b2a'), colors.HexColor('#152238')]),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e2e8f0')),
        ]))
        elements.append(t)

    doc.build(elements)
    return path
