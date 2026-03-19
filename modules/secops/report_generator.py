"""
SecOps Module — Report Generator
Generates HTML, CSV, and PDF reports from scan results.
"""

import os
import csv
import html as html_mod
from datetime import datetime

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

SEV_COLORS = {'CRITICAL': '#dc2626', 'HIGH': '#ea580c', 'MEDIUM': '#d97706',
              'LOW': '#65a30d', 'INFO': '#0891b2'}
STATUS_COLORS = {'PASS': '#16a34a', 'FAIL': '#dc2626', 'WARNING': '#d97706',
                 'NOT_AVAILABLE': '#6b7280', 'MANUAL': '#7c3aed'}


def _ts():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def generate_html(results: dict, ts: str = None) -> str:
    _e = html_mod.escape
    profile    = _e(results.get('profile', 'unknown'))
    account_id = _e(results.get('account_id', 'unknown'))
    scan_time  = _e(results.get('scan_time', ''))
    summary    = results.get('summary', {})
    findings   = results.get('findings', [])
    score      = summary.get('score', 0)
    weighted   = summary.get('weighted_score', 0)
    sev        = summary.get('severity', {})

    # Collect unique values for filters
    all_services = sorted({f.get('service', '') for f in findings if f.get('service')})
    all_regions  = sorted({f.get('region', '') for f in findings if f.get('region')})
    all_fws      = sorted({k for f in findings for k in f.get('frameworks', {}).keys()})

    svc_options = ''.join(f'<option value="{_e(s)}">{_e(s)}</option>' for s in all_services)
    region_options = ''.join(f'<option value="{_e(r)}">{_e(r)}</option>' for r in all_regions)
    fw_options = ''.join(f'<option value="{_e(fw)}">{_e(fw)}</option>' for fw in all_fws)

    rows = ''
    for f in sorted(findings, key=lambda x: (
            ['CRITICAL','HIGH','MEDIUM','LOW','INFO'].index(x.get('severity','INFO')),
            x.get('status','') != 'FAIL')):
        sc = SEV_COLORS.get(f['severity'], '#888')
        stc = STATUS_COLORS.get(f['status'], '#888')
        fw_str = ', '.join(f.get('frameworks', {}).keys())
        rows += f"""
        <tr data-sev="{_e(f['severity'])}" data-status="{_e(f['status'])}" data-svc="{_e(f['service'])}" data-region="{_e(f.get('region',''))}" data-fw="{_e(fw_str)}">
          <td><span class="badge" style="background:{sc}">{_e(f['severity'])}</span></td>
          <td><span class="badge" style="background:{stc}">{_e(f['status'])}</span></td>
          <td class="svc-cell">{_e(f['service'])}</td>
          <td>{_e(f['title'])}</td>
          <td style="font-family:monospace;font-size:11px">{_e(f['resource_id'])}</td>
          <td>{_e(f.get('region',''))}</td>
          <td style="font-size:11px;color:#7a90a8">{_e(fw_str)}</td>
          <td style="font-size:11px">{_e(f['remediation'])}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>SecOps Report — {profile}</title>
<style>
  *{{box-sizing:border-box}}
  body{{font-family:'Inter','Segoe UI',sans-serif;background:#0d1117;color:#e2e8f0;margin:0;padding:24px}}
  h1{{color:#ff9900;margin-bottom:4px}}
  .meta{{color:#7a90a8;font-size:13px;margin-bottom:24px}}
  .cards{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:24px}}
  .card{{background:#131f2e;border:1px solid #1e2f44;border-radius:8px;padding:14px 20px;min-width:110px}}
  .card-val{{font-size:26px;font-weight:700;color:#ff9900}}
  .card-lbl{{font-size:11px;color:#7a90a8;margin-top:3px}}
  .filters{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px;padding:12px 14px;background:#131f2e;border:1px solid #1e2f44;border-radius:8px}}
  .filters label{{font-size:11px;color:#7a90a8;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
  .filters select,.filters input{{padding:5px 10px;border:1px solid #1e2f44;border-radius:5px;background:#0d1117;color:#e2e8f0;font-size:12px;outline:none}}
  .filters select:focus,.filters input:focus{{border-color:#ff9900}}
  .filters input::placeholder{{color:#4d6480}}
  .count-label{{font-size:11px;color:#7a90a8;margin-left:auto}}
  table{{width:100%;border-collapse:collapse;background:#131f2e;border-radius:8px;overflow:hidden}}
  th{{background:#1a2638;padding:10px 12px;text-align:left;font-size:11px;color:#7a90a8;text-transform:uppercase;letter-spacing:.5px;cursor:pointer;user-select:none;white-space:nowrap}}
  th:hover{{color:#ff9900}}
  td{{padding:8px 12px;border-bottom:1px solid #1e2f44;font-size:12px;vertical-align:middle}}
  tr:hover td{{background:#1a2638}}
  tr.hidden{{display:none}}
  .badge{{color:#fff;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;display:inline-block}}
  .svc-search-wrap{{position:relative;display:inline-block}}
  .svc-search-wrap input{{width:150px}}
</style></head><body>
<h1>SecOps Security Report</h1>
<div class="meta">
  Profile: <strong>{profile}</strong> &nbsp;|&nbsp;
  Account: <strong style="color:#ff9900">{account_id}</strong> &nbsp;|&nbsp;
  Scan: {scan_time} &nbsp;|&nbsp;
  Score: {score}% &nbsp;|&nbsp; Weighted: {weighted}%
</div>
<div class="cards">
  <div class="card"><div class="card-val">{score}%</div><div class="card-lbl">Overall Score</div></div>
  <div class="card"><div class="card-val" style="color:#4da6ff">{weighted}%</div><div class="card-lbl">Weighted Score</div></div>
  <div class="card"><div class="card-val" style="color:#dc2626">{sev.get('CRITICAL',0)}</div><div class="card-lbl">Critical</div></div>
  <div class="card"><div class="card-val" style="color:#ea580c">{sev.get('HIGH',0)}</div><div class="card-lbl">High</div></div>
  <div class="card"><div class="card-val" style="color:#d97706">{sev.get('MEDIUM',0)}</div><div class="card-lbl">Medium</div></div>
  <div class="card"><div class="card-val" style="color:#65a30d">{sev.get('LOW',0)}</div><div class="card-lbl">Low</div></div>
  <div class="card"><div class="card-val">{summary.get('total',0)}</div><div class="card-lbl">Total</div></div>
</div>

<!-- Filters -->
<div class="filters">
  <label>Severity</label>
  <select id="fSev" onchange="applyF()">
    <option value="">All</option>
    <option value="CRITICAL">Critical</option><option value="HIGH">High</option>
    <option value="MEDIUM">Medium</option><option value="LOW">Low</option><option value="INFO">Info</option>
  </select>

  <label>Status</label>
  <select id="fStatus" onchange="applyF()">
    <option value="">All</option>
    <option value="FAIL">Fail</option><option value="PASS">Pass</option>
    <option value="WARNING">Warning</option><option value="NOT_AVAILABLE">N/A</option><option value="MANUAL">Manual</option>
  </select>

  <label>Service</label>
  <div class="svc-search-wrap">
    <input type="text" id="fSvcSearch" placeholder="Search services…" oninput="applyF()" autocomplete="off" list="svcList">
    <datalist id="svcList">{svc_options}</datalist>
  </div>

  <label>Region</label>
  <select id="fRegion" onchange="applyF()">
    <option value="">All</option>
    {region_options}
  </select>

  <label>Framework</label>
  <select id="fFw" onchange="applyF()">
    <option value="">All</option>
    {fw_options}
  </select>

  <button onclick="clearF()" style="padding:4px 12px;border:1px solid #1e2f44;border-radius:5px;background:transparent;color:#7a90a8;cursor:pointer;font-size:11px">Clear</button>
  <span class="count-label" id="fCount">{len(findings)} findings</span>
</div>

<table id="fTable">
  <thead><tr>
    <th onclick="sortT(0)">Severity</th>
    <th onclick="sortT(1)">Status</th>
    <th onclick="sortT(2)">Service</th>
    <th onclick="sortT(3)">Finding</th>
    <th onclick="sortT(4)">Resource</th>
    <th onclick="sortT(5)">Region</th>
    <th onclick="sortT(6)">Frameworks</th>
    <th onclick="sortT(7)">Remediation</th>
  </tr></thead>
  <tbody id="fBody">
  {rows}
  </tbody>
</table>

<script>
function applyF(){{
  const sev=document.getElementById('fSev').value;
  const st=document.getElementById('fStatus').value;
  const svc=(document.getElementById('fSvcSearch').value||'').toLowerCase();
  const reg=document.getElementById('fRegion').value;
  const fw=document.getElementById('fFw').value;
  let n=0;
  document.querySelectorAll('#fBody tr').forEach(r=>{{
    let show=true;
    if(sev&&r.dataset.sev!==sev)show=false;
    if(st&&r.dataset.status!==st)show=false;
    if(svc&&!r.dataset.svc.toLowerCase().includes(svc))show=false;
    if(reg&&r.dataset.region!==reg)show=false;
    if(fw&&!r.dataset.fw.includes(fw))show=false;
    r.classList.toggle('hidden',!show);
    if(show)n++;
  }});
  document.getElementById('fCount').textContent=n+' findings';
}}
function clearF(){{
  ['fSev','fStatus','fRegion','fFw'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('fSvcSearch').value='';
  applyF();
}}
let _sc=-1,_sd=1;
function sortT(ci){{
  const tb=document.getElementById('fBody');
  const rows=[...tb.querySelectorAll('tr')];
  if(_sc===ci)_sd*=-1;else{{_sc=ci;_sd=1;}}
  const sevO={{'CRITICAL':0,'HIGH':1,'MEDIUM':2,'LOW':3,'INFO':4}};
  rows.sort((a,b)=>{{
    let va=a.cells[ci].textContent.trim(),vb=b.cells[ci].textContent.trim();
    if(ci===0)return(sevO[va]??5)-(sevO[vb]??5)*_sd||(sevO[va]??5)>(sevO[vb]??5)?_sd:-_sd;
    return va.localeCompare(vb)*_sd;
  }});
  rows.forEach(r=>tb.appendChild(r));
}}
</script>
</body></html>"""

    path = os.path.join(REPORTS_DIR, f'secops_{profile}_{ts or _ts()}.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path


def generate_csv(results: dict, ts: str = None) -> str:
    profile    = results.get('profile', 'unknown')
    account_id = results.get('account_id', 'unknown')
    scan_time  = results.get('scan_time', '')
    summary    = results.get('summary', {})
    findings   = results.get('findings', [])

    path = os.path.join(REPORTS_DIR, f'secops_{profile}_{ts or _ts()}.csv')
    with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.writer(fh)
        # Meta header rows
        writer.writerow(['# SecOps Security Report'])
        writer.writerow(['# Profile', profile])
        writer.writerow(['# Account ID', account_id])
        writer.writerow(['# Scan Time', scan_time])
        writer.writerow(['# Score', f"{summary.get('score', 0)}%",
                         'Weighted', f"{summary.get('weighted_score', 0)}%"])
        writer.writerow([])
        writer.writerow(['Severity', 'Status', 'Service', 'Title', 'Resource ID',
                         'Resource Type', 'Region', 'Frameworks', 'Remediation'])
        for f in findings:
            writer.writerow([
                f.get('severity', ''), f.get('status', ''), f.get('service', ''),
                f.get('title', ''), f.get('resource_id', ''), f.get('resource_type', ''),
                f.get('region', ''), ', '.join(f.get('frameworks', {}).keys()),
                f.get('remediation', ''),
            ])
    return path


def generate_pdf(results: dict, ts: str = None):
    try:
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        return None

    profile    = results.get('profile', 'unknown')
    account_id = results.get('account_id', 'unknown')
    scan_time  = results.get('scan_time', '')
    summary    = results.get('summary', {})
    findings   = results.get('findings', [])
    score      = summary.get('score', 0)
    weighted   = summary.get('weighted_score', 0)
    sev        = summary.get('severity', {})

    path = os.path.join(REPORTS_DIR, f'secops_{profile}_{ts or _ts()}.pdf')
    doc  = SimpleDocTemplate(path, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph(f'SecOps Security Report — {profile}', styles['Title']))
    story.append(Paragraph(
        f'Account ID: {account_id} | Scan: {scan_time} | '
        f'Score: {score}% | Weighted: {weighted}% | '
        f'Critical: {sev.get("CRITICAL",0)} | High: {sev.get("HIGH",0)} | '
        f'Medium: {sev.get("MEDIUM",0)} | Low: {sev.get("LOW",0)} | '
        f'Total: {summary.get("total",0)}',
        styles['Normal']))
    story.append(Spacer(1, 12))

    header = ['Severity', 'Status', 'Service', 'Finding', 'Region']
    rows   = [header]
    for f in findings[:500]:
        rows.append([f.get('severity',''), f.get('status',''), f.get('service',''),
                     f.get('title','')[:80], f.get('region','')])

    t = Table(rows, colWidths=[70, 70, 60, 300, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a2638')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#0d1117'), colors.HexColor('#131f2e')]),
        ('TEXTCOLOR',  (0,1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('GRID',       (0,0), (-1,-1), 0.3, colors.HexColor('#1e2f44')),
    ]))
    story.append(t)
    doc.build(story)
    return path
