/* ============================================================
   SecOps Dashboard — Main JS
   Independent from FinOps module. No shared globals.
   ============================================================ */

/* global Chart, t, formatUSD, getTheme */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let _profiles         = [];
let _profileSearch    = '';
let _selectedProfile  = '';
let _lastScan         = null;
let _radarMode        = 'framework';  // 'framework' | 'service'
let _availableRegions = [];
let _selectedRegions  = [];
let _regionError      = '';

// Chart instances
let _radarChart      = null;
let _severityChart   = null;
let _serviceBarChart = null;
let _svcDonutChart   = null;
let _svcDistBarChart = null;
let _wafrPillarChart = null;
let _trendChart          = null;
let _findingTrendChart   = null;
let _complianceGapChart  = null;
let _topFailedChart      = null;
let _scanDeltaChart      = null;
let _passRateChart       = null;

// Findings state
let _allFindings      = [];
let _filteredFindings = [];
let _page             = 1;
const PAGE_SIZE       = 50;
let _sortCol          = 'severity';
let _sortDir          = 'asc';
let _searchText       = '';
let _expandedRows     = new Set();

// ---------------------------------------------------------------------------
// XSS sanitisation helper
// ---------------------------------------------------------------------------
function _escHtml(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

const ROWS_PER_COL = 10;

const SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'NOT_AVAILABLE'];
const SEV_COLORS = {
  CRITICAL: '#dc2626', HIGH: '#ea580c', MEDIUM: '#d97706',
  LOW: '#65a30d', INFO: '#0891b2', NOT_AVAILABLE: '#6b7280',
};
const STATUS_COLORS = {
  PASS: '#16a34a', FAIL: '#dc2626', WARNING: '#d97706',
  NOT_AVAILABLE: '#6b7280', MANUAL: '#7c3aed',
};
const FW_COLORS = ['#ff9900','#4da6ff','#00c87a','#b07aff','#ffd166','#ff4d6a'];

// Severity weights for weighted score calculation (mirrors backend)
const SEV_WEIGHTS = { CRITICAL: 10, HIGH: 7, MEDIUM: 4, LOW: 2, INFO: 1 };

// localStorage key for scan history
const SCAN_HISTORY_KEY = 'secops_scan_history';

// Report groups: base_key → { base, mtime, files: {html,csv,pdf} }
let _reportGroups = {};

// ---------------------------------------------------------------------------
// Chart helpers
// ---------------------------------------------------------------------------
function applyChartDefaults() {
  const dark = getTheme() !== 'light';
  Chart.defaults.color       = dark ? '#7a90a8' : '#334155';
  Chart.defaults.borderColor = dark ? '#1e2f44' : '#d0d9e8';
}

function getChartColors() {
  const dark = getTheme() !== 'light';
  return {
    grid:    dark ? '#1e2f44' : '#d0d9e8',
    text:    dark ? '#7a90a8' : '#334155',
    tooltip: dark ? '#111927' : '#ffffff',
    bg:      dark ? '#131f2e' : '#ffffff',
  };
}

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------
async function loadProfiles() {
  const container = document.getElementById('profileList');
  if (!container) return;
  try {
    const resp = await fetch('/secops/api/profiles');
    const data = await resp.json();
    _profiles = (data.profiles || []).map(p => typeof p === 'string' ? {name: p, sso: false} : p);
    renderProfiles();
    const countEl = document.getElementById('profileCount');
    if (countEl) countEl.textContent = _profiles.length;
  } catch (e) {
    container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:10px">${_escHtml(e.message)}</div>`;
  }
}

function getFilteredProfiles() {
  if (!_profileSearch) return _profiles;
  const q = _profileSearch.toLowerCase();
  return _profiles.filter(p => p.name.toLowerCase().includes(q));
}

function onSecopsProfileSearch(value) {
  _profileSearch = value || '';
  renderProfiles();
  const clearBtn = document.getElementById('secopsProfileSearchClear');
  if (clearBtn) clearBtn.style.display = _profileSearch ? 'flex' : 'none';
}

function clearSecopsProfileSearch() {
  const input = document.getElementById('secopsProfileSearchInput');
  if (input) input.value = '';
  _profileSearch = '';
  renderProfiles();
  const clearBtn = document.getElementById('secopsProfileSearchClear');
  if (clearBtn) clearBtn.style.display = 'none';
}

function renderProfiles() {
  const container = document.getElementById('profileList');
  if (!container) return;

  const filtered = getFilteredProfiles();

  if (!_profiles.length) {
    container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:10px;grid-column:1/-1">${t('profile_none_found') || 'No AWS profiles found.'}</div>`;
    return;
  }

  if (_profileSearch && !filtered.length) {
    container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:10px;grid-column:1/-1">${t('profile_no_match') || 'No matching profiles found'}</div>`;
    return;
  }

  const numCols = Math.ceil(filtered.length / ROWS_PER_COL);

  const colsHtml = Array.from({ length: numCols }, (_, ci) => {
    const rowsHtml = filtered
      .slice(ci * ROWS_PER_COL, ci * ROWS_PER_COL + ROWS_PER_COL)
      .map((p, ri) => {
        const idx      = _profiles.indexOf(p);
        const selected = p.name === _selectedProfile;
        const ssoLabel = p.sso ? '<span class="sso-badge">SSO</span>' : '';
        return `
          <div class="profile-row ${selected ? 'selected' : ''}" data-idx="${idx}">
            <div class="profile-row-check">${selected ? ICONS.check : ''}</div>
            <div class="profile-row-name" title="${_escHtml(p.name)}">${_escHtml(p.name)}</div>
            ${ssoLabel}
          </div>`;
      }).join('');
    return `<div class="profile-col">${rowsHtml}</div>`;
  }).join('');

  container.innerHTML = colsHtml;

  // Event delegation
  container.onclick = null;
  container.onclick = (e) => {
    const row = e.target.closest('.profile-row[data-idx]');
    if (!row) return;
    const p = _profiles[parseInt(row.dataset.idx, 10)];
    if (p) selectProfile(p.name);
  };
}

function selectProfile(name) {
  _selectedProfile = name;
  _selectedRegions  = [];
  hideSsoBanner();
  renderProfiles();  // re-render to apply selected state correctly
  document.getElementById('scanBtn').disabled = false;

  const lbl = document.getElementById('selectedProfileLabel');
  if (lbl) lbl.textContent = name;

  loadRegions(name);
  loadLastScan(name);
}

async function loadRegions(profile) {
  const content = document.getElementById('regionDropdownContent');
  if (content) content.innerHTML = '<span class="spinner"></span>';
  _regionError = '';
  hideSsoBanner();
  try {
    const resp = await fetch(`/secops/api/regions?profile=${encodeURIComponent(profile)}`);
    const data = await resp.json();
    if (data.status === 'ok') {
      _availableRegions = data.regions;
    } else {
      _availableRegions = [];
      _regionError = data.error || 'Failed to load regions';
      showSsoBanner(profile, _regionError);
    }
  } catch (e) {
    _availableRegions = [];
    _regionError = e.message || 'Network error';
    showSsoBanner(profile, _regionError);
  }
  renderRegionDropdown();
}

function showSsoBanner(profile, error) {
  const banner = document.getElementById('ssoBanner');
  const msg    = document.getElementById('ssoBannerMsg');
  if (!banner || !msg) return;
  const isSso = error && (error.includes('SSO') || error.includes('expired') || error.includes('sso'));
  const cmd = `aws sso login --profile ${profile}`;
  const copyLabel = t('secops_copy') || 'Copy';
  const copiedLabel = t('secops_copied') || 'Copied';
  if (isSso) {
    const ssoMsg = t('secops_sso_expired') || 'SSO session expired for';
    const ssoRun = t('secops_sso_run') || 'Run:';
    msg.innerHTML = `<span>${ssoMsg} <b>${_escHtml(profile)}</b>. ${ssoRun}</span>
      <code id="ssoCmd" style="background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.15);padding:3px 10px;border-radius:4px;font-size:11px;font-family:monospace;user-select:all;margin:0 6px">${_escHtml(cmd)}</code>
      <button onclick="copySsoCmd()" id="ssoCopyBtn" style="padding:3px 10px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:4px;color:#f5c6c6;font-size:11px;cursor:pointer;white-space:nowrap">${copyLabel}</button>`;
  } else {
    const credErr = t('secops_credential_error') || 'Credential error for';
    msg.innerHTML = `<span>${credErr} <b>${_escHtml(profile)}</b>: ${_escHtml(error)}</span>`;
  }
  banner.style.display = 'flex';
}

function copySsoCmd() {
  const cmd = document.getElementById('ssoCmd');
  const btn = document.getElementById('ssoCopyBtn');
  if (!cmd) return;
  navigator.clipboard.writeText(cmd.textContent).then(() => {
    if (btn) { btn.textContent = '✓ ' + (t('secops_copied') || 'Copied'); setTimeout(() => { btn.textContent = t('secops_copy') || 'Copy'; }, 2000); }
  }).catch(() => {
    // Fallback: select text so user can manually copy
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(cmd);
    sel.removeAllRanges();
    sel.addRange(range);
  });
}

function hideSsoBanner() {
  const banner = document.getElementById('ssoBanner');
  if (banner) banner.style.display = 'none';
}

function renderRegionDropdown() {
  const content = document.getElementById('regionDropdownContent');
  if (!content) return;
  if (!_availableRegions.length) {
    content.innerHTML = _regionError
      ? '<span style="color:#e05c5c;font-size:11px;padding:8px;display:block">⚠ Credential error — see banner above</span>'
      : '<span style="color:var(--text-muted);font-size:12px;padding:8px;display:block">No regions found</span>';
    return;
  }
  const allChecked = _selectedRegions.length === 0;
  const sortedRegions = [..._availableRegions].sort();
  let html = `
    <div style="padding:8px 10px 6px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg-card);z-index:1">
      <input type="text" id="regionSearch" placeholder="Search regions…" oninput="filterRegionDropdown(this.value)"
        onclick="event.stopPropagation()"
        style="width:100%;box-sizing:border-box;padding:5px 9px;border:1px solid var(--border);border-radius:5px;
               background:var(--bg-base);color:var(--text-primary);font-size:12px;outline:none">
    </div>
    <div id="regionList" style="display:flex;flex-direction:column">`;
  for (const r of sortedRegions) {
    const checked = !allChecked && _selectedRegions.includes(r);
    html += `<label class="region-label" data-region="${r}"
        style="display:flex;align-items:center;gap:8px;padding:6px 14px;font-size:12px;cursor:pointer;
               border-bottom:1px solid var(--border);white-space:nowrap;transition:background .1s"
        onmouseover="this.style.background='var(--bg-base)'" onmouseout="this.style.background=''">
      <input type="checkbox" class="region-cb" value="${r}" ${checked ? 'checked' : ''} onchange="onRegionChange()" style="accent-color:var(--accent);flex-shrink:0">
      <span style="color:var(--text-secondary);font-family:monospace;letter-spacing:.3px">${r}</span>
    </label>`;
  }
  html += `</div>`;
  content.innerHTML = html;
}

function filterRegionDropdown(query) {
  const q = query.toLowerCase().trim();
  document.querySelectorAll('.region-label').forEach(label => {
    const region = label.dataset.region || '';
    label.style.display = region.includes(q) ? '' : 'none';
  });
}

function toggleAllRegions(checked) {
  _selectedRegions = [];
  document.querySelectorAll('.region-cb').forEach(cb => { cb.checked = checked; });
  updateRegionLabel();
}

function onRegionChange() {
  const checked = [...document.querySelectorAll('.region-cb:checked')].map(cb => cb.value);
  const allEl = document.getElementById('regionAll');
  if (checked.length === _availableRegions.length) {
    _selectedRegions = [];
    if (allEl) allEl.checked = true;
  } else {
    _selectedRegions = checked;
    if (allEl) allEl.checked = false;
  }
  updateRegionLabel();
}

function updateRegionLabel() {
  const lbl = document.getElementById('regionPickerLabel');
  if (!lbl) return;
  if (_selectedRegions.length === 0) {
    lbl.textContent = t('secops_all_regions') || 'All Regions';
  } else {
    lbl.textContent = `${_selectedRegions.length} Region${_selectedRegions.length > 1 ? 's' : ''}`;
  }
}

