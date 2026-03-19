"""
Map Inventory — Report Generator
Produces HTML, CSV, and PDF reports from inventory scan results.
"""

import csv
import io
import os
from datetime import datetime

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


def _filename(profile, fmt, ts=None):
    if ts is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in profile)
    return os.path.join(REPORTS_DIR, f'mapinventory_{safe}_{ts}.{fmt}')


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def generate_html(results, ts=None):
    profile = results.get('profile', 'unknown')
    meta = results.get('metadata', {})
    resources = results.get('resources', [])
    path = _filename(profile, 'html', ts)

    svc_counts = meta.get('service_counts', {})
    region_counts = meta.get('region_counts', {})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Map Inventory Report — {profile}</title>
<style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #0d1520; color: #c8d6e5; margin: 0; padding: 20px; font-size: 13px; }}
  h1 {{ color: #ff9900; font-size: 22px; margin-bottom: 4px; }}
  h2 {{ color: #ff9900; font-size: 16px; margin-top: 28px; border-bottom: 1px solid #1e2f44; padding-bottom: 6px; }}
  .meta {{ color: #7a90a8; font-size: 12px; margin-bottom: 20px; }}
  .meta span {{ margin-right: 20px; }}
  .summary {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
  .card {{ background: #111927; border: 1px solid #1e2f44; border-radius: 8px; padding: 14px 18px; min-width: 140px; }}
  .card-label {{ font-size: 11px; color: #7a90a8; text-transform: uppercase; }}
  .card-value {{ font-size: 22px; font-weight: 700; color: #ff9900; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th {{ background: #1a2638; color: #7a90a8; font-size: 11px; text-transform: uppercase; padding: 8px 10px; text-align: left; border-bottom: 1px solid #1e2f44; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #1a2638; font-size: 12px; }}
  tr:hover td {{ background: #111927; }}
  .tag {{ background: #1e2f44; color: #7a90a8; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-right: 4px; }}
  .svc-section {{ margin-bottom: 24px; }}
</style>
</head>
<body>
<h1>Map Inventory Report</h1>
<div class="meta">
  <span>Profile: <strong>{profile}</strong></span>
  <span>Account: <strong>{meta.get('account_id', '—')}</strong></span>
  <span>Scan: {meta.get('timestamp', '—')}</span>
  <span>Duration: {meta.get('scan_duration_seconds', 0)}s</span>
  <span>Resources: <strong>{meta.get('resource_count', 0)}</strong></span>
</div>
<div class="summary">
  <div class="card"><div class="card-label">Total Resources</div><div class="card-value">{meta.get('resource_count', 0)}</div></div>
  <div class="card"><div class="card-label">Services</div><div class="card-value">{meta.get('services_with_resources', 0)}</div></div>
  <div class="card"><div class="card-label">Regions</div><div class="card-value">{len(region_counts)}</div></div>
</div>
"""

    # Group resources by service
    by_service = {}
    for r in resources:
        svc = r.get('service', 'unknown')
        by_service.setdefault(svc, []).append(r)

    for svc in sorted(by_service.keys()):
        items = by_service[svc]
        html += f'<div class="svc-section"><h2>{svc.upper()} ({len(items)})</h2>\n'
        html += '<table><thead><tr><th>Type</th><th>Name</th><th>ID</th><th>Region</th><th>Tags</th></tr></thead><tbody>\n'
        for r in items[:500]:  # limit per service
            tags_str = ' '.join(f'<span class="tag">{k}={v}</span>' for k, v in list(r.get('tags', {}).items())[:5])
            html += f'<tr><td>{r.get("type","")}</td><td>{r.get("name","")}</td><td>{r.get("id","")}</td><td>{r.get("region","")}</td><td>{tags_str}</td></tr>\n'
        if len(items) > 500:
            html += f'<tr><td colspan="5" style="color:#7a90a8;font-style:italic">... and {len(items)-500} more</td></tr>\n'
        html += '</tbody></table></div>\n'

    html += '</body></html>'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def generate_csv(results, ts=None):
    profile = results.get('profile', 'unknown')
    resources = results.get('resources', [])
    path = _filename(profile, 'csv', ts)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Service', 'Type', 'Name', 'ID', 'ARN', 'Region', 'Is Default', 'Tags', 'Details'])

    for r in resources:
        tags_str = '; '.join(f'{k}={v}' for k, v in r.get('tags', {}).items())
        details_str = '; '.join(f'{k}={v}' for k, v in r.get('details', {}).items() if not isinstance(v, (dict, list)))
        writer.writerow([
            r.get('service', ''),
            r.get('type', ''),
            r.get('name', ''),
            r.get('id', ''),
            r.get('arn', ''),
            r.get('region', ''),
            r.get('is_default', False),
            tags_str,
            details_str,
        ])

    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(output.getvalue())
    return path


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def generate_pdf(results, ts=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except ImportError:
        return None

    profile = results.get('profile', 'unknown')
    meta = results.get('metadata', {})
    resources = results.get('resources', [])
    path = _filename(profile, 'pdf', ts)

    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=18, textColor=colors.HexColor('#ff9900'))
    elements.append(Paragraph('Map Inventory Report', title_style))
    elements.append(Spacer(1, 4*mm))

    # Meta info
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'],
                                 fontSize=9, textColor=colors.HexColor('#7a90a8'))
    meta_text = (f"Profile: {profile} | Account: {meta.get('account_id', '—')} | "
                 f"Scan: {meta.get('timestamp', '—')} | "
                 f"Resources: {meta.get('resource_count', 0)}")
    elements.append(Paragraph(meta_text, meta_style))
    elements.append(Spacer(1, 8*mm))

    # Group by service
    by_service = {}
    for r in resources:
        svc = r.get('service', 'unknown')
        by_service.setdefault(svc, []).append(r)

    cell_style = ParagraphStyle('Cell', parent=styles['Normal'],
                                 fontSize=7, textColor=colors.HexColor('#c8d6e5'))
    header_style = ParagraphStyle('Header', parent=styles['Normal'],
                                   fontSize=7, textColor=colors.white,
                                   fontName='Helvetica-Bold')

    for svc in sorted(by_service.keys()):
        items = by_service[svc]
        svc_title = ParagraphStyle('SvcTitle', parent=styles['Heading2'],
                                    fontSize=11, textColor=colors.HexColor('#ff9900'))
        elements.append(Paragraph(f'{svc.upper()} ({len(items)})', svc_title))
        elements.append(Spacer(1, 2*mm))

        data = [[
            Paragraph('Type', header_style),
            Paragraph('Name', header_style),
            Paragraph('ID', header_style),
            Paragraph('Region', header_style),
        ]]
        for r in items[:200]:
            data.append([
                Paragraph(str(r.get('type', '')), cell_style),
                Paragraph(str(r.get('name', ''))[:60], cell_style),
                Paragraph(str(r.get('id', ''))[:60], cell_style),
                Paragraph(str(r.get('region', '')), cell_style),
            ])
        if len(items) > 200:
            data.append([Paragraph(f'... +{len(items)-200} more', cell_style), '', '', ''])

        t = Table(data, colWidths=[50*mm, 80*mm, 80*mm, 40*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2638')),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#1e2f44')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#111927')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6*mm))

    doc.build(elements)
    return path
