"""
AWS ScanBox Dashboard — Report Generator
Exports dashboard data as HTML, CSV, or PDF.
All reports saved to the reports/ directory inside the project.
"""

import os
import csv
import html as html_mod
import json
from datetime import datetime

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


def _timestamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def _report_path(prefix, ext, ts=None):
    return os.path.join(REPORTS_DIR, f'{prefix}_{ts or _timestamp()}.{ext}')


def _safe_profile(name):
    """Sanitize profile name for use in filenames."""
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in name).strip('_') or 'default'


# ---------------------------------------------------------------------------
# HTML Report
# ---------------------------------------------------------------------------

def generate_html(profiles_data, title='AWS ScanBox Report'):
    """Generate a styled HTML report from profiles cost data."""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    path = _report_path('aws_finops', 'html')

    # Collect all months across all profiles
    all_months = sorted({
        month
        for p in profiles_data if p.get('status') == 'success'
        for month in p.get('monthly_totals', {})
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0d1117; color: #e8eaf0; margin: 40px; }}
  h1 {{ color: #ff9900; border-left: 5px solid #ff9900; padding-left: 16px; }}
  .meta {{ color: #8892a4; font-size: 13px; margin-bottom: 32px; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 40px; background: #1a2235; border-radius: 8px; overflow: hidden; }}
  th {{ background: #232f3e; color: #ff9900; padding: 12px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid #2a3244; font-size: 13px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #1f2d44; }}
  .num {{ text-align: right; font-family: monospace; }}
  .ok {{ color: #00d68f; }}
  .warn {{ color: #ffaa00; }}
  .danger {{ color: #ff3d71; }}
  .section {{ margin: 32px 0 8px; font-size: 18px; font-weight: 600; color: #ff9900; }}
  .card-row {{ display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; }}
  .card {{ background: #1a2235; border: 1px solid #2a3244; border-radius: 8px; padding: 20px 24px; min-width: 160px; }}
  .card-label {{ font-size: 11px; text-transform: uppercase; color: #8892a4; letter-spacing: 0.5px; }}
  .card-value {{ font-size: 24px; font-weight: 700; color: #e8eaf0; margin-top: 6px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">Generated: {ts} &nbsp;|&nbsp; Profiles: {len(profiles_data)}</div>
"""

    for p in profiles_data:
        if p.get('status') != 'success':
            html += f'<div class="section">{html_mod.escape(str(p["profile"]))}</div>'
            html += f'<p style="color:#ff3d71">Error: {html_mod.escape(str(p.get("error","Unknown error")))}</p>'
            continue

        html += f'<div class="section">{html_mod.escape(str(p["profile"]))}</div>'
        html += f'''<div class="card-row">
  <div class="card"><div class="card-label">This Month</div><div class="card-value">${p["current_spend"]:,.2f}</div></div>
  <div class="card"><div class="card-label">Projected</div><div class="card-value">${p["projection"]:,.2f}</div></div>
  <div class="card"><div class="card-label">Historical Usage</div><div class="card-value">${p["total_usage"]:,.2f}</div></div>
  <div class="card"><div class="card-label">Credits</div><div class="card-value" style="color:#00d68f">${p["total_credits"]:,.2f}</div></div>
</div>'''

        # Monthly totals table
        html += '<table><thead><tr><th>Month</th>'
        for month in all_months:
            html += f'<th class="num">{month}</th>'
        html += '</tr></thead><tbody>'
        html += f'<tr><td><strong>{p["profile"]}</strong></td>'
        for month in all_months:
            val = p['monthly_totals'].get(month, 0)
            html += f'<td class="num">${val:,.2f}</td>'
        html += '</tr></tbody></table>'

        # Top services
        services = p.get('service_totals', {})
        if services:
            html += '<table><thead><tr><th>Service</th><th class="num">Total Cost ($)</th></tr></thead><tbody>'
            for svc, cost in list(services.items())[:20]:
                html += f'<tr><td>{svc}</td><td class="num">${cost:,.2f}</td></tr>'
            html += '</tbody></table>'

        # Anomalies
        anomalies = p.get('anomalies', [])
        if anomalies:
            html += '<p style="color:#ffaa00"><strong>Cost Anomalies Detected:</strong></p><ul>'
            for a in anomalies:
                color = '#ff3d71' if a['severity'] == 'critical' else '#ffaa00'
                html += f'<li style="color:{color}">{a["month"]}: +{a["change_pct"]}% vs {a["prev_month"]} (${a["prev_cost"]:,.2f} → ${a["curr_cost"]:,.2f})</li>'
            html += '</ul>'

    html += '</body></html>'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    return path


# ---------------------------------------------------------------------------
# CSV Report
# ---------------------------------------------------------------------------

def generate_csv(profiles_data):
    """Generate a CSV with monthly costs per profile."""
    path = _report_path('aws_finops', 'csv')

    all_months = sorted({
        month
        for p in profiles_data if p.get('status') == 'success'
        for month in p.get('monthly_totals', {})
    })

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Profile', 'Status', 'Current Month Spend', 'Projection', 'Historical Usage', 'Credits'] + all_months)
        for p in profiles_data:
            if p.get('status') != 'success':
                writer.writerow([p['profile'], 'error', '', '', '', '', *([''] * len(all_months))])
                continue
            row = [
                p['profile'],
                'success',
                p['current_spend'],
                p['projection'],
                p['total_usage'],
                p['total_credits'],
            ] + [p['monthly_totals'].get(m, 0) for m in all_months]
            writer.writerow(row)

    # Second sheet: service breakdown (as separate CSV)
    svc_path = path.replace('.csv', '_services.csv')
    with open(svc_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Profile', 'Service', 'Total Cost'])
        for p in profiles_data:
            if p.get('status') != 'success':
                continue
            for svc, cost in p.get('service_totals', {}).items():
                writer.writerow([p['profile'], svc, cost])

    return path


# ---------------------------------------------------------------------------
# PDF Report
# ---------------------------------------------------------------------------

def generate_pdf(profiles_data, title='AWS ScanBox Report'):
    """Generate a PDF report using ReportLab (pure Python, cross-platform)."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_RIGHT, TA_LEFT
    except ImportError:
        return None

    path = _report_path('aws_finops', 'pdf')
    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                 textColor=colors.HexColor('#ff9900'), fontSize=18)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'],
                               textColor=colors.HexColor('#232f3e'), fontSize=13)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8)

    # Colours
    DARK = colors.HexColor('#232f3e')
    ORANGE = colors.HexColor('#ff9900')
    LIGHT = colors.HexColor('#f4f6f9')
    WHITE = colors.white
    GREEN = colors.HexColor('#00d68f')
    RED = colors.HexColor('#ff3d71')

    def tbl_style(col_count):
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT, WHITE]),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#cccccc')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])

    story = []
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f'Generated: {ts}', small_style))
    story.append(Spacer(1, 0.5*cm))

    all_months = sorted({
        month
        for p in profiles_data if p.get('status') == 'success'
        for month in p.get('monthly_totals', {})
    })

    # Summary table
    header = ['Profile', 'This Month ($)', 'Projected ($)', 'Historical ($)', 'Credits ($)'] + all_months[-6:]
    rows = [header]
    for p in profiles_data:
        if p.get('status') != 'success':
            rows.append([p['profile'], 'ERROR', '', '', ''] + [''] * len(all_months[-6:]))
            continue
        row = [
            p['profile'],
            f"${p['current_spend']:,.2f}",
            f"${p['projection']:,.2f}",
            f"${p['total_usage']:,.2f}",
            f"${p['total_credits']:,.2f}",
        ] + [f"${p['monthly_totals'].get(m, 0):,.2f}" for m in all_months[-6:]]
        rows.append(row)

    story.append(Paragraph('Monthly Summary', h2_style))
    t = Table(rows, repeatRows=1)
    t.setStyle(tbl_style(len(header)))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Per-profile service table (top 15)
    for p in profiles_data:
        if p.get('status') != 'success':
            continue
        services = list(p.get('service_totals', {}).items())[:15]
        if not services:
            continue
        story.append(Paragraph(f'{p["profile"]} — Top Services', h2_style))
        svc_rows = [['Service', 'Total Cost ($)']]
        for svc, cost in services:
            svc_rows.append([svc, f'${cost:,.2f}'])
        t = Table(svc_rows, repeatRows=1, colWidths=[14*cm, 4*cm])
        t.setStyle(tbl_style(2))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    doc.build(story)
    return path


# ---------------------------------------------------------------------------
# List saved reports
# ---------------------------------------------------------------------------

def list_reports(limit=100):
    """Return list of saved report files, newest first (capped at limit)."""
    if not os.path.exists(REPORTS_DIR):
        return []
    files = []
    for fn in os.listdir(REPORTS_DIR):
        if fn.startswith(('secops_', 'advice_', 'mapinventory_', 'topology_')):
            continue  # Other modules own these
        if fn.endswith(('.html', '.csv', '.pdf')):
            full = os.path.join(REPORTS_DIR, fn)
            mt = os.path.getmtime(full)
            files.append({
                'filename': fn,
                'size_kb': round(os.path.getsize(full) / 1024, 1),
                'modified': datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M'),
                'mtime': mt,
                'ext': fn.rsplit('.', 1)[-1].upper(),
            })
    return sorted(files, key=lambda x: x['mtime'], reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Per-profile report generation
# ---------------------------------------------------------------------------

def generate_profile_report(profile_data, ts=None):
    """Generate HTML+CSV+PDF for a single profile. Returns dict of filenames."""
    if not profile_data or profile_data.get('status') != 'success':
        return {}
    profile_name = profile_data.get('profile', 'unknown')
    safe = _safe_profile(profile_name)
    ts = ts or _timestamp()
    filenames = {}

    single = [profile_data]

    try:
        path = generate_html(single, title=f'AWS ScanBox — {profile_name}')
        # Rename to include profile name
        new_name = f'aws_finops_{safe}_{ts}.html'
        new_path = os.path.join(REPORTS_DIR, new_name)
        os.rename(path, new_path)
        filenames['html'] = new_name
    except Exception:
        filenames['html'] = None

    try:
        path = generate_csv(single)
        new_name = f'aws_finops_{safe}_{ts}.csv'
        new_path = os.path.join(REPORTS_DIR, new_name)
        os.rename(path, new_path)
        filenames['csv'] = new_name
        # Also rename services csv if exists
        svc_old = path.replace('.csv', '_services.csv')
        if os.path.exists(svc_old):
            svc_new = os.path.join(REPORTS_DIR, f'aws_finops_{safe}_{ts}_services.csv')
            os.rename(svc_old, svc_new)
    except Exception:
        filenames['csv'] = None

    try:
        path = generate_pdf(single, title=f'AWS ScanBox — {profile_name}')
        if path:
            new_name = f'aws_finops_{safe}_{ts}.pdf'
            new_path = os.path.join(REPORTS_DIR, new_name)
            os.rename(path, new_path)
            filenames['pdf'] = new_name
        else:
            filenames['pdf'] = None
    except Exception:
        filenames['pdf'] = None

    return filenames