function toggleRegionDropdown() {
  const dd = document.getElementById('regionDropdown');
  if (!dd) return;
  const opening = dd.style.display === 'none' || dd.style.display === '';

  if (opening && !_selectedProfile) {
    const btn = document.getElementById('regionPickerBtn');
    if (btn) {
      const orig = btn.style.borderColor;
      btn.style.borderColor = '#dc2626';
      btn.title = t('secops_select_profile_first') || 'Please select a profile first';
      // Show a small tooltip/shake then revert
      setTimeout(() => { btn.style.borderColor = orig; btn.title = ''; }, 1800);
    }
    // Show inline message under the button
    dd.style.display = 'block';
    const content = document.getElementById('regionDropdownContent');
    if (content) {
      content.innerHTML = `<div style="padding:12px 14px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:8px">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        ${t('secops_select_profile_first') || 'Please select a profile first'}
      </div>`;
    }
    setTimeout(() => { dd.style.display = 'none'; }, 2000);
    return;
  }

  // If the profile section is collapsed, open it first so the dropdown is visible
  if (opening) {
    const sec = document.getElementById('profileSection');
    if (sec && !sec.classList.contains('open')) sec.classList.add('open');
    // Clear search input when opening
    const search = document.getElementById('regionSearch');
    if (search) { search.value = ''; filterRegionDropdown(''); }
  }
  dd.style.display = opening ? 'block' : 'none';
}

// Close region dropdown on outside click
document.addEventListener('click', () => {
  const dd = document.getElementById('regionDropdown');
  if (dd) dd.style.display = 'none';
});

async function loadLastScan(profile) {
  try {
    const resp = await fetch(`/secops/api/last-scan?profile=${encodeURIComponent(profile)}`);
    const data = await resp.json();
    if (data.status === 'ok') {
      _lastScan = data;
      renderDashboard(data, true);  // true = from cache, skip saveToHistory
      const age = Math.round((data._cache_age_seconds || 0) / 60);
      showCacheBanner(`info`, `${t('secops_last_scan_age') || 'Last scan'}: ${age} ${t('secops_minutes_ago') || 'minutes ago'}. ${t('secops_click_scan') || 'Click "Start Scan" to refresh.'}`);
    }
  } catch (e) { /* no previous scan */ }
}

// ---------------------------------------------------------------------------
// Scan
// ---------------------------------------------------------------------------
async function startScan() {
  if (!_selectedProfile) return;
  const excludeDefaults = document.getElementById('excludeDefaults').checked;

  showLoading(true, t('secops_scanning') || 'Running security checks...');
  updateProgress(0, 0, '');
  document.getElementById('scanBtn').disabled = true;

  // Poll progress while scan runs
  const progressInterval = setInterval(async () => {
    try {
      const pr = await fetch(`/secops/api/scan-progress?profile=${encodeURIComponent(_selectedProfile)}`);
      const pd = await pr.json();
      if (pd.status === 'ok') {
        updateProgress(pd.percent, pd.completed, pd.service, pd.total);
      }
    } catch (_) { /* ignore polling errors */ }
  }, 800);

  try {
    const resp = await fetch('/secops/api/scan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        profile: _selectedProfile,
        exclude_defaults: excludeDefaults,
        regions: _selectedRegions.length ? _selectedRegions : null,
      }),
    });
    const data = await resp.json();

    if (data.status === 'error') {
      showCacheBanner('error', `${t('secops_scan_error') || 'Scan error'}: ${_escHtml(data.error)}`);
      return;
    }

    _lastScan = data;
    renderDashboard(data);

    const errs = Object.keys(data.errors || {});
    if (errs.length) {
      showCacheBanner('warning',
        `${t('secops_partial_scan') || 'Partial scan'}: ${_escHtml(errs.join(', '))} — ${t('secops_insufficient_perms') || 'insufficient permissions or service unavailable.'}`);
    } else {
      hideCacheBanner();
    }

    // Auto-generate reports after successful scan
    _autoGenerateReports(_selectedProfile);
  } catch (e) {
    showCacheBanner('error', _escHtml(e.message));
  } finally {
    clearInterval(progressInterval);
    showLoading(false);
    document.getElementById('scanBtn').disabled = false;
    loadCachedScans();
  }
}

// ---------------------------------------------------------------------------
// Render Dashboard
// ---------------------------------------------------------------------------
function renderDashboard(data, fromCache) {
  const summary    = data.summary    || {};
  const frameworks = data.frameworks || {};
  const services   = data.services   || {};
  const findings   = data.findings   || [];

  _allFindings = findings;
  _filteredFindings = [...findings];
  _expandedRows.clear();
  _searchText = '';
  const searchEl = document.getElementById('findingsSearch');
  if (searchEl) searchEl.value = '';

  // Profile / Account info bar
  const infoBar = document.getElementById('scanInfoBar');
  if (infoBar) {
    document.getElementById('infoProfile').textContent    = data.profile    || '—';
    document.getElementById('infoAccountId').textContent = data.account_id || '—';
    document.getElementById('infoScanTime').textContent  = data.scan_time
      ? new Date(data.scan_time).toLocaleString() : '—';
    infoBar.style.display = 'flex';
  }

  renderMetricCards(summary, data.profile, data.scan_time, data.elapsed_seconds);
  populateServiceFilter(findings);
  renderFindingsTable();

  // Show all dashboard sections
  ['radarSection','chartsRow','chartsRow2','chartsRow3','findingsSection']
    .forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'block'; });

  // Save to history ONLY for new scans (not cached loads)
  if (!fromCache) {
    saveToHistory(data);
  }

  // Charts
  applyChartDefaults();
  renderRadar(frameworks, services);
  renderSeverityChart(summary.severity || {});
  renderFwGauges(frameworks);
  renderServiceCharts(services);
  renderWafrPillarChart(frameworks.WAFR || {});
  renderTrendChart(data.profile);
  renderFindingTrendChart(data.profile);
  renderTopFailedChart(findings);
  renderRiskTreemap(findings);
  renderPassRateChart(services);
  renderHeatMap(findings);
  renderRemediationProgress(findings);
}

// ---------------------------------------------------------------------------
// Metric Cards
// ---------------------------------------------------------------------------
function renderMetricCards(summary, profile, scanTime, elapsed) {
  const score         = summary.score          || 0;
  const weightedScore = summary.weighted_score || 0;
  const coverageScore = summary.coverage_score != null ? summary.coverage_score : 100;
  const sev           = summary.severity       || {};
  const naCount       = summary.not_available  || 0;
  const scoreColor    = score >= 80 ? '#16a34a' : score >= 60 ? '#d97706' : '#dc2626';
  const wScoreColor   = weightedScore >= 80 ? '#16a34a' : weightedScore >= 60 ? '#d97706' : '#dc2626';
  const covColor      = coverageScore >= 80 ? '#16a34a' : coverageScore >= 60 ? '#d97706' : '#dc2626';

  const shieldSvg  = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`;
  const scaleSvg   = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`;
  const clockSvg   = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
  const coverSvg   = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`;

  // Trend velocity: compare with previous scan
  let trendHtml = '';
  const history = loadScanHistory(profile);
  if (history.length >= 2) {
    const prevScore = history[history.length - 2].score || 0;
    const diff = Math.round(score - prevScore);
    if (diff > 0) trendHtml = `<div style="font-size:10px;color:#16a34a;margin-top:2px">▲ +${diff}% ${t('secops_trend_up')}</div>`;
    else if (diff < 0) trendHtml = `<div style="font-size:10px;color:#dc2626;margin-top:2px">▼ ${diff}% ${t('secops_trend_down')}</div>`;
    else trendHtml = `<div style="font-size:10px;color:var(--text-muted);margin-top:2px">● ${t('secops_trend_stable')}</div>`;
  }

  // Severity impact breakdown for weighted score
  const critFail = (summary._sev_fail || {}).__computed || '';
  const sevBreak = [];
  if (sev.CRITICAL > 0) sevBreak.push(`${sev.CRITICAL} CRIT`);
  if (sev.HIGH > 0)     sevBreak.push(`${sev.HIGH} HIGH`);
  if (sev.MEDIUM > 0)   sevBreak.push(`${sev.MEDIUM} MED`);
  const sevBreakStr = sevBreak.length ? sevBreak.join(' · ') : '';

  const cards = [
    { icon: shieldSvg, val: `${score}%`,          label: t('secops_score')     || 'Security Score',    color: scoreColor,  extra: trendHtml },
    { icon: scaleSvg,  val: `${weightedScore}%`,   label: 'Weighted Score',                             color: wScoreColor,
      sub: t('secops_weighted_sub') || 'Severity-adjusted',
      extra: sevBreakStr ? `<div style="font-size:9px;color:var(--text-muted);margin-top:2px">${sevBreakStr}</div>` : '' },
    { icon: coverSvg,  val: `${coverageScore}%`,   label: t('secops_coverage')  || 'Coverage',          color: covColor,
      sub: t('secops_coverage_sub') || 'Checked active services' },
    { icon: ICONS.alertCircle,  val: sev.CRITICAL || 0, label: t('secops_critical') || 'Critical',     color: '#dc2626' },
    { icon: ICONS.alertTriangle,val: sev.HIGH     || 0, label: t('secops_high')     || 'High',         color: '#ea580c' },
    { icon: ICONS.warning,      val: sev.MEDIUM   || 0, label: t('secops_medium')   || 'Medium',       color: '#d97706' },
    { icon: ICONS.checkCircle,  val: summary.passed || 0, label: t('secops_passed') || 'Passed',       color: '#16a34a' },
    { icon: ICONS.x,            val: summary.failed || 0, label: t('secops_failed') || 'Failed',       color: '#dc2626' },
    { icon: clockSvg,  val: `${elapsed}s`,         label: t('secops_scan_time') || 'Scan Time',        color: 'var(--text-secondary)' },
  ];

  document.getElementById('metricCards').innerHTML = cards.map(c => `
    <div class="metric-card">
      <div class="metric-body">
        <div class="metric-icon" style="color:${c.color};margin-bottom:6px">${c.icon}</div>
        <div>
          <div class="metric-value" style="color:${c.color};font-size:26px;font-weight:700">${c.val}</div>
          <div class="metric-label">${c.label}</div>
          ${c.sub ? `<div style="font-size:10px;color:var(--text-muted);margin-top:2px">${c.sub}</div>` : ''}
          ${c.extra || ''}
        </div>
      </div>
    </div>`).join('');

  // NOT_AVAILABLE banner — warn about skipped checks
  const naBanner = document.getElementById('naBanner');
  if (naBanner) {
    if (naCount > 0) {
      naBanner.style.display = 'flex';
      naBanner.innerHTML = `<div style="display:flex;align-items:center;gap:8px;padding:10px 16px;background:rgba(107,114,128,0.1);border:1px solid rgba(107,114,128,0.3);border-radius:8px;font-size:12px;color:var(--text-secondary)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span><strong>${naCount}</strong> ${t('secops_na_banner') || 'checks skipped due to insufficient permissions'}</span>
      </div>`;
    } else {
      naBanner.style.display = 'none';
    }
  }
}

// ---------------------------------------------------------------------------
// Radar Chart
// ---------------------------------------------------------------------------
function renderRadar(frameworks, services) {
  if (_radarMode === 'framework') {
    const keys    = Object.keys(frameworks);
    const labels  = keys.map(k => frameworks[k].label || k);
    const scores  = keys.map(k => frameworks[k].score || 0);
    _drawRadar(labels, scores, t('secops_fw_score') || 'Compliance Score %');
  } else {
    const svcKeys  = Object.keys(services).filter(s => services[s].total > 0);
    const labels   = svcKeys;
    const scores   = svcKeys.map(s => services[s].score || 0);
    _drawRadar(labels, scores, t('secops_svc_score') || 'Service Score %');
  }
}

function _splitLabel(text) {
  if (text.length <= 14) return text;
  const words = text.split(' ');
  if (words.length <= 1) return text;
  const mid = Math.ceil(words.length / 2);
  return [words.slice(0, mid).join(' '), words.slice(mid).join(' ')];
}

function _drawRadar(labels, data, label) {
  const ctx = document.getElementById('radarChart');
  if (!ctx) return;
  const cc = getChartColors();
  const threshold = labels.map(() => 70); // 70% acceptance threshold
  const splitLabels = labels.map(l => _splitLabel(l));

  if (_radarChart) _radarChart.destroy();
  _radarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: splitLabels,
      datasets: [
        {
          label,
          data,
          backgroundColor: 'rgba(255,153,0,0.18)',
          borderColor: '#ff9900',
          pointBackgroundColor: '#ff9900',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: '#ff9900',
          borderWidth: 2.5,
          pointRadius: 5,
        },
        {
          label: 'Target (70%)',
          data: threshold,
          backgroundColor: 'rgba(22,163,74,0.05)',
          borderColor: 'rgba(22,163,74,0.5)',
          borderDash: [4, 4],
          borderWidth: 1.5,
          pointRadius: 0,
          pointHoverRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { stepSize: 20, color: cc.text, backdropColor: 'transparent', font: { size: 11 } },
          grid:  { color: cc.grid },
          pointLabels: { color: cc.text, font: { size: 13, weight: '600' } },
          angleLines: { color: cc.grid },
        },
      },
      plugins: {
        legend: { labels: { color: cc.text, font: { size: 12 }, filter: item => item.datasetIndex === 0 } },
        tooltip: {
          filter: item => item.datasetIndex === 0,
          callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.raw}%` },
        },
      },
    },
  });
}

function switchRadarTab(mode) {
  _radarMode = mode;
  document.getElementById('radarTabFw').classList.toggle('active', mode === 'framework');
  document.getElementById('radarTabSvc').classList.toggle('active', mode === 'service');
  // Also update modal tabs if open
  document.getElementById('radarModalTabFw')?.classList.toggle('active', mode === 'framework');
  document.getElementById('radarModalTabSvc')?.classList.toggle('active', mode === 'service');
  if (_lastScan) renderRadar(_lastScan.frameworks || {}, _lastScan.services || {});
  if (_radarModalChart && _lastScan) _renderRadarModal();
}

// ---------------------------------------------------------------------------
// Radar Expand Modal
// ---------------------------------------------------------------------------
let _radarModalChart = null;

function toggleRadarExpand() {
  // Check if modal already exists
  let overlay = document.getElementById('radarModalOverlay');
  if (overlay) { closeRadarModal(); return; }

  overlay = document.createElement('div');
  overlay.id = 'radarModalOverlay';
  overlay.className = 'chart-modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) closeRadarModal(); };

  overlay.innerHTML = `
    <div class="chart-modal">
      <div class="chart-modal-header">
        <div class="chart-title">Capability Radar</div>
        <div style="display:flex;align-items:center;gap:8px">
          <button class="period-btn ${_radarMode === 'framework' ? 'active' : ''}" id="radarModalTabFw" onclick="switchRadarTab('framework')">Framework</button>
          <button class="period-btn ${_radarMode === 'service' ? 'active' : ''}" id="radarModalTabSvc" onclick="switchRadarTab('service')">Service</button>
          <button class="chart-modal-close" onclick="closeRadarModal()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>
      <div class="chart-modal-body">
        <canvas id="radarModalCanvas"></canvas>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  // ESC to close
  overlay._escHandler = (e) => { if (e.key === 'Escape') closeRadarModal(); };
  document.addEventListener('keydown', overlay._escHandler);

  _renderRadarModal();
}

function _renderRadarModal() {
  const canvas = document.getElementById('radarModalCanvas');
  if (!canvas || !_lastScan) return;
  applyChartDefaults();
  const cc = getChartColors();

  let labels, data;
  if (_radarMode === 'framework') {
    const fw = _lastScan.frameworks || {};
    labels = Object.keys(fw);
    data = labels.map(k => fw[k]?.score ?? 0);
  } else {
    const svc = _lastScan.services || {};
    labels = Object.keys(svc).filter(k => svc[k].total > 0);
    data = labels.map(k => svc[k]?.score ?? 0);
  }

  if (_radarModalChart) _radarModalChart.destroy();
  _radarModalChart = new Chart(canvas, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: _radarMode === 'framework' ? 'Compliance Score %' : 'Service Score %',
        data,
        borderColor: '#ff9900',
        backgroundColor: 'rgba(255,153,0,0.15)',
        pointBackgroundColor: '#ff9900',
        pointRadius: 5,
        pointHoverRadius: 7,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { stepSize: 20, color: cc.text, backdropColor: 'transparent', font: { size: 12 } },
          grid: { color: cc.grid },
          angleLines: { color: cc.grid },
          pointLabels: { color: cc.text, font: { size: 13, weight: '500' } },
        },
      },
      plugins: {
        legend: { display: true, position: 'top', labels: { color: cc.text, font: { size: 13 } } },
        tooltip: {
          backgroundColor: cc.tooltip,
          borderColor: cc.border,
          borderWidth: 1,
          titleColor: cc.title,
          bodyColor: cc.text,
          bodyFont: { size: 13 },
          callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}%` },
        },
      },
    },
  });
}

function closeRadarModal() {
  const overlay = document.getElementById('radarModalOverlay');
  if (!overlay) return;
  if (overlay._escHandler) document.removeEventListener('keydown', overlay._escHandler);
  if (_radarModalChart) { _radarModalChart.destroy(); _radarModalChart = null; }
  overlay.remove();
}

// ---------------------------------------------------------------------------
// Severity Chart — removed (data already shown in metric cards)
// ---------------------------------------------------------------------------
function renderSeverityChart(sev) {
  // Severity bar chart removed — severity counts are displayed in the metric cards.
  // Hide the container if it exists.
  const ctx = document.getElementById('severityChart');
  if (ctx) {
    const wrap = ctx.closest('.chart-card');
    if (wrap) wrap.style.display = 'none';
  }
  if (_severityChart) { _severityChart.destroy(); _severityChart = null; }
}

// ---------------------------------------------------------------------------
// Framework Gauges (SVG ring per framework)
// ---------------------------------------------------------------------------
function renderFwGauges(frameworks) {
  const container = document.getElementById('fwGaugesContainer');
  if (!container) return;

  const R = 36;          // circle radius
  const C = 2 * Math.PI * R; // circumference ≈ 226.19

  container.innerHTML = Object.entries(frameworks).map(([key, fw]) => {
    const score  = fw.score  || 0;
    const pass   = fw.pass   || 0;
    const total  = fw.total  || 0;
    const color  = score >= 80 ? '#16a34a' : score >= 60 ? '#d97706' : '#dc2626';
    const bg     = getTheme() === 'light' ? '#d0d9e8' : '#1e2f44';
    const dash   = (score / 100) * C;
    const label  = key === 'ISO27001' ? 'ISO 27001' : key;
    const sublabel = key === 'WAFR' ? 'Well-Architected' :
                     key === 'CIS'  ? 'CIS Benchmark v3' :
                     key === 'HIPAA'? 'HIPAA Security'   : 'ISO/IEC 27001';
    return `
      <div style="display:flex;flex-direction:column;align-items:center;padding:8px 4px;cursor:pointer"
           onclick="filterByFramework('${key}')" title="Click to filter findings by ${label}">
        <svg viewBox="0 0 100 100" width="88" height="88" style="overflow:visible">
          <circle cx="50" cy="50" r="${R}" fill="none" stroke="${bg}" stroke-width="10"/>
          <circle cx="50" cy="50" r="${R}" fill="none" stroke="${color}" stroke-width="10"
            stroke-dasharray="${dash.toFixed(2)} ${C.toFixed(2)}"
            transform="rotate(-90 50 50)" stroke-linecap="round"/>
          <text x="50" y="44" text-anchor="middle" fill="${color}" font-size="15" font-weight="700" dy="0.35em">${score}%</text>
          <text x="50" y="62" text-anchor="middle" fill="var(--text-muted)" font-size="8">${pass}/${total}</text>
        </svg>
        <div style="font-size:11px;font-weight:700;color:var(--text-primary);margin-top:2px;text-align:center">${label}</div>
        <div style="font-size:9px;color:var(--text-muted);text-align:center">${sublabel}</div>
      </div>`;
  }).join('');
}

function filterByFramework(key) {
  selectCfd('cfdFw', key, key);
  document.getElementById('findingsSection')?.scrollIntoView({ behavior: 'smooth' });
}

// ---------------------------------------------------------------------------
// Service Charts
// ---------------------------------------------------------------------------
// Saved service data for re-render on legend toggle
let _svcChartData = null;

function renderServiceCharts(services) {
  _svcChartData = services;
  const keys    = Object.keys(services).filter(k => services[k].total > 0);
  const cc      = getChartColors();

  _svcHiddenDatasets.clear();
  _renderServiceBar(keys, services, cc, _svcHiddenDatasets);

  // Donut — fail distribution across services (with % labels)
  const failKeys   = keys.filter(k => (services[k].fail || 0) > 0);
  const failCounts = failKeys.map(k => services[k].fail || 0);
  const failTotal  = failCounts.reduce((a, b) => a + b, 0);

  const ctxDonut = document.getElementById('serviceDonutChart');
  if (ctxDonut) {
    if (_svcDonutChart) _svcDonutChart.destroy();
    if (failKeys.length) {
      _svcDonutChart = new Chart(ctxDonut, {
        type: 'doughnut',
        data: {
          labels: failKeys,
          datasets: [{ data: failCounts, backgroundColor: FW_COLORS, borderWidth: 2, borderColor: cc.bg }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '60%',
          plugins: {
            legend: { position: 'right', labels: { color: cc.text, font: { size: 10 } } },
            tooltip: {
              callbacks: {
                label: c => {
                  const pct = failTotal > 0 ? Math.round(c.raw / failTotal * 100) : 0;
                  return ` ${c.label}: ${c.raw} fails (${pct}%)`;
                },
              },
            },
            // Percentage labels on segments
            datalabels: undefined, // not using plugin — use custom afterDraw
          },
          onClick(evt, elements) {
            if (!elements.length) return;
            const svc = failKeys[elements[0].index];
            selectCfd('cfdSvc', svc, svc);
            document.getElementById('findingsSection')?.scrollIntoView({ behavior: 'smooth' });
          },
        },
        plugins: [{
          id: 'donutPercentLabels',
          afterDraw(chart) {
            const { ctx } = chart;
            chart.data.datasets[0].data.forEach((val, i) => {
              const pct = failTotal > 0 ? Math.round(val / failTotal * 100) : 0;
              if (pct < 5) return; // skip tiny segments
              const meta = chart.getDatasetMeta(0).data[i];
              const { x, y } = meta.tooltipPosition();
              ctx.save();
              ctx.fillStyle = '#fff';
              ctx.font = 'bold 10px Inter, sans-serif';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText(`${pct}%`, x, y);
              ctx.restore();
            });
          },
        }],
      });
    }
  }

  // Bar alternative — same data as donut but horizontal bar
  _renderSvcDistBar(failKeys, failCounts, failTotal, cc);
}


// Service Distribution — bar alternative view
function _renderSvcDistBar(failKeys, failCounts, failTotal, cc) {
  const ctxBar = document.getElementById('serviceDistBarChart');
  if (!ctxBar || !failKeys.length) return;

  if (_svcDistBarChart) _svcDistBarChart.destroy();
  _svcDistBarChart = new Chart(ctxBar, {
    type: 'bar',
    data: {
      labels: failKeys,
      datasets: [{
        data: failCounts,
        backgroundColor: FW_COLORS.slice(0, failKeys.length),
        borderRadius: 3,
        barPercentage: 0.65,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => {
              const pct = failTotal > 0 ? Math.round(item.raw / failTotal * 100) : 0;
              return ` ${item.raw} fails (${pct}%)`;
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { color: cc.text, font: { size: 9 }, precision: 0 },
          grid: { color: cc.grid },
        },
        y: {
          ticks: { color: cc.text, font: { size: 10 } },
          grid: { display: false },
        },
      },
      onClick(evt, elements) {
        if (!elements.length) return;
        const svc = failKeys[elements[0].index];
        selectCfd('cfdSvc', svc, svc);
        document.getElementById('findingsSection')?.scrollIntoView({ behavior: 'smooth' });
      },
    },
  });
}


// Tab switch for Service Distribution (donut ↔ bar)
function switchSvcDistTab(mode) {
  const donutWrap = document.getElementById('svcDistDonutWrap');
  const barWrap   = document.getElementById('svcDistBarWrap');
  const btnDonut  = document.getElementById('svcDistTabDonut');
  const btnBar    = document.getElementById('svcDistTabBar');
  if (!donutWrap || !barWrap) return;

  if (mode === 'bar') {
    donutWrap.style.display = 'none';
    barWrap.style.display   = 'block';
    if (btnDonut) { btnDonut.style.background = 'var(--bg-input)'; btnDonut.style.color = 'var(--text-secondary)'; }
    if (btnBar)   { btnBar.style.background = 'var(--accent)'; btnBar.style.color = '#fff'; }
  } else {
    donutWrap.style.display = 'block';
    barWrap.style.display   = 'none';
    if (btnDonut) { btnDonut.style.background = 'var(--accent)'; btnDonut.style.color = '#fff'; }
    if (btnBar)   { btnBar.style.background = 'var(--bg-input)'; btnBar.style.color = 'var(--text-secondary)'; }
  }
}

// Track which legend items are hidden
let _svcHiddenDatasets = new Set();

function _renderServiceBar(allKeys, services, cc, hiddenSet) {
  const ctxBar = document.getElementById('serviceBarChart');
  if (!ctxBar) return;

  // Build raw data per key
  const rawData = allKeys.map(k => ({
    key: k,
    pass: services[k].pass || 0,
    warn: services[k].warning || 0,
    fail: services[k].fail || 0,
    na:   (services[k].not_available || 0) + (services[k].manual || 0),
  }));

  // Filter out services that have zero visible bars (all visible datasets are 0)
  const keys = rawData.filter(d => {
    let hasVisible = false;
    if (!hiddenSet.has('Pass')    && d.pass > 0) hasVisible = true;
    if (!hiddenSet.has('Warning') && d.warn > 0) hasVisible = true;
    if (!hiddenSet.has('Fail')    && d.fail > 0) hasVisible = true;
    if (!hiddenSet.has('N/A')     && d.na   > 0) hasVisible = true;
    return hasVisible;
  }).map(d => d.key);

  const passData = keys.map(k => services[k].pass || 0);
  const warnData = keys.map(k => services[k].warning || 0);
  const failData = keys.map(k => services[k].fail || 0);
  const naData   = keys.map(k => (services[k].not_available || 0) + (services[k].manual || 0));

  // Dynamic height based on visible services
  const barHeight = Math.max(120, keys.length * 24 + 50);
  const wrap = ctxBar.parentElement;
  if (wrap) wrap.style.height = barHeight + 'px';
  ctxBar.style.height = barHeight + 'px';

  if (_serviceBarChart) _serviceBarChart.destroy();

  const datasets = [
    { label: 'Pass',    data: passData, backgroundColor: '#16a34a', borderRadius: 2, hidden: hiddenSet.has('Pass') },
    { label: 'Warning', data: warnData, backgroundColor: '#d97706', borderRadius: 2, hidden: hiddenSet.has('Warning') },
    { label: 'Fail',    data: failData, backgroundColor: '#dc2626', borderRadius: 2, hidden: hiddenSet.has('Fail') },
    { label: 'N/A',     data: naData,   backgroundColor: '#4b5563', borderRadius: 2, hidden: hiddenSet.has('N/A') },
  ];

  _serviceBarChart = new Chart(ctxBar, {
    type: 'bar',
    data: { labels: keys, datasets },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: cc.text, font: { size: 10 }, boxWidth: 10, padding: 8 },
          onClick: (evt, legendItem, legend) => {
            const dsLabel = legendItem.text;
            if (_svcHiddenDatasets.has(dsLabel)) {
              _svcHiddenDatasets.delete(dsLabel);
            } else {
              _svcHiddenDatasets.add(dsLabel);
            }
            // Re-render with filtered services
            const allSvcKeys = Object.keys(_svcChartData).filter(k => _svcChartData[k].total > 0);
            _renderServiceBar(allSvcKeys, _svcChartData, getChartColors(), _svcHiddenDatasets);
          },
        },
        tooltip: {
          mode: 'index',
          callbacks: {
            footer: items => {
              const pass = items.find(i => i.dataset.label === 'Pass')?.raw || 0;
              const fail = items.find(i => i.dataset.label === 'Fail')?.raw || 0;
              const warn = items.find(i => i.dataset.label === 'Warning')?.raw || 0;
              const actionable = pass + fail + warn;
              return `Score: ${actionable ? Math.round(pass / actionable * 100) : 0}%`;
            },
          },
        },
      },
      scales: {
        x: { stacked: true, grid: { color: cc.grid }, ticks: { color: cc.text, font: { size: 10 } } },
        y: { stacked: true, grid: { display: false }, ticks: { color: cc.text, font: { size: 11 } } },
      },
      onClick(evt, elements) {
        if (!elements.length) return;
        const svc = keys[elements[0].index];
        selectCfd('cfdSvc', svc, svc);
        document.getElementById('findingsSection')?.scrollIntoView({ behavior: 'smooth' });
      },
    },
  });
}

// (donut rendering is integrated into renderServiceCharts above)

// ---------------------------------------------------------------------------
// WAFR Pillar Chart — click to drill down into findings
// ---------------------------------------------------------------------------
function renderWafrPillarChart(wafr) {
  const ctx = document.getElementById('wafrPillarChart');
  if (!ctx) return;
  const pillars = wafr.pillars || {};
  const labels  = Object.keys(pillars);
  const scores  = labels.map(p => pillars[p].score || 0);
  const totals  = labels.map(p => pillars[p].total || 0);
  const colors  = scores.map(s => s >= 80 ? '#16a34a' : s >= 60 ? '#d97706' : '#dc2626');
  const cc      = getChartColors();

  if (_wafrPillarChart) _wafrPillarChart.destroy();
  _wafrPillarChart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ data: scores, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: c => ` ${c.raw}% (${pillars[labels[c.dataIndex]]?.pass||0}/${totals[c.dataIndex]} passed)`,
            afterLabel: () => 'Click to filter findings',
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: cc.text, font: { size: 10 } } },
        y: { min: 0, max: 100, grid: { color: cc.grid }, ticks: { color: cc.text, callback: v => v + '%' } },
      },
      onClick(evt, elements) {
        if (!elements.length) return;
        const pillar = labels[elements[0].index];
        filterByWAFRPillar(pillar);
      },
    },
  });
}

function filterByWAFRPillar(pillar) {
  _filteredFindings = _allFindings.filter(f => f.frameworks?.WAFR?.pillar === pillar);
  _page = 1;
  renderFindingsTable();
  document.getElementById('findingsSection')?.scrollIntoView({ behavior: 'smooth' });
  showCacheBanner('info', `WAFR Pillar: ${pillar} — ${_filteredFindings.length} findings. Click "Clear" to reset.`);
}

function filterByServiceRegion(svc, region) {
  _filteredFindings = _allFindings.filter(f => f.service === svc && f.region === region);
  _page = 1;
  renderFindingsTable();
  document.getElementById('findingsSection')?.scrollIntoView({ behavior: 'smooth' });
  showCacheBanner('info', `${svc} / ${region} — ${_filteredFindings.length} findings. Click "Clear" to reset.`);
}

// ---------------------------------------------------------------------------
// Scan History (localStorage)
// ---------------------------------------------------------------------------
function saveToHistory(data) {
  if (!data.profile || !data.scan_time) return;
  const key = `${SCAN_HISTORY_KEY}_${data.profile}`;
  let history = [];
  try { history = JSON.parse(localStorage.getItem(key) || '[]'); } catch (e) {}

  // Prevent duplicate entries for the same scan_time
  if (history.some(h => h.date === data.scan_time)) return;

  history.push({
    date:            data.scan_time,
    score:           data.summary?.score          || 0,
    weighted_score:  data.summary?.weighted_score || 0,
    coverage_score:  data.summary?.coverage_score || 0,
    critical:        data.summary?.severity?.CRITICAL || 0,
    high:            data.summary?.severity?.HIGH     || 0,
    medium:          data.summary?.severity?.MEDIUM   || 0,
    low:             data.summary?.severity?.LOW      || 0,
    info:            data.summary?.severity?.INFO     || 0,
    passed:          data.summary?.passed   || 0,
    failed:          data.summary?.failed   || 0,
    warnings:        data.summary?.warnings || 0,
    total:           data.summary?.total    || 0,
  });
  if (history.length > 20) history = history.slice(-20);
  try { localStorage.setItem(key, JSON.stringify(history)); } catch (e) {}
}

function loadScanHistory(profile) {
  try {
    return JSON.parse(localStorage.getItem(`${SCAN_HISTORY_KEY}_${profile}`) || '[]');
  } catch (e) { return []; }
}

// ---------------------------------------------------------------------------
// Trend Chart
// ---------------------------------------------------------------------------
function renderTrendChart(profile) {
  const wrap = document.getElementById('trendChartWrap');
  const ctx  = document.getElementById('trendChart');
  if (!ctx || !wrap) return;

  const history = loadScanHistory(profile);
  if (history.length < 2) {
    wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:200px;font-size:12px;color:var(--text-muted);text-align:center;padding:20px">Run 2+ scans<br>to see trend</div>`;
    return;
  }

  // Re-add canvas if it was replaced
  if (!document.getElementById('trendChart')) {
    const c = document.createElement('canvas');
    c.id = 'trendChart';
    wrap.innerHTML = '';
    wrap.appendChild(c);
  }
  const canv = document.getElementById('trendChart');
  const cc = getChartColors();
  const labels  = history.map(h => new Date(h.date).toLocaleDateString(undefined, { month:'short', day:'numeric' }));
  const scores  = history.map(h => h.score || 0);
  const wScores = history.map(h => h.weighted_score || 0);

  if (_trendChart) _trendChart.destroy();
  _trendChart = new Chart(canv, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Score %',
          data: scores,
          borderColor: '#ff9900',
          backgroundColor: 'rgba(255,153,0,0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#ff9900',
        },
        {
          label: 'Weighted %',
          data: wScores,
          borderColor: '#4da6ff',
          backgroundColor: 'transparent',
          borderDash: [5, 3],
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: '#4da6ff',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: cc.text, font: { size: 10 }, boxWidth: 10 } },
        tooltip: {
          mode: 'index', intersect: false,
          callbacks: {
            afterBody: (items) => {
              if (!items.length || items[0].dataIndex === 0) return '';
              const cur = items[0].raw;
              const prev = items[0].dataset.data[items[0].dataIndex - 1];
              const diff = cur - prev;
              if (diff === 0) return '  Change: —';
              return `  Change: ${diff > 0 ? '+' : ''}${diff.toFixed(1)}%`;
            },
          },
        },
      },
      scales: {
        x: { ticks: { color: cc.text, font: { size: 9 } }, grid: { color: cc.grid } },
        y: { min: 0, max: 100, ticks: { color: cc.text, callback: v => v + '%', font: { size: 9 } }, grid: { color: cc.grid } },
      },
    },
  });
}


// ---------------------------------------------------------------------------
// Finding Trend Chart (severity breakdown over scans)
// ---------------------------------------------------------------------------
function renderFindingTrendChart(profile) {
  const wrap = document.getElementById('findingTrendWrap');
  const ctx  = document.getElementById('findingTrendChart');
  if (!ctx || !wrap) return;

  const history = loadScanHistory(profile);
  if (history.length < 2) {
    wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:200px;font-size:12px;color:var(--text-muted);text-align:center;padding:20px">${t('secops_finding_trend_empty') || 'Run 2+ scans to see finding trend'}</div>`;
    return;
  }

  // Re-add canvas if it was replaced by the empty placeholder
  if (!document.getElementById('findingTrendChart')) {
    const c = document.createElement('canvas');
    c.id = 'findingTrendChart';
    wrap.innerHTML = '';
    wrap.appendChild(c);
  }
  const canv = document.getElementById('findingTrendChart');
  const cc = getChartColors();
  const labels = history.map(h => new Date(h.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));

  const criticals = history.map(h => h.critical || 0);
  const highs     = history.map(h => h.high     || 0);
  const mediums   = history.map(h => h.medium   || 0);
  const lows      = history.map(h => h.low      || 0);
  const infos     = history.map(h => h.info     || 0);

  if (_findingTrendChart) _findingTrendChart.destroy();
  _findingTrendChart = new Chart(canv, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Critical',
          data: criticals,
          backgroundColor: '#dc2626',
          borderRadius: 2,
          barPercentage: 0.7,
        },
        {
          label: 'High',
          data: highs,
          backgroundColor: '#f97316',
          borderRadius: 2,
          barPercentage: 0.7,
        },
        {
          label: 'Medium',
          data: mediums,
          backgroundColor: '#eab308',
          borderRadius: 2,
          barPercentage: 0.7,
        },
        {
          label: 'Low',
          data: lows,
          backgroundColor: '#3b82f6',
          borderRadius: 2,
          barPercentage: 0.7,
        },
        {
          label: 'Info',
          data: infos,
          backgroundColor: '#6b7280',
          borderRadius: 2,
          barPercentage: 0.7,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: cc.text, font: { size: 9 }, boxWidth: 10, padding: 8 },
          position: 'bottom',
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            footer: (items) => {
              const total = items.reduce((s, i) => s + (i.raw || 0), 0);
              return `Total: ${total}`;
            },
            afterFooter: (items) => {
              if (!items.length) return '';
              const idx = items[0].dataIndex;
              if (idx === 0) return '';
              const curTotal  = items.reduce((s, i) => s + (i.raw || 0), 0);
              // Compute previous total
              const chart = items[0].chart;
              let prevTotal = 0;
              chart.data.datasets.forEach(ds => { prevTotal += ds.data[idx - 1] || 0; });
              const diff = curTotal - prevTotal;
              if (diff === 0) return 'Change: —';
              return `Change: ${diff > 0 ? '+' : ''}${diff}`;
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          ticks: { color: cc.text, font: { size: 9 } },
          grid: { display: false },
        },
        y: {
          stacked: true,
          beginAtZero: true,
          ticks: { color: cc.text, font: { size: 9 }, precision: 0 },
          grid: { color: cc.grid },
          title: {
            display: true,
            text: t('secops_finding_trend_yaxis') || 'Findings',
            color: cc.text,
            font: { size: 9 },
          },
        },
      },
    },
  });
}


// ---------------------------------------------------------------------------
// 1) Compliance Gap Chart — Framework pass/fail comparison
// ---------------------------------------------------------------------------
function renderComplianceGapChart(frameworks) {
  const wrap = document.getElementById('complianceGapWrap');
  if (!wrap) return;

  // Re-create canvas
  wrap.innerHTML = '<canvas id="complianceGapChart"></canvas>';
  const canv = document.getElementById('complianceGapChart');
  const cc = getChartColors();

  const fwKeys  = Object.keys(frameworks).filter(k => frameworks[k].total > 0);
  if (!fwKeys.length) {
    wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:12px;color:var(--text-muted)">${t('secops_no_data') || 'No data'}</div>`;
    return;
  }

  const labels = fwKeys.map(k => frameworks[k].label || k);
  const passed = fwKeys.map(k => frameworks[k].pass || 0);
  const failed = fwKeys.map(k => (frameworks[k].total || 0) - (frameworks[k].pass || 0));
  const scores = fwKeys.map(k => frameworks[k].score || 0);

  if (_complianceGapChart) _complianceGapChart.destroy();
  _complianceGapChart = new Chart(canv, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Pass',
          data: passed,
          backgroundColor: '#16a34a',
          borderRadius: 3,
        },
        {
          label: 'Fail',
          data: failed,
          backgroundColor: '#dc2626',
          borderRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { labels: { color: cc.text, font: { size: 9 }, boxWidth: 10 }, position: 'bottom' },
        tooltip: {
          callbacks: {
            afterBody: (items) => {
              const idx = items[0]?.dataIndex;
              if (idx == null) return '';
              return `Score: ${scores[idx]}%`;
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          ticks: { color: cc.text, font: { size: 9 }, precision: 0 },
          grid: { color: cc.grid },
          title: { display: true, text: t('secops_cg_xaxis') || 'Controls', color: cc.text, font: { size: 9 } },
        },
        y: {
          stacked: true,
          ticks: { color: cc.text, font: { size: 9 } },
          grid: { display: false },
        },
      },
    },
  });
}


// ---------------------------------------------------------------------------
// 2) Top 10 Failed Controls
// ---------------------------------------------------------------------------
function renderTopFailedChart(findings) {
  const wrap = document.getElementById('topFailedWrap');
  if (!wrap) return;

  const failFindings = findings.filter(f => f.status === 'FAIL' && (f.severity === 'CRITICAL' || f.severity === 'HIGH'));
  if (!failFindings.length) {
    wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:200px;font-size:12px;color:var(--text-muted)">${t('secops_no_failures') || 'No failures — great!'}</div>`;
    return;
  }

  // Group by title, track count + severity + service
  const countMap = {};
  const sevMap = {};
  const svcMap = {};
  for (const f of failFindings) {
    const key = f.title || f.id;
    countMap[key] = (countMap[key] || 0) + 1;
    if (!sevMap[key]) sevMap[key] = f.severity;
    if (!svcMap[key]) svcMap[key] = f.service || '';
  }

  const sorted = Object.entries(countMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const maxCount = sorted[0]?.[1] || 1;

  const sevBadgeColors = {
    CRITICAL: { bg: '#dc2626', text: '#fff' },
    HIGH:     { bg: '#ea580c', text: '#fff' },
    MEDIUM:   { bg: '#d97706', text: '#fff' },
    LOW:      { bg: '#3b82f6', text: '#fff' },
    INFO:     { bg: '#6b7280', text: '#fff' },
  };

  let html = '';
  for (const [title, count] of sorted) {
    const sev = sevMap[title] || 'INFO';
    const svc = svcMap[title] || '';
    const bc = sevBadgeColors[sev] || sevBadgeColors.INFO;
    const barPct = Math.round((count / maxCount) * 100);
    const escaped = _escHtml(title);
    const escapedSvc = _escHtml(svc);

    html += `<div style="margin-bottom:8px;cursor:pointer" title="${escaped}"
      onclick="selectCfd('cfdSvc','${escapedSvc}','${escapedSvc}');document.getElementById('findingsSection')?.scrollIntoView({behavior:'smooth'})">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
        <span style="background:${bc.bg};color:${bc.text};font-size:8px;font-weight:700;padding:1px 5px;border-radius:3px;white-space:nowrap;flex-shrink:0">${sev}</span>
        <span style="font-size:10px;color:var(--accent);font-weight:600;flex-shrink:0">${escapedSvc}</span>
        <span style="font-size:11px;color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">${escaped}</span>
        <span style="font-size:12px;font-weight:700;color:var(--text-primary);flex-shrink:0;min-width:20px;text-align:right">${count}</span>
      </div>
      <div style="background:var(--border);border-radius:3px;height:5px;overflow:hidden">
        <div style="background:${bc.bg};width:${barPct}%;height:5px;border-radius:3px;transition:width .4s ease"></div>
      </div>
    </div>`;
  }

  // Summary footer
  const totalFails = failFindings.length;
  const uniqueControls = Object.keys(countMap).length;
  html += `<div style="border-top:1px solid var(--border);margin-top:6px;padding-top:8px;display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted)">
    <span>${totalFails} total fails</span>
    <span>${uniqueControls} unique controls</span>
  </div>`;

  wrap.innerHTML = html;
}


// ---------------------------------------------------------------------------
// 3) Risk Exposure Treemap (HTML-based, no plugin needed)
// ---------------------------------------------------------------------------
function renderRiskTreemap(findings) {
  const wrap = document.getElementById('riskTreemapWrap');
  if (!wrap) return;

  // Group by service: count findings, track max severity
  const svcMap = {};
  const sevRank = { CRITICAL: 5, HIGH: 4, MEDIUM: 3, LOW: 2, INFO: 1 };
  for (const f of findings) {
    if (f.status === 'PASS' || f.status === 'NOT_AVAILABLE') continue;
    const svc = f.service || 'Unknown';
    if (!svcMap[svc]) svcMap[svc] = { count: 0, maxSev: 'INFO', maxRank: 0 };
    svcMap[svc].count++;
    const rank = sevRank[f.severity] || 0;
    if (rank > svcMap[svc].maxRank) {
      svcMap[svc].maxRank = rank;
      svcMap[svc].maxSev = f.severity;
    }
  }

  const entries = Object.entries(svcMap).sort((a, b) => b[1].count - a[1].count);
  if (!entries.length) {
    wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:12px;color:var(--text-muted)">${t('secops_no_data') || 'No data'}</div>`;
    return;
  }

  const totalFindings = entries.reduce((s, [, v]) => s + v.count, 0);
  const treemapColors = {
    CRITICAL: '#dc2626', HIGH: '#ea580c', MEDIUM: '#d97706', LOW: '#3b82f6', INFO: '#6b7280',
  };

  let html = '<div style="display:flex;flex-wrap:wrap;gap:4px;height:100%;align-content:flex-start;padding:6px">';
  for (const [svc, info] of entries) {
    const pct = Math.max((info.count / totalFindings) * 100, 8); // min 8% for visibility
    const bg = treemapColors[info.maxSev] || '#6b7280';
    const opacity = 0.55 + (info.maxRank / 5) * 0.45;
    const escaped = _escHtml(svc);
    html += `<div title="${escaped}: ${info.count} finding(s) — ${info.maxSev}"
      onclick="selectCfd('cfdSvc','${escaped}','${escaped}');document.getElementById('findingsSection')?.scrollIntoView({behavior:'smooth'})"
      style="
      flex:0 0 calc(${Math.min(pct, 50)}% - 4px);
      min-width:70px;
      height:${Math.max(44, Math.min(72, 24 + info.count * 3))}px;
      background:${bg};
      opacity:${opacity.toFixed(2)};
      border-radius:5px;
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      color:#fff;font-weight:600;
      padding:4px 6px;text-align:center;overflow:hidden;
      cursor:pointer;transition:opacity 0.15s,transform 0.1s;
    " onmouseenter="this.style.opacity='1';this.style.transform='scale(1.03)'"
      onmouseleave="this.style.opacity='${opacity.toFixed(2)}';this.style.transform='scale(1)'">
      <span style="font-size:${info.count > 5 ? 11 : 10}px;line-height:1.2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%">${escaped}</span>
      <span style="font-size:12px;font-weight:700;margin-top:2px">${info.count}</span>
    </div>`;
  }
  html += '</div>';

  // Legend
  html += '<div style="display:flex;gap:10px;justify-content:center;padding:4px 0;flex-wrap:wrap">';
  for (const sev of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']) {
    html += `<span style="font-size:8px;color:var(--text-muted);display:flex;align-items:center;gap:3px">
      <span style="width:8px;height:8px;border-radius:2px;background:${treemapColors[sev]};display:inline-block"></span>${sev}
    </span>`;
  }
  html += '</div>';

  wrap.innerHTML = html;
}


// ---------------------------------------------------------------------------
// 4) Scan Delta — changes between last 2 scans
// ---------------------------------------------------------------------------
function renderScanDeltaChart(profile) {
  const wrap = document.getElementById('scanDeltaWrap');
  if (!wrap) return;

  const history = loadScanHistory(profile);
  if (history.length < 2) {
    wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:12px;color:var(--text-muted);text-align:center;padding:20px">${t('secops_delta_empty') || 'Run 2+ scans to see changes'}</div>`;
    return;
  }

  const curr = history[history.length - 1];
  const prev = history[history.length - 2];

  const categories = ['Critical', 'High', 'Medium', 'Low', 'Info', 'Failed', 'Passed'];
  const currVals = [curr.critical||0, curr.high||0, curr.medium||0, curr.low||0, curr.info||0, curr.failed||0, curr.passed||0];
  const prevVals = [prev.critical||0, prev.high||0, prev.medium||0, prev.low||0, prev.info||0, prev.failed||0, prev.passed||0];
  const deltas = currVals.map((v, i) => v - prevVals[i]);

  const barColors = deltas.map((d, i) => {
    // For passed: increase is green, decrease is red (inverted)
    if (i === 6) return d >= 0 ? '#16a34a' : '#dc2626';
    // For all severities/failed: increase is red, decrease is green
    return d > 0 ? '#dc2626' : d < 0 ? '#16a34a' : '#6b7280';
  });

  wrap.innerHTML = '<canvas id="scanDeltaChart"></canvas>';
  const canv = document.getElementById('scanDeltaChart');
  const cc = getChartColors();

  if (_scanDeltaChart) _scanDeltaChart.destroy();
  _scanDeltaChart = new Chart(canv, {
    type: 'bar',
    data: {
      labels: categories,
      datasets: [{
        data: deltas,
        backgroundColor: barColors,
        borderRadius: 3,
        barPercentage: 0.6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => {
              const d = item.raw;
              const sign = d > 0 ? '+' : '';
              return `${sign}${d} (${prevVals[item.dataIndex]} → ${currVals[item.dataIndex]})`;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: cc.text, font: { size: 9 } },
          grid: { display: false },
        },
        y: {
          ticks: { color: cc.text, font: { size: 9 }, precision: 0 },
          grid: { color: cc.grid },
          title: { display: true, text: t('secops_delta_yaxis') || 'Change', color: cc.text, font: { size: 9 } },
        },
      },
    },
  });
}


// ---------------------------------------------------------------------------
// 5) Pass Rate by Service — 100% stacked horizontal bar
// ---------------------------------------------------------------------------
function renderPassRateChart(services) {
  const wrap = document.getElementById('passRateWrap');
  if (!wrap) return;

  const svcNames = Object.keys(services).filter(s => {
    const d = services[s];
    return (d.pass + d.fail + d.warning) > 0;
  });
  if (!svcNames.length) {
    wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:200px;font-size:12px;color:var(--text-muted)">${t('secops_no_data') || 'No data'}</div>`;
    return;
  }

  // Sort by score ascending (worst first), show ALL services
  svcNames.sort((a, b) => (services[a].score || 0) - (services[b].score || 0));

  const passData = svcNames.map(s => services[s].pass || 0);
  const failData = svcNames.map(s => services[s].fail || 0);
  const warnData = svcNames.map(s => services[s].warning || 0);

  // Dynamic height: 22px per service, min 200px
  const chartH = Math.max(200, svcNames.length * 22 + 40);
  wrap.innerHTML = `<canvas id="passRateChart" style="height:${chartH}px"></canvas>`;
  const canv = document.getElementById('passRateChart');
  const cc = getChartColors();

  if (_passRateChart) _passRateChart.destroy();
  _passRateChart = new Chart(canv, {
    type: 'bar',
    data: {
      labels: svcNames,
      datasets: [
        { label: 'Pass',    data: passData, backgroundColor: '#16a34a', borderRadius: 2 },
        { label: 'Warning', data: warnData, backgroundColor: '#d97706', borderRadius: 2 },
        { label: 'Fail',    data: failData, backgroundColor: '#dc2626', borderRadius: 2 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { labels: { color: cc.text, font: { size: 9 }, boxWidth: 10 }, position: 'bottom' },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            afterBody: (items) => {
              const idx = items[0]?.dataIndex;
              if (idx == null) return '';
              const svc = svcNames[idx];
              return `Score: ${services[svc].score}%`;
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          ticks: { color: cc.text, font: { size: 9 }, precision: 0 },
          grid: { color: cc.grid },
        },
        y: {
          stacked: true,
          ticks: { color: cc.text, font: { size: 8 } },
          grid: { display: false },
        },
      },
    },
  });
}


// ---------------------------------------------------------------------------
// Heat Map (Service × Region)
// ---------------------------------------------------------------------------
function renderHeatMap(findings) {
  const container = document.getElementById('heatmapContainer');
  if (!container) return;

  const services = [...new Set(findings.map(f => f.service))].sort();
  // Include 'global' as a column so IAM/S3/CloudTrail global findings are visible
  const rawRegions = [...new Set(findings.map(f => f.region).filter(Boolean))].sort();
  // Put 'global' first, then regional sorted
  const regions = [];
  if (rawRegions.includes('global')) regions.push('global');
  rawRegions.filter(r => r !== 'global').forEach(r => regions.push(r));

  if (!regions.length) {
    container.innerHTML = `<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:30px">No regional data</div>`;
    return;
  }

  // Build grid
  const grid = {};
  for (const svc of services) {
    grid[svc] = {};
    for (const reg of regions) grid[svc][reg] = { pass: 0, fail: 0, total: 0 };
  }
  for (const f of findings) {
    const svc = f.service, reg = f.region;
    if (!grid[svc] || !grid[svc][reg]) continue;
    grid[svc][reg].total++;
    if (f.status === 'PASS') grid[svc][reg].pass++;
    else if (f.status === 'FAIL') grid[svc][reg].fail++;
  }

  const shortReg = r => {
    if (r === 'global') return 'GLB';
    return r.replace('us-east-','ue').replace('us-west-','uw')
            .replace('eu-west-','ew').replace('eu-central-','ec')
            .replace('ap-southeast-','ase').replace('ap-northeast-','ane')
            .replace('ap-south-','as').replace('ca-central-','cc')
            .replace('sa-east-','se').replace('eu-north-','en')
            .replace('me-south-','ms').replace('af-south-','af')
            .replace('me-central-','mc').replace('il-central-','il');
  };

  let html = `<table style="border-collapse:collapse;font-size:10px;width:100%">
    <thead><tr>
      <th style="padding:3px 6px;text-align:left;position:sticky;left:0;background:var(--bg-card);color:var(--text-muted);font-weight:600;z-index:1">SVC</th>
      ${regions.map(r => `<th style="padding:3px 4px;text-align:center;color:var(--text-muted);font-weight:500" title="${r}">${shortReg(r)}</th>`).join('')}
    </tr></thead><tbody>`;

  for (const svc of services) {
    html += `<tr><td style="padding:3px 6px;font-weight:600;color:var(--text-secondary);position:sticky;left:0;background:var(--bg-card);z-index:1">${svc}</td>`;
    for (const reg of regions) {
      const cell = grid[svc][reg];
      if (!cell.total) { html += `<td style="padding:3px 4px"></td>`; continue; }
      const pct   = Math.round(cell.pass / cell.total * 100);
      const color = pct >= 80 ? '#16a34a' : pct >= 60 ? '#d97706' : '#dc2626';
      const bg    = pct >= 80 ? 'rgba(22,163,74,.15)' : pct >= 60 ? 'rgba(217,119,6,.15)' : 'rgba(220,38,38,.15)';
      html += `<td style="background:${bg};color:${color};text-align:center;padding:3px 4px;border-radius:3px;font-weight:700;cursor:pointer"
                  onclick="filterByServiceRegion('${svc}','${reg}')"
                  title="${svc} / ${reg}: ${cell.pass}/${cell.total} passed (${pct}%)">${pct}%</td>`;
    }
    html += `</tr>`;
  }

  html += `</tbody></table>`;
  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Remediation Progress
// ---------------------------------------------------------------------------
function renderRemediationProgress(findings) {
  const container = document.getElementById('remediationContainer');
  if (!container) return;

  const fails = s => findings.filter(f => f.status === 'FAIL' && s.includes(f.severity)).length;
  const tots  = s => findings.filter(f => s.includes(f.severity)).length;

  const critFail   = fails(['CRITICAL']);
  const critTotal  = tots(['CRITICAL']);
  const highFail   = fails(['HIGH']);
  const highTotal  = tots(['HIGH']);
  const medFail    = fails(['MEDIUM']);
  const medTotal   = tots(['MEDIUM']);
  const lowFail    = fails(['LOW','INFO']);
  const lowTotal   = tots(['LOW','INFO']);
  const totalFail  = findings.filter(f => f.status === 'FAIL').length;

  const bar = (fail, total, color) => {
    if (!total) return `<div style="background:var(--border);border-radius:4px;height:8px"></div>`;
    const pct = Math.round((total - fail) / total * 100);
    return `
      <div style="background:var(--border);border-radius:4px;height:8px;overflow:hidden">
        <div style="background:${color};width:${pct}%;height:8px;border-radius:4px;transition:width .6s ease"></div>
      </div>`;
  };

  const quickWins = fails(['LOW','INFO']);

  container.innerHTML = `
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
        <span style="font-weight:600;color:#dc2626">Critical</span>
        <span style="color:var(--text-muted)">${critFail} open / ${critTotal}</span>
      </div>
      ${bar(critFail, critTotal, '#dc2626')}
    </div>
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
        <span style="font-weight:600;color:#ea580c">High</span>
        <span style="color:var(--text-muted)">${highFail} open / ${highTotal}</span>
      </div>
      ${bar(highFail, highTotal, '#ea580c')}
    </div>
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
        <span style="font-weight:600;color:#d97706">Medium</span>
        <span style="color:var(--text-muted)">${medFail} open / ${medTotal}</span>
      </div>
      ${bar(medFail, medTotal, '#d97706')}
    </div>
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
        <span style="font-weight:600;color:#65a30d">Low + Info</span>
        <span style="color:var(--text-muted)">${lowFail} open / ${lowTotal}</span>
      </div>
      ${bar(lowFail, lowTotal, '#65a30d')}
    </div>
    <div style="border-top:1px solid var(--border);padding-top:10px;margin-top:2px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <div style="text-align:center">
        <div style="font-size:20px;font-weight:700;color:#dc2626">${totalFail}</div>
        <div style="font-size:10px;color:var(--text-muted)">Total open</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:20px;font-weight:700;color:#65a30d">${quickWins}</div>
        <div style="font-size:10px;color:var(--text-muted)">Quick wins</div>
      </div>
    </div>
    ${(() => {
      const topFails = findings.filter(f => f.status === 'FAIL')
        .sort((a, b) => (SEV_WEIGHTS[b.severity]||1) - (SEV_WEIGHTS[a.severity]||1))
        .slice(0, 5);
      if (!topFails.length) return '';
      return '<div style="border-top:1px solid var(--border);padding-top:10px;margin-top:8px;font-size:11px">' +
        '<div style="font-weight:600;color:var(--text-secondary);margin-bottom:6px">Top Priority</div>' +
        topFails.map(f => {
          const sc = SEV_COLORS[f.severity] || '#888';
          return '<div style="display:flex;align-items:center;gap:6px;padding:3px 0;color:var(--text-primary)">' +
            '<span class="badge" style="background:'+sc+';font-size:9px;padding:1px 5px;border-radius:3px">'+f.severity+'</span>' +
            '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_escHtml(f.title)+'">'+_escHtml(f.title)+'</span>' +
            '</div>';
        }).join('') + '</div>';
    })()}`;
}

// ---------------------------------------------------------------------------
// Findings Table
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Custom Filter Dropdowns (CFD)
// ---------------------------------------------------------------------------

// CFD state: { cfdSev: '', cfdSvc: '', cfdStatus: '', cfdFw: '' }
const _cfdValues = { cfdSev: '', cfdSvc: '', cfdStatus: '', cfdFw: '' };

function toggleCfd(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const wasOpen = el.classList.contains('open');
  // Close all dropdowns first
  document.querySelectorAll('.cfd.open').forEach(d => d.classList.remove('open'));
  if (!wasOpen) {
    el.classList.add('open');
    // Focus search input if searchable
    const search = el.querySelector('.cfd-search');
    if (search) setTimeout(() => search.focus(), 50);
  }
}

function selectCfd(id, value, label) {
  _cfdValues[id] = value;
  const labelEl = document.getElementById(id + 'Label');
  if (labelEl) labelEl.textContent = label;
  // Update selected state
  const panel = document.getElementById(id + 'Panel') || document.getElementById(id).querySelector('.cfd-panel');
  if (panel) {
    panel.querySelectorAll('.cfd-opt').forEach(opt => {
      opt.classList.toggle('selected', opt.dataset.val === value);
    });
  }
  // Close dropdown
  document.getElementById(id)?.classList.remove('open');
  // Clear search if any
  const search = document.getElementById(id + 'Search');
  if (search) { search.value = ''; filterCfdOptions(id, ''); }
  applyFilters();
}

function filterCfdOptions(id, query) {
  const container = document.getElementById(id + 'Options');
  if (!container) return;
  const q = query.toLowerCase();
  let visible = 0;
  container.querySelectorAll('.cfd-opt').forEach(opt => {
    const val = opt.dataset.val || '';
    const text = opt.textContent.toLowerCase();
    const show = !q || val === '' || text.includes(q);
    opt.classList.toggle('hidden', !show);
    if (show) visible++;
  });
  // Show no-match message
  let noMatch = container.querySelector('.cfd-no-match');
  if (visible <= 1 && q) { // 1 = only "All Services"
    if (!noMatch) {
      noMatch = document.createElement('div');
      noMatch.className = 'cfd-no-match';
      container.appendChild(noMatch);
    }
    noMatch.textContent = 'No match';
    noMatch.style.display = 'block';
  } else if (noMatch) {
    noMatch.style.display = 'none';
  }
}

// Close dropdowns on outside click
document.addEventListener('click', (e) => {
  if (!e.target.closest('.cfd')) {
    document.querySelectorAll('.cfd.open').forEach(d => d.classList.remove('open'));
  }
});

function populateServiceFilter(findings) {
  const svcs = [...new Set(findings.map(f => f.service))].sort();
  const container = document.getElementById('cfdSvcOptions');
  if (!container) return;
  const cur = _cfdValues.cfdSvc;
  container.innerHTML = `<div class="cfd-opt ${!cur ? 'selected' : ''}" data-val="" onclick="selectCfd('cfdSvc','','All Services')">All Services</div>`
    + svcs.map(s => `<div class="cfd-opt ${cur === s ? 'selected' : ''}" data-val="${_escHtml(s)}" onclick="selectCfd('cfdSvc','${_escHtml(s)}','${_escHtml(s)}')">${_escHtml(s)}</div>`).join('');
}

function applyFilters() {
  const sev    = _cfdValues.cfdSev    || '';
  const svc    = _cfdValues.cfdSvc    || '';
  const status = _cfdValues.cfdStatus || '';
  const fw     = _cfdValues.cfdFw     || '';

  _filteredFindings = _allFindings.filter(f => {
    if (sev    && f.severity !== sev)                              return false;
    if (svc    && f.service  !== svc)                              return false;
    if (status && f.status   !== status)                           return false;
    if (fw     && !Object.keys(f.frameworks || {}).includes(fw))   return false;
    return true;
  });
  _page = 1;
  renderFindingsTable();
}

function clearFilters() {
  // Reset all custom dropdowns
  Object.keys(_cfdValues).forEach(k => { _cfdValues[k] = ''; });
  ['cfdSev','cfdSvc','cfdStatus','cfdFw'].forEach(id => {
    const label = document.getElementById(id + 'Label');
    if (label) {
      const defaults = { cfdSev: 'All Severities', cfdSvc: 'All Services', cfdStatus: 'All Statuses', cfdFw: 'All Frameworks' };
      label.textContent = defaults[id];
    }
    const panel = document.getElementById(id + 'Panel') || document.getElementById(id)?.querySelector('.cfd-panel');
    if (panel) {
      panel.querySelectorAll('.cfd-opt').forEach(opt => {
        opt.classList.toggle('selected', opt.dataset.val === '');
      });
    }
  });
  const s = document.getElementById('findingsSearch');
  if (s) s.value = '';
  _searchText = '';
  _filteredFindings = [..._allFindings];
  _page = 1;
  renderFindingsTable();
}

// Sort column toggle
function setSortCol(col) {
  if (_sortCol === col) {
    _sortDir = _sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    _sortCol = col;
    _sortDir = 'asc';
  }
  // Update sort indicators
  ['severity','status','service','resource','region'].forEach(c => {
    const el = document.getElementById(`sortInd_${c}`);
    if (!el) return;
    el.textContent = _sortCol === c ? (_sortDir === 'asc' ? '↑' : '↓') : '↕';
    el.style.opacity = _sortCol === c ? '1' : '.35';
  });
  renderFindingsTable();
}

// Search input handler (debounced)
let _searchDebounceTimer = null;
function onSearchInput(val) {
  clearTimeout(_searchDebounceTimer);
  _searchDebounceTimer = setTimeout(() => {
    _searchText = val.toLowerCase();
    _page = 1;
    renderFindingsTable();
  }, 300);
}

// Toggle accordion row expansion
function toggleRowExpand(fid) {
  if (_expandedRows.has(fid)) {
    _expandedRows.delete(fid);
  } else {
    _expandedRows.add(fid);
  }
  renderFindingsTable();
}

// Export filtered findings as CSV
function exportFilteredCSV() {
  const data = _searchText
    ? _filteredFindings.filter(f =>
        (f.title||'').toLowerCase().includes(_searchText) ||
        (f.resource_id||'').toLowerCase().includes(_searchText) ||
        (f.service||'').toLowerCase().includes(_searchText) ||
        (f.region||'').toLowerCase().includes(_searchText))
    : _filteredFindings;

  const esc = v => `"${(v||'').toString().replace(/"/g,'""')}"`;
  const headers = ['Severity','Status','Service','Title','ResourceID','ResourceType','Region','Frameworks','Remediation'];
  const rows = data.map(f => [
    esc(f.severity), esc(f.status), esc(f.service), esc(f.title),
    esc(f.resource_id), esc(f.resource_type), esc(f.region),
    esc(Object.keys(f.frameworks||{}).join(';')),
    esc(f.remediation),
  ].join(','));
  const csv  = [headers.join(','), ...rows].join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = `secops_findings_${Date.now()}.csv`;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

function renderFindingsTable() {
  // 1) Apply free-text search on top of dropdown filters
  let sorted = [..._filteredFindings];
  if (_searchText) {
    const q = _searchText;
    sorted = sorted.filter(f =>
      (f.title      || '').toLowerCase().includes(q) ||
      (f.resource_id|| '').toLowerCase().includes(q) ||
      (f.service    || '').toLowerCase().includes(q) ||
      (f.region     || '').toLowerCase().includes(q) ||
      (f.description|| '').toLowerCase().includes(q));
  }

  // 2) Sort
  sorted.sort((a, b) => {
    let cmp = 0;
    if      (_sortCol === 'severity') cmp = SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity);
    else if (_sortCol === 'status')   cmp = (a.status||'').localeCompare(b.status||'');
    else if (_sortCol === 'service')  cmp = (a.service||'').localeCompare(b.service||'');
    else if (_sortCol === 'resource') cmp = (a.resource_id||'').localeCompare(b.resource_id||'');
    else if (_sortCol === 'region')   cmp = (a.region||'').localeCompare(b.region||'');
    return _sortDir === 'asc' ? cmp : -cmp;
  });

  const total = sorted.length;
  const start = (_page - 1) * PAGE_SIZE;
  const page  = sorted.slice(start, start + PAGE_SIZE);

  // 3) Render rows with accordion
  document.getElementById('findingsBody').innerHTML = page.map((f, i) => {
    const sc      = SEV_COLORS[f.severity]  || '#888';
    const stc     = STATUS_COLORS[f.status] || '#888';
    const fws     = Object.keys(f.frameworks || {}).join(', ');
    const expanded = _expandedRows.has(f.id);
    const fwDetail = Object.entries(f.frameworks || {}).map(([k, v]) => {
      const controls = Array.isArray(v) ? v.join(', ') :
                       (typeof v === 'object' && v.pillar) ? `${v.pillar} → ${(v.controls||[]).join(', ')}` :
                       JSON.stringify(v);
      return `<span style="margin-right:8px;white-space:nowrap"><strong>${_escHtml(k)}</strong>: ${_escHtml(controls)}</span>`;
    }).join('');

    const mainRow = `<tr style="cursor:pointer;${expanded ? 'background:var(--bg-base)' : ''}"
         onclick="toggleRowExpand('${f.id.replace(/'/g,"\\'")}')">
      <td><span class="badge" style="background:${sc}">${_escHtml(f.severity)}</span></td>
      <td><span class="badge" style="background:${stc}">${_escHtml(f.status)}</span></td>
      <td style="white-space:nowrap;font-size:12px">${_escHtml(f.service)}</td>
      <td>
        <div style="font-weight:500;font-size:12px;display:flex;align-items:center;gap:6px">
          <span style="opacity:.5;font-size:10px">${expanded ? '▼' : '▶'}</span>${_escHtml(f.title)}
        </div>
      </td>
      <td style="font-family:monospace;font-size:11px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
          title="${_escHtml(f.resource_id||'')}">${_escHtml(f.resource_id)}</td>
      <td style="font-size:11px;white-space:nowrap">${_escHtml(f.region)}</td>
      <td style="font-size:11px;color:var(--text-muted)">${_escHtml(fws)}</td>
    </tr>`;

    if (!expanded) return mainRow;

    const detailRow = `<tr style="background:var(--bg-base)">
      <td colspan="7" style="padding:0 16px 16px 32px;border-bottom:2px solid var(--accent)">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px">
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Description</div>
            <div style="font-size:12px;color:var(--text-secondary);line-height:1.6">${_escHtml(f.description)}</div>
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Remediation</div>
            <div style="font-size:12px;color:var(--text-secondary);line-height:1.6">${_escHtml(f.remediation || '—')}</div>
          </div>
        </div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:4px;font-size:11px">
          <span style="color:var(--text-muted);font-weight:600;margin-right:4px">Frameworks:</span>${fwDetail}
          <span style="margin-left:12px;color:var(--text-muted)">Type: <code style="font-size:10px;color:var(--text-secondary)">${_escHtml(f.resource_type||'—')}</code></span>
        </div>
      </td>
    </tr>`;

    return mainRow + detailRow;
  }).join('');

  // 4) Pagination
  const pages = Math.ceil(total / PAGE_SIZE);
  const pag   = document.getElementById('findingsPagination');
  let html    = `<span style="font-size:12px;color:var(--text-muted)">${total} ${t('secops_findings_count') || 'findings'}</span>`;
  if (pages > 1) {
    html += `<button class="btn btn-outline btn-sm" onclick="goPage(${_page-1})" ${_page===1?'disabled':''}>‹</button>`;
    for (let p = Math.max(1,_page-2); p <= Math.min(pages,_page+2); p++) {
      html += `<button class="btn btn-outline btn-sm${p===_page?' active':''}" onclick="goPage(${p})">${p}</button>`;
    }
    html += `<button class="btn btn-outline btn-sm" onclick="goPage(${_page+1})" ${_page===pages?'disabled':''}>›</button>`;
  }
  pag.innerHTML = html;
}

function goPage(p) {
  if (p < 1) return;
  const pages = Math.ceil(_filteredFindings.length / PAGE_SIZE);
  if (p > pages) return;
  _page = p;
  renderFindingsTable();
}

// ---------------------------------------------------------------------------
// Reports — save current scan and navigate
// ---------------------------------------------------------------------------

async function _autoGenerateReports(profile) {
  if (!profile) return;
  try {
    await fetch('/secops/api/reports/generate_all', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ profile }),
    });
    // Refresh report list silently
    loadReportList();
  } catch (_) { /* non-critical — ignore */ }
}

async function saveAndGoToReports(btn) {
  if (!_lastScan || _lastScan.status !== 'ok') {
    showSection('reports');
    return;
  }
  if (btn) { btn.disabled = true; btn.style.opacity = '.6'; }
  const statusEl = document.getElementById('reportStatus');

  try {
    const resp = await fetch('/secops/api/reports/generate_all', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ profile: _selectedProfile }),
    });
    const data = await resp.json();
    if (data.status === 'ok') {
      const fmts = Object.keys(data.filenames).filter(f => data.filenames[f]).join(', ').toUpperCase();
      if (statusEl) {
        statusEl.style.color = '#16a34a';
        statusEl.textContent = `Saved: ${fmts}`;
      }
    } else {
      if (statusEl) { statusEl.style.color = '#dc2626'; statusEl.textContent = data.error || 'Save failed'; }
    }
  } catch (e) {
    if (statusEl) { statusEl.style.color = '#dc2626'; statusEl.textContent = e.message; }
  } finally {
    if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
  }

  showSection('reports');
}

// ---------------------------------------------------------------------------
// Reports — Advice-style list with per-row delete + bulk delete
// ---------------------------------------------------------------------------
async function loadReportList() {
  try {
    const resp = await fetch('/secops/api/reports/list');
    const data = await resp.json();
    if (data.status !== 'ok') return;

    const tbody = document.getElementById('reportListBody');
    const table = document.getElementById('reportListTable');
    const empty = document.getElementById('reportListEmpty');
    const selAll = document.getElementById('reportSelectAll');
    if (!tbody || !table || !empty) return;

    if (!data.reports.length) {
      table.style.display = 'none'; empty.style.display = 'block';
      _reportGroups = {};
      return;
    }

    // Group files by base key: secops_{profile}_{YYYYMMDD}_{HHMMSS}
    const groups = {};
    for (const r of data.reports) {
      const m = r.filename.match(/^(secops_.+_\d{8}_\d{6})\.(html|csv|pdf)$/);
      if (!m) continue;
      const base = m[1];
      if (!groups[base]) groups[base] = { base, mtime: r.mtime, files: {} };
      groups[base].files[m[2]] = r;
      if (r.mtime > groups[base].mtime) groups[base].mtime = r.mtime;
    }

    _reportGroups = groups;
    const sorted = Object.values(groups).sort((a, b) => b.mtime - a.mtime);
    if (!sorted.length) { table.style.display = 'none'; empty.style.display = 'block'; return; }

    const fmtDate = ts => new Date(ts * 1000).toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });

    const profileFromBase = base => {
      const m = base.match(/^secops_(.+)_\d{8}_\d{6}$/);
      return m ? m[1] : base;
    };

    const fmtBadge = (label, color, file, target) => file
      ? `<a href="/secops/reports/download/${encodeURIComponent(file.filename)}" ${target === '_blank' ? 'target="_blank" rel="noopener"' : `download="${_escHtml(file.filename)}"`}
            title="Download ${label}"
            style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;background:${color}22;color:${color};border:1px solid ${color}44;text-decoration:none;transition:background .15s"
            onmouseover="this.style.background='${color}44'" onmouseout="this.style.background='${color}22'">${label}</a>`
      : `<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;background:var(--bg-card);color:var(--text-muted);border:1px solid var(--border);opacity:.4">${label}</span>`;

    const delSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

    tbody.innerHTML = sorted.map(g => {
      const safe = g.base.replace(/'/g, "\\'");
      const html = g.files['html'];
      const csv  = g.files['csv'];
      const pdf  = g.files['pdf'];
      const profile = profileFromBase(g.base);

      return `<tr class="report-row">
        <td style="text-align:center;width:36px">
          <input type="checkbox" class="report-check" data-base="${safe}"
                 style="accent-color:var(--accent);width:14px;height:14px;cursor:pointer"
                 onchange="onReportCheckChange()">
        </td>
        <td style="font-size:12px">
          <div style="font-weight:600;color:var(--text-primary)">${fmtDate(g.mtime)}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px">${_escHtml(profile)}</div>
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:nowrap">
            ${fmtBadge('HTML', '#3b82f6', html, '_blank')}
            ${fmtBadge('CSV',  '#10b981', csv)}
            ${fmtBadge('PDF',  '#f97316', pdf)}
          </div>
        </td>
        <td style="text-align:center;width:40px">
          <button class="report-delete-btn" onclick="deleteReportGroup('${safe}')" title="Delete">
            ${delSvg}
          </button>
        </td>
      </tr>`;
    }).join('');

    if (selAll) selAll.checked = false;
    table.style.display = '';
    empty.style.display = 'none';
    updateDeleteBtnVisibility();
  } catch (e) { /* silent */ }
}

function toggleSelectAllReports(masterCb) {
  document.querySelectorAll('.report-check').forEach(cb => { cb.checked = masterCb.checked; });
  updateDeleteBtnVisibility();
}

function onReportCheckChange() {
  const all     = document.querySelectorAll('.report-check');
  const checked = document.querySelectorAll('.report-check:checked');
  const master  = document.getElementById('reportSelectAll');
  if (master) {
    master.indeterminate = checked.length > 0 && checked.length < all.length;
    master.checked       = checked.length === all.length && all.length > 0;
  }
  updateDeleteBtnVisibility();
}

function updateDeleteBtnVisibility() {
  const n   = document.querySelectorAll('.report-check:checked').length;
  const btn = document.getElementById('deleteSelectedBtn');
  if (btn) btn.style.display = n >= 2 ? 'inline-flex' : 'none';
}

async function deleteReportGroup(base) {
  try {
    const resp = await fetch('/secops/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases: [base] }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportList();
  } catch (e) { /* silent */ }
}

async function deleteSelectedReports() {
  const checked = [...document.querySelectorAll('.report-check:checked')];
  if (checked.length < 2) return;
  const bases = checked.map(cb => cb.dataset.base).filter(Boolean);
  if (!bases.length) return;
  try {
    const resp = await fetch('/secops/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportList();
  } catch (e) { /* silent */ }
}

function exportSelected(fmt) {
  const checked = [...document.querySelectorAll('.report-check:checked')];
  const exportEl = document.getElementById('exportStatus');

  if (!checked.length) {
    if (exportEl) { exportEl.style.color = '#d97706'; exportEl.textContent = 'Select at least one report.'; }
    return;
  }

  let downloaded = 0;
  let missing    = 0;

  checked.forEach((cb, i) => {
    const group = _reportGroups[cb.dataset.base];
    if (!group || !group.files[fmt]) { missing++; return; }
    setTimeout(() => {
      const file = group.files[fmt];
      const a = document.createElement('a');
      a.href = `/secops/reports/download/${encodeURIComponent(file.filename)}`;
      a.download = file.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }, i * 350);
    downloaded++;
  });

  if (exportEl) {
    if (downloaded === 0) {
      exportEl.style.color = '#dc2626';
      exportEl.textContent = `No ${fmt.toUpperCase()} files available for selected reports.`;
    } else if (missing > 0) {
      exportEl.style.color = '#d97706';
      exportEl.textContent = `Downloading ${downloaded} ${fmt.toUpperCase()} file${downloaded > 1 ? 's' : ''} (${missing} not available).`;
    } else {
      exportEl.style.color = '#16a34a';
      exportEl.textContent = `Downloading ${downloaded} ${fmt.toUpperCase()} file${downloaded > 1 ? 's' : ''}…`;
    }
    setTimeout(() => updateExportStatus(), 4000);
  }
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------
function showLoading(on, msg) {
  const banner = document.getElementById('scanProgressBanner');
  if (!banner) return;
  banner.style.display = on ? 'block' : 'none';
  if (msg) {
    const el = document.getElementById('loadingMsg');
    if (el) el.textContent = msg;
  }
  if (!on) updateProgress(0, 0, '');
}

function updateProgress(percent, completed, service, total) {
  const bar = document.getElementById('progressBar');
  const pct = document.getElementById('progressPct');
  const svc = document.getElementById('progressService');
  const cnt = document.getElementById('progressCount');
  if (bar) bar.style.width = percent + '%';
  if (pct) pct.textContent = total ? `${percent}%` : '';
  if (svc) svc.textContent = service || '';
  if (cnt) cnt.textContent = total ? `${completed} / ${total}` : '';
}

function showCacheBanner(type, msg) {
  const el = document.getElementById('cacheBanner');
  if (!el) return;
  const colors = { info: '#1e3a5f', warning: '#7c4a00', error: '#5f1d1d' };
  const bords  = { info: '#2563eb', warning: '#d97706', error: '#dc2626' };
  el.style.cssText = `
    display:block;padding:10px 16px;border-radius:6px;margin-bottom:16px;
    background:${colors[type]||colors.info};border-left:3px solid ${bords[type]||bords.info};
    font-size:13px;color:var(--text-primary)`;
  el.textContent = msg;
}

function hideCacheBanner() {
  const el = document.getElementById('cacheBanner');
  if (el) el.style.display = 'none';
}

// ---------------------------------------------------------------------------
// Section navigation (same pattern as FinOps)
// ---------------------------------------------------------------------------
function showSection(name) {
  document.querySelectorAll('.page-section').forEach(s => {
    s.style.display = s.id === `section-${name}` ? 'block' : 'none';
  });
  document.querySelectorAll('.nav-item[data-section]').forEach(link => {
    link.classList.toggle('active', link.dataset.section === name);
  });
  location.hash = '#' + name;
  if (name === 'reports') loadReportList();
}

// ---------------------------------------------------------------------------
// Profile section toggle
// ---------------------------------------------------------------------------
function toggleProfileSection() {
  const sec = document.getElementById('profileSection');
  if (sec) sec.classList.toggle('open');
}

// ---------------------------------------------------------------------------
// Scan History
// ---------------------------------------------------------------------------
function toggleScanHistory() {
  const sec = document.getElementById('scanHistorySection');
  if (sec) sec.classList.toggle('open');
}

async function loadCachedScans() {
  const list = document.getElementById('scanHistoryList');
  const countEl = document.getElementById('scanHistoryCount');
  try {
    const resp = await fetch('/secops/api/scan-history');
    const data = await resp.json();
    const scans = data.scans || [];
    if (countEl) countEl.textContent = scans.length;

    if (scans.length === 0) {
      list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px">' +
        (t('secops_no_scan_history') || 'No cached scans found') + '</div>';
      return;
    }

    const delSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

    let html = '<div style="max-height:400px;overflow-y:auto">';
    html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
    html += '<thead style="position:sticky;top:0;z-index:1;background:var(--bg-card)"><tr style="border-bottom:1px solid var(--border)">' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Profile</th>' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Account</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Score</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Passed</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Failed</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Services</th>' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Scan Time</th>' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Age</th>' +
      '<th style="width:100px"></th>' +
      '</tr></thead><tbody>';

    for (const s of scans) {
      const ageMins = Math.round(s.age_seconds / 60);
      const ageStr = ageMins < 60 ? `${ageMins}m ago` : `${Math.round(ageMins / 60)}h ago`;
      const isActive = _selectedProfile === s.profile;
      const scoreColor = s.score >= 70 ? '#16a34a' : s.score >= 40 ? '#d97706' : '#dc2626';
      const scanTimeStr = s.scan_time ? new Date(s.scan_time).toLocaleString() : '—';
      const safeProfile = s.profile.replace(/'/g, "\\'");
      html += `<tr style="border-bottom:1px solid var(--border);${isActive ? 'background:var(--accent-dim)' : ''}">
        <td style="padding:6px 12px;font-weight:600;color:var(--text-primary)">${_escHtml(s.profile)}</td>
        <td style="padding:6px 12px;font-family:monospace;font-size:11px;color:var(--text-muted)">${_escHtml(s.account_id || '—')}</td>
        <td style="padding:6px 12px;text-align:right;color:${scoreColor};font-weight:700">${s.score}%</td>
        <td style="padding:6px 12px;text-align:right;color:#16a34a">${s.passed}</td>
        <td style="padding:6px 12px;text-align:right;color:#dc2626">${s.failed}</td>
        <td style="padding:6px 12px;text-align:right;color:var(--text-secondary)">${s.services_count}</td>
        <td style="padding:6px 12px;color:var(--text-muted);font-size:11px">${scanTimeStr}</td>
        <td style="padding:6px 12px;color:var(--text-muted);font-size:11px">${ageStr}</td>
        <td style="padding:4px 8px;text-align:right;white-space:nowrap">
          <button class="btn ${isActive ? 'btn-primary' : 'btn-outline'} btn-sm" style="font-size:10px;padding:2px 10px"
            onclick="viewScanHistory('${safeProfile}')">${isActive ? 'Active' : 'View'}</button>
          <button class="report-delete-btn" style="margin-left:4px;width:24px;height:24px" title="Delete scan"
            onclick="deleteScanHistory('${safeProfile}')">${delSvg}</button>
        </td>
      </tr>`;
    }
    html += '</tbody></table></div>';
    list.innerHTML = html;
  } catch (e) {
    list.innerHTML = `<div style="text-align:center;padding:16px;color:#f87171;font-size:12px">${_escHtml(e.message)}</div>`;
  }
}

async function deleteScanHistory(profile) {
  try {
    const resp = await fetch('/secops/api/scan-history/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile }),
    });
    const data = await resp.json();
    if (data.status === 'ok') {
      loadCachedScans();
      // If deleted scan was active, clear dashboard
      if (_selectedProfile === profile) {
        _selectedProfile = '';
        _lastScan = null;
        ['radarSection','chartsRow','chartsRow2','chartsRow3','findingsSection']
          .forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; });
      }
    }
  } catch (_) { /* silent */ }
}

async function viewScanHistory(profile) {
  try {
    const resp = await fetch(`/secops/api/last-scan?profile=${encodeURIComponent(profile)}`);
    const data = await resp.json();
    if (data.status === 'not_found') return;
    _selectedProfile = profile;
    _lastScan = data;
    renderDashboard(data);
    const age = Math.round((data._cache_age_seconds || 0) / 60);
    showCacheBanner('info', `${t('secops_last_scan_age') || 'Last scan'}: ${age} ${t('secops_minutes_ago') || 'minutes ago'}. ${t('secops_click_scan') || 'Click "Start Scan" to refresh.'}`);
    loadCachedScans(); // refresh active state
  } catch (e) { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  // Section nav: wire sidebar links
  document.querySelectorAll('.nav-item[data-section]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      showSection(link.dataset.section);
    });
  });

  // Default: exclude AWS default resources checked
  const excludeEl = document.getElementById('excludeDefaults');
  if (excludeEl) excludeEl.checked = true;

  // Hash routing on load
  const hash = location.hash.replace('#', '');
  if (hash === 'reports') {
    showSection('reports');
  } else {
    showSection('dashboard');
  }

  loadProfiles();
  loadCachedScans();

  // Custom filter dropdowns are wired via onclick in HTML — no wiring needed here

  // Wire search input
  const searchEl = document.getElementById('findingsSearch');
  if (searchEl) searchEl.addEventListener('input', e => onSearchInput(e.target.value));

  // Init sort indicators
  setSortCol('severity');
});

// Re-render charts on theme change
document.addEventListener('themechange', () => {
  if (!_lastScan) return;
  applyChartDefaults();
  renderRadar(_lastScan.frameworks || {}, _lastScan.services || {});
  renderSeverityChart(_lastScan.summary?.severity || {});
  renderFwGauges(_lastScan.frameworks || {});
  renderServiceCharts(_lastScan.services || {});
  renderWafrPillarChart(_lastScan.frameworks?.WAFR || {});
  renderTrendChart(_lastScan.profile);
  renderFindingTrendChart(_lastScan.profile);
  renderTopFailedChart(_lastScan.findings || []);
  renderRiskTreemap(_lastScan.findings || []);
  renderPassRateChart(_lastScan.services || {});
  renderHeatMap(_lastScan.findings || []);
  renderRemediationProgress(_lastScan.findings || []);
});
