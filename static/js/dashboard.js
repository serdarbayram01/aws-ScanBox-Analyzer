/* ============================================================
   AWS FinOps Dashboard — Main Dashboard Logic
   ============================================================ */

/* global Chart, t, formatUSD, formatNum, setLang, getTheme, escapeHtml, applyChartDefaults, getChartColors, PALETTE, ICONS */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let _profiles = [];
let _ssoSet = new Set();
let _selectedProfiles = new Set();
let _lastData = null;
let _historyChart = null;
let _breakdownChart = null;
let _historyPeriod = '12m';
let _profileSearch = '';
let _analyzeController = null; // AbortController for cancel

// ---------------------------------------------------------------------------
// Favorites persistence
// ---------------------------------------------------------------------------

const FAV_KEY = 'finops_favorites';

function loadFavorites() {
  try { return new Set(JSON.parse(localStorage.getItem(FAV_KEY)) || []); }
  catch { return new Set(); }
}

function saveFavorites(set) {
  localStorage.setItem(FAV_KEY, JSON.stringify([...set]));
}

let _favorites = loadFavorites();

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------

async function loadProfiles() {
  const container = document.getElementById('profileList');
  if (!container) return;
  container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:10px;grid-column:1/-1"><span class="spinner"></span> Loading...</div>`;

  try {
    const resp = await fetch('/finops/api/profiles');
    const data = await resp.json();
    const rawProfiles = data.profiles || [];
    _profiles = rawProfiles
      .map(p => (typeof p === 'string' ? p : p.name))
      .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
    _ssoSet = new Set(rawProfiles.filter(p => p.sso).map(p => p.name));

    renderProfileGrid();
    renderFavoritesBar();
    updateAnalyzeBtn();
    updateAnalyzeSelectedBtn();
    updateSelectedCount();

    // Auto-analyze favorites if any exist
    if (_favorites.size > 0) {
      analyzeFavorites();
    }
  } catch (err) {
    container.innerHTML = `<div style="color:var(--red);padding:10px">${escapeHtml(err.message)}</div>`;
  }
}

const ROWS_PER_COL = 10;

function _getFilteredProfiles() {
  if (!_profileSearch) return _profiles;
  const q = _profileSearch.toLowerCase();
  return _profiles.filter(p => p.toLowerCase().includes(q));
}

function renderProfileGrid() {
  const container = document.getElementById('profileList');
  if (!container) return;

  const countEl = document.getElementById('profileCount');
  if (countEl) countEl.textContent = _profiles.length;

  const filtered = _getFilteredProfiles();

  if (_profiles.length === 0) {
    container.innerHTML = `
      <div class="state-empty" style="grid-column:1/-1;padding:24px">
        <div class="state-empty-icon">${ICONS.inbox}</div>
        <div class="state-empty-text">${t('empty_no_profiles_title')}</div>
        <div class="state-empty-action"><code>aws configure --profile &lt;name&gt;</code></div>
      </div>`;
    return;
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div class="profile-no-match">${t('profile_no_match')}</div>`;
    return;
  }

  // Distribute profiles column-major: col 0 → [0..9], col 1 → [10..19], ...
  const numCols = Math.ceil(filtered.length / ROWS_PER_COL);

  const colsHtml = Array.from({ length: numCols }, (_, ci) => {
    const rowsHtml = filtered
      .slice(ci * ROWS_PER_COL, ci * ROWS_PER_COL + ROWS_PER_COL)
      .map((p, ri) => {
        const globalIdx = _profiles.indexOf(p);
        const selected = _selectedProfiles.has(p);
        const starred  = _favorites.has(p);
        const ssoLabel = _ssoSet.has(p) ? '<span class="sso-badge">SSO</span>' : '';
        return `
          <div class="profile-row ${selected ? 'selected' : ''}" data-idx="${globalIdx}" tabindex="0" role="button" aria-label="${escapeHtml(p)}">
            <div class="profile-row-check">${selected ? ICONS.check : ''}</div>
            <div class="profile-row-name" title="${escapeHtml(p)}">${escapeHtml(p)}</div>
            ${ssoLabel}
            <button class="star-btn ${starred ? 'starred' : ''}" data-star="1"
                    title="${starred ? 'Remove favorite' : 'Add to favorites'}"
                    aria-label="${starred ? 'Remove favorite' : 'Add to favorites'}">
              ${starred ? ICONS.starFilled : ICONS.starOutline}
            </button>
          </div>`;
      }).join('');
    return `<div class="profile-col">${rowsHtml}</div>`;
  }).join('');

  container.innerHTML = colsHtml;

  // Event delegation — whole row = select, star button = favorite
  container.onclick = null;
  container.onclick = (e) => {
    const row = e.target.closest('.profile-row[data-idx]');
    if (!row) return;
    const name = _profiles[parseInt(row.dataset.idx, 10)];
    if (!name) return;
    if (e.target.closest('[data-star]')) {
      toggleFavorite(name);
    } else {
      toggleProfile(name);
    }
  };

  // Keyboard support for profile rows
  container.onkeydown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const row = e.target.closest('.profile-row[data-idx]');
      if (!row) return;
      e.preventDefault();
      const name = _profiles[parseInt(row.dataset.idx, 10)];
      if (name) toggleProfile(name);
    }
  };
}

function renderFavoritesBar() {
  const container = document.getElementById('favoritesChips');
  if (!container) return;

  const favProfiles = [..._favorites].filter(f => _profiles.includes(f)).sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));

  if (favProfiles.length === 0) {
    container.innerHTML = `<span class="fav-empty">${t('fav_empty')}</span>`;
    return;
  }

  container.innerHTML = favProfiles.map((p, idx) => {
    const ssoSuffix = _ssoSet.has(p) ? ' <span class="fav-sso">SSO</span>' : '';
    return `<div class="fav-chip" data-fav-idx="${idx}" title="${escapeHtml(p)}">
      <span class="fav-chip-star">${ICONS.starFilled}</span>
      <span class="fav-chip-name">${escapeHtml(p)}${ssoSuffix}</span>
      <button class="fav-chip-remove" data-remove="1" title="Remove from favorites" aria-label="Remove ${escapeHtml(p)} from favorites">${ICONS.x}</button>
    </div>`;
  }).join('');

  container.onclick = null;
  container.onclick = (e) => {
    const btn = e.target.closest('[data-remove]');
    if (!btn) return;
    const chip = btn.closest('[data-fav-idx]');
    if (!chip) return;
    const name = favProfiles[parseInt(chip.dataset.favIdx, 10)];
    if (name) toggleFavorite(name);
  };
}

function toggleProfile(name) {
  if (_selectedProfiles.has(name)) {
    _selectedProfiles.delete(name);
  } else {
    _selectedProfiles.add(name);
  }
  renderProfileGrid();
  updateAnalyzeSelectedBtn();
  updateSelectedCount();
}

function toggleFavorite(name) {
  if (_favorites.has(name)) {
    _favorites.delete(name);
  } else {
    _favorites.add(name);
  }
  saveFavorites(_favorites);
  renderProfileGrid();
  renderFavoritesBar();
  updateAnalyzeBtn();
}

function favoriteSelected() {
  _selectedProfiles.forEach(p => _favorites.add(p));
  saveFavorites(_favorites);
  renderProfileGrid();
  renderFavoritesBar();
  updateAnalyzeBtn();
}

function toggleAllProfiles() {
  const section = document.getElementById('allProfilesSection');
  if (section) section.classList.toggle('open');
}

function selectAllProfiles() {
  _profiles.forEach(p => _selectedProfiles.add(p));
  renderProfileGrid();
  updateAnalyzeSelectedBtn();
  updateSelectedCount();
}

function clearProfiles() {
  _selectedProfiles.clear();
  renderProfileGrid();
  updateAnalyzeSelectedBtn();
  updateSelectedCount();
}

function updateAnalyzeBtn() {
  const btn = document.getElementById('analyzeBtn');
  if (!btn) return;
  const favCount = [..._favorites].filter(f => _profiles.includes(f)).length;
  btn.disabled = favCount === 0;
}

function updateAnalyzeSelectedBtn() {
  const btn = document.getElementById('analyzeSelectedBtn');
  if (btn) btn.disabled = _selectedProfiles.size === 0;
}

function updateSelectedCount() {
  const el = document.getElementById('selectedCount');
  if (el) el.textContent = _selectedProfiles.size > 0 ? `${_selectedProfiles.size} selected` : '';
}

// ---------------------------------------------------------------------------
// Profile Search
// ---------------------------------------------------------------------------

function onProfileSearch(value) {
  _profileSearch = value || '';
  renderProfileGrid();
  // Show/hide clear button
  const clearBtn = document.getElementById('profileSearchClear');
  if (clearBtn) clearBtn.style.display = _profileSearch ? 'flex' : 'none';
}

function clearProfileSearch() {
  const input = document.getElementById('profileSearchInput');
  if (input) input.value = '';
  _profileSearch = '';
  renderProfileGrid();
  const clearBtn = document.getElementById('profileSearchClear');
  if (clearBtn) clearBtn.style.display = 'none';
}


// ---------------------------------------------------------------------------
// Analyze
// ---------------------------------------------------------------------------

let _analyzeAborted = false;

async function _doAnalyze(profileList) {
  _analyzeAborted = false;
  _analyzeController = new AbortController();
  showInlineLoading(true);
  clearDashboard();
  try {
    const resp = await fetch('/finops/api/costs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profiles: profileList, months_back: 13 }),
      signal: _analyzeController.signal,
    });
    const data = await resp.json();
    _lastData = data;
    // Check for SSO/credential errors and show banner
    if (data.profiles) {
      showFinopsSsoBanner(data.profiles);
    }
    renderDashboard(data);
  } catch (err) {
    if (err.name === 'AbortError') {
      // User cancelled — do nothing
    } else {
      showError(escapeHtml(err.message));
    }
  } finally {
    _analyzeController = null;
    showInlineLoading(false);
  }
}

function cancelAnalyze() {
  if (_analyzeController) {
    _analyzeAborted = true;
    _analyzeController.abort();
  }
}

async function analyzeFavorites() {
  const favList = [..._favorites].filter(f => _profiles.includes(f));
  if (favList.length === 0) return;
  await _doAnalyze(favList);
}

async function analyzeSelected() {
  if (_selectedProfiles.size === 0) return;
  await _doAnalyze(Array.from(_selectedProfiles));
}

// ---------------------------------------------------------------------------
// Render Dashboard
// ---------------------------------------------------------------------------

function renderDashboard(data) {
  const { profiles, summary } = data;

  renderMetricCards(summary, profiles);
  renderAnomalies(profiles);
  renderHistoryChart(profiles, _historyPeriod);
  renderBreakdownTable(profiles);
}

// --- Metric Cards ---

function renderMetricCards(summary, profiles) {
  const el = document.getElementById('metricCards');
  if (!el) return;

  const successCount = profiles.filter(p => p.status === 'success').length;
  const savedByCredits = Math.abs(summary.total_credits || 0);

  el.innerHTML = `
    <div class="metric-card orange">
      <div class="metric-icon">${ICONS.dollar}</div>
      <div class="metric-label" data-i18n="metric_total">${t('metric_total')}</div>
      <div class="metric-value">${formatUSD(summary.total_historical)}</div>
      <div class="metric-sub">Historical usage (13 mo.)</div>
    </div>
    <div class="metric-card blue">
      <div class="metric-icon">${ICONS.calendar}</div>
      <div class="metric-label" data-i18n="metric_month">${t('metric_month')}</div>
      <div class="metric-value">${formatUSD(summary.total_current_spend)}</div>
      <div class="metric-sub">${new Date().toLocaleString('default', {month:'long', year:'numeric'})}</div>
    </div>
    <div class="metric-card yellow">
      <div class="metric-icon">${ICONS.trendingUp}</div>
      <div class="metric-label" data-i18n="metric_projected">${t('metric_projected')}</div>
      <div class="metric-value">${formatUSD(summary.total_projection)}</div>
      <div class="metric-sub">${t('forecast_based_on')} (daily avg.)</div>
    </div>
    <div class="metric-card green">
      <div class="metric-icon">${ICONS.tag}</div>
      <div class="metric-label" data-i18n="metric_credits">${t('metric_credits')}</div>
      <div class="metric-value" style="color:var(--green)">${formatUSD(savedByCredits)}</div>
      <div class="metric-sub">Applied credits</div>
    </div>
    <div class="metric-card blue">
      <div class="metric-icon">${ICONS.layers}</div>
      <div class="metric-label" data-i18n="metric_profiles">${t('metric_profiles')}</div>
      <div class="metric-value">${successCount}</div>
      <div class="metric-sub">of ${profiles.length} selected</div>
    </div>
  `;
}

// --- Anomaly Banners ---

function renderAnomalies(profiles) {
  const container = document.getElementById('anomalyContainer');
  if (!container) return;

  const allAnomalies = [];
  profiles.forEach(p => {
    if (p.status !== 'success') return;
    (p.anomalies || []).forEach(a => {
      allAnomalies.push({ ...a, profile: p.profile });
    });
  });

  if (allAnomalies.length === 0) {
    container.innerHTML = '';
    return;
  }

  allAnomalies.sort((a, b) => b.change_pct - a.change_pct);

  const wasOpen = document.getElementById('anomalySection')?.classList.contains('open');
  const openClass = wasOpen === false ? '' : ' open'; // default open on first render

  container.innerHTML = `
    <div class="anomaly-section${openClass}" id="anomalySection" style="margin-bottom:20px">
      <div class="anomaly-toggle" onclick="toggleAnomalies()">
        <div style="display:flex;align-items:center;gap:10px">
          <span class="chart-title" style="margin:0" data-i18n="anomaly_title">${t('anomaly_title')}</span>
          <span class="anomaly-count">${allAnomalies.length}</span>
        </div>
        <svg class="anomaly-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="anomaly-body">
        <div style="padding:0 20px 4px;font-size:12px;color:var(--text-muted)">${allAnomalies.length} ${t('anomaly_detected')}</div>
        <div class="alert-list" style="padding:0 20px 16px">
          ${allAnomalies.map(a => {
            const typeLabel = a.type === 'new_spend' ? t('anomaly_new_spend') : t('anomaly_spike');
            return `
            <div class="alert-item alert-${escapeHtml(a.severity)}">
              <div class="alert-icon">${a.severity === 'critical' ? ICONS.alertCircle : ICONS.alertTriangle}</div>
              <div class="alert-text">
                <div class="alert-title">${escapeHtml(a.profile)} — ${escapeHtml(a.month)} <span style="font-size:10px;color:var(--text-muted)">(${escapeHtml(typeLabel)})</span></div>
                <div class="alert-desc">
                  +${formatNum(a.change_pct)}% ${t('anomaly_vs')} ${escapeHtml(a.prev_month)}
                  (${formatUSD(a.prev_cost)} → ${formatUSD(a.curr_cost)})
                </div>
              </div>
            </div>`;
          }).join('')}
        </div>
      </div>
    </div>
  `;
}

function toggleAnomalies() {
  const section = document.getElementById('anomalySection');
  if (section) section.classList.toggle('open');
}

// --- Cost History Chart ---

let _highlightedDatasetIdx = -1;

function _setChartHighlight(canvas, datasetIndex, dataset) {
  const container = canvas.parentElement;
  let el = container.querySelector('.chart-highlight');

  // Toggle off if same dataset
  if (datasetIndex === _highlightedDatasetIdx) {
    _highlightedDatasetIdx = -1;
    if (el) el.style.display = 'none';
    return;
  }

  _highlightedDatasetIdx = datasetIndex;
  const color = dataset.borderColor;

  if (!el) {
    el = document.createElement('div');
    el.className = 'chart-highlight';
    container.appendChild(el);
  }

  el.innerHTML = `
    <span class="chart-hl-dot" style="background:${escapeHtml(color)};box-shadow:0 0 6px ${escapeHtml(color)}88"></span>
    <span class="chart-hl-name">${escapeHtml(dataset.label)}</span>
    <button class="chart-hl-close" title="Clear" aria-label="Clear highlight">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>`;
  el.style.setProperty('--hl-color', color);
  el.style.display = 'flex';

  el.querySelector('.chart-hl-close').onclick = (e) => {
    e.stopPropagation();
    el.style.display = 'none';
    _highlightedDatasetIdx = -1;
  };
}

function renderHistoryChart(profiles, period) {
  const canvas = document.getElementById('historyChart');
  if (!canvas) return;
  applyChartDefaults();
  const cc = getChartColors();

  // Clear any existing highlight when chart is re-rendered
  _highlightedDatasetIdx = -1;
  const oldHl = canvas.parentElement.querySelector('.chart-highlight');
  if (oldHl) oldHl.remove();

  const successProfiles = profiles.filter(p => p.status === 'success');
  if (!successProfiles.length) return;

  // Collect all months from monthly_totals
  const allMonths = [...new Set(
    successProfiles.flatMap(p => Object.keys(p.monthly_totals || {}))
  )].sort();

  // Filter by period
  const limit = period === '12m' ? 12 : period === '6m' ? 6 : period === '3m' ? 3 : allMonths.length;
  const months = allMonths.slice(-limit);

  const datasets = successProfiles.map((p, i) => ({
    label: p.profile,
    data: months.map(m => p.monthly_totals[m] || 0),
    borderColor: PALETTE[i % PALETTE.length],
    backgroundColor: PALETTE[i % PALETTE.length] + '18',
    fill: successProfiles.length === 1,
    tension: 0.4,
    pointRadius: 4,
    pointHoverRadius: 6,
    borderWidth: 2,
  }));

  if (_historyChart) _historyChart.destroy();
  _historyChart = new Chart(canvas, {
    type: 'line',
    data: { labels: months, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      onClick: (event, elements, chart) => {
        const nearest = chart.getElementsAtEventForMode(
          event.native, 'nearest', { intersect: false }, false
        );
        if (!nearest.length) {
          _highlightedDatasetIdx = -1;
          const hl = canvas.parentElement.querySelector('.chart-highlight');
          if (hl) hl.style.display = 'none';
          return;
        }
        _setChartHighlight(canvas, nearest[0].datasetIndex, chart.data.datasets[nearest[0].datasetIndex]);
      },
      plugins: {
        legend: {
          display: successProfiles.length > 1,
          labels: { color: cc.text, usePointStyle: true, pointStyleWidth: 8 },
        },
        tooltip: {
          enabled: true,
          backgroundColor: cc.tooltip,
          borderColor: cc.border,
          borderWidth: 1,
          titleColor: getTheme() !== 'light' ? '#e2e8f0' : '#0f172a',
          bodyColor: cc.text,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${formatUSD(ctx.raw)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: cc.grid },
          ticks: { color: cc.text, maxRotation: 0 },
        },
        y: {
          grid: { color: cc.grid },
          ticks: {
            color: cc.text,
            callback: v => '$' + v.toLocaleString(),
          },
          beginAtZero: true,
        },
      },
    },
  });

  // Make canvas show pointer cursor on hover
  canvas.style.cursor = 'pointer';
}

// --- Monthly Breakdown Table ---

function renderBreakdownTable(profiles) {
  const container = document.getElementById('breakdownContainer');
  if (!container) return;

  const successProfiles = profiles.filter(p => p.status === 'success');
  if (!successProfiles.length) { container.innerHTML = ''; return; }

  const allMonths = [...new Set(
    successProfiles.flatMap(p => Object.keys(p.monthly_totals || {}))
  )].sort().slice(-12);

  const thead = `
    <thead>
      <tr>
        <th data-i18n="col_profile">${t('col_profile')}</th>
        ${allMonths.map(m => `<th class="num">${escapeHtml(m)}</th>`).join('')}
        <th class="num" data-i18n="col_total">${t('col_total')}</th>
        <th data-i18n="col_trend">${t('col_trend')}</th>
      </tr>
    </thead>`;

  const tbody = successProfiles.map(p => {
    const vals = allMonths.map(m => p.monthly_totals[m] || 0);
    const total = vals.reduce((a, b) => a + b, 0);
    const last = vals[vals.length - 1] || 0;
    const prev = vals[vals.length - 2] || 0;
    let trendHtml = '<span class="trend trend-flat">—</span>';
    if (prev > 0) {
      const pct = ((last - prev) / prev) * 100;
      if (pct > 5) trendHtml = `<span class="trend trend-up">${formatNum(pct)}%</span>`;
      else if (pct < -5) trendHtml = `<span class="trend trend-down">${formatNum(Math.abs(pct))}%</span>`;
    } else if (prev === 0 && last > 0) {
      trendHtml = `<span class="trend trend-up">new</span>`;
    }

    const profileSafe = encodeURIComponent(p.profile);
    return `
      <tr class="clickable-row" onclick="goToDetail('${profileSafe}')">
        <td><strong>${escapeHtml(p.profile)}</strong></td>
        ${vals.map(v => `<td class="num">${v > 0 ? formatUSD(v) : '<span style="color:var(--text-muted)">—</span>'}</td>`).join('')}
        <td class="num"><strong>${formatUSD(total)}</strong></td>
        <td>${trendHtml}</td>
      </tr>`;
  }).join('');

  // Error rows — with SSO command hint for auth errors
  const errRows = profiles.filter(p => p.status === 'error').map(p => {
    const isSso = _isSsoError(p.error);
    const ssoHint = isSso
      ? ` <code style="background:rgba(0,0,0,.2);padding:1px 6px;border-radius:3px;font-size:10px;margin-left:6px;user-select:all">aws sso login --profile ${escapeHtml(p.profile)}</code>`
      : '';
    return `<tr>
      <td>${escapeHtml(p.profile)}</td>
      <td colspan="${allMonths.length + 2}" style="color:var(--red);font-size:12px">${escapeHtml(p.error)}${ssoHint}</td>
    </tr>`;
  }).join('');

  container.innerHTML = `
    <div class="table-card">
      <div class="table-card-header">
        <div>
          <div class="table-card-title" data-i18n="chart_breakdown">${t('chart_breakdown')}</div>
        </div>
        <button class="btn btn-outline btn-sm" id="savePerProfileBtn" onclick="savePerProfileReports(this)" title="Save reports for each profile" style="display:inline-flex;align-items:center;gap:5px">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          ${t('btn_save_reports') || 'Save Reports'}
        </button>
      </div>
      <div style="overflow-x:auto">
        <table class="data-table">
          ${thead}
          <tbody>${tbody}${errRows}</tbody>
        </table>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Period Buttons
// ---------------------------------------------------------------------------

function setPeriod(period) {
  _historyPeriod = period;
  document.querySelectorAll('.period-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.period === period);
  });
  if (_lastData) renderHistoryChart(_lastData.profiles, period);
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

function goToDetail(profile) {
  // profile may already be encoded from the onclick attribute
  const decoded = decodeURIComponent(profile);
  window.location.href = `/finops/detail?profile=${encodeURIComponent(decoded)}`;
}

// ---------------------------------------------------------------------------
// Export / Reports
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Reports — SecOps-style grouped list
// ---------------------------------------------------------------------------

let _finopsReportGroups = {};

async function _autoGenerateFinopsReports(profileList) {
  if (!profileList || !profileList.length) return;
  try {
    await fetch('/finops/api/reports/generate_per_profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profiles: profileList, months_back: 13 }),
    });
    loadReportsList();
  } catch (_) { /* non-critical */ }
}

async function finopsGenerateAll(btn) {
  const profiles = _lastData ? _lastData.profiles.filter(p => p.status === 'success').map(p => p.profile) : Array.from(_selectedProfiles);
  if (!profiles.length) return;
  if (btn) { btn.disabled = true; btn.style.opacity = '.6'; }
  try {
    await fetch('/finops/api/reports/generate_per_profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profiles, months_back: 13 }),
    });
    loadReportsList();
  } catch (_) { /* silent */ }
  finally { if (btn) { btn.disabled = false; btn.style.opacity = '1'; } }
}

async function savePerProfileReports(btn) {
  const profiles = _lastData ? _lastData.profiles.filter(p => p.status === 'success').map(p => p.profile) : Array.from(_selectedProfiles);
  if (!profiles.length) return;
  if (btn) { btn.disabled = true; btn.style.opacity = '.6'; btn.innerHTML = '<span class="spinner" style="width:12px;height:12px"></span> Saving...'; }
  try {
    await fetch('/finops/api/reports/generate_per_profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profiles, months_back: 13 }),
    });
    loadReportsList();
    if (btn) btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Saved!';
    setTimeout(() => {
      if (btn) btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> ' + (t('btn_save_reports') || 'Save Reports');
    }, 2000);
  } catch (_) { /* silent */ }
  finally { if (btn) { btn.disabled = false; btn.style.opacity = '1'; } }
}

async function loadReportsList() {
  try {
    const resp = await fetch('/finops/api/reports/list');
    const data = await resp.json();
    const reports = data.reports || [];

    const tbody = document.getElementById('finopsReportBody');
    const table = document.getElementById('finopsReportTable');
    const empty = document.getElementById('finopsReportEmpty');
    const selAll = document.getElementById('finopsReportSelectAll');
    if (!tbody || !table || !empty) return;

    if (!reports.length) {
      table.style.display = 'none'; empty.style.display = 'block';
      _finopsReportGroups = {};
      return;
    }

    // Group by base key: aws_finops_{profile?}_YYYYMMDD_HHMMSS or aws_finops_YYYYMMDD_HHMMSS
    const groups = {};
    for (const r of reports) {
      const m = r.filename.match(/^(aws_finops_(?:[\w\-]+_)?\d{8}_\d{6})(?:_services)?\.(html|csv|pdf)$/);
      if (!m) continue;
      const base = m[1];
      const ftype = r.filename.includes('_services') ? 'csv_svc' : m[2];
      if (!groups[base]) groups[base] = { base, mtime: r.mtime || 0, files: {}, profile: '' };
      groups[base].files[ftype] = r;
      if ((r.mtime || 0) > groups[base].mtime) groups[base].mtime = r.mtime;
    }

    // Extract profile name from base key
    for (const [key, g] of Object.entries(groups)) {
      const pm = key.match(/^aws_finops_(.+)_\d{8}_\d{6}$/);
      g.profile = pm ? pm[1] : '';
    }

    _finopsReportGroups = groups;
    const sorted = Object.values(groups).sort((a, b) => b.mtime - a.mtime);
    if (!sorted.length) { table.style.display = 'none'; empty.style.display = 'block'; return; }

    const fmtDate = ts => {
      if (!ts) return '—';
      return new Date(ts * 1000).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      });
    };

    const fmtBadge = (label, color, file, target) => file
      ? `<a href="/finops/reports/download/${encodeURIComponent(file.filename)}" ${target === '_blank' ? 'target="_blank" rel="noopener"' : `download="${escapeHtml(file.filename)}"`}
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

      return `<tr class="report-row">
        <td style="text-align:center;width:36px">
          <input type="checkbox" class="finops-report-check" data-base="${safe}"
                 style="accent-color:var(--accent);width:14px;height:14px;cursor:pointer"
                 onchange="finopsCheckChange()">
        </td>
        <td style="font-size:12px">
          <div style="font-weight:600;color:var(--text-primary)">${fmtDate(g.mtime)}</div>
          <div style="font-size:11px;color:var(--accent);margin-top:2px;font-weight:600">${g.profile ? escapeHtml(g.profile) : 'All Profiles'}</div>
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:nowrap">
            ${fmtBadge('HTML', '#3b82f6', html, '_blank')}
            ${fmtBadge('CSV', '#10b981', csv)}
            ${fmtBadge('PDF', '#f97316', pdf)}
          </div>
        </td>
        <td style="text-align:center;width:40px">
          <button class="report-delete-btn" onclick="finopsDeleteGroup('${safe}')" title="Delete">
            ${delSvg}
          </button>
        </td>
      </tr>`;
    }).join('');

    if (selAll) selAll.checked = false;
    table.style.display = '';
    empty.style.display = 'none';
    _finopsUpdateDeleteBtn();
  } catch (err) { /* silent */ }
}

function finopsToggleAll(masterCb) {
  document.querySelectorAll('.finops-report-check').forEach(cb => { cb.checked = masterCb.checked; });
  _finopsUpdateDeleteBtn();
}

function finopsCheckChange() {
  const all     = document.querySelectorAll('.finops-report-check');
  const checked = document.querySelectorAll('.finops-report-check:checked');
  const master  = document.getElementById('finopsReportSelectAll');
  if (master) {
    master.indeterminate = checked.length > 0 && checked.length < all.length;
    master.checked       = checked.length === all.length && all.length > 0;
  }
  _finopsUpdateDeleteBtn();
}

function _finopsUpdateDeleteBtn() {
  const n   = document.querySelectorAll('.finops-report-check:checked').length;
  const btn = document.getElementById('finopsDeleteSelectedBtn');
  if (btn) btn.style.display = n >= 1 ? 'inline-flex' : 'none';
}

async function finopsDeleteGroup(base) {
  try {
    const resp = await fetch('/finops/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases: [base] }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportsList();
  } catch (_) { /* silent */ }
}

async function finopsDeleteSelected() {
  const checked = [...document.querySelectorAll('.finops-report-check:checked')];
  if (checked.length < 1) return;
  const bases = checked.map(cb => cb.dataset.base).filter(Boolean);
  if (!bases.length) return;
  try {
    const resp = await fetch('/finops/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportsList();
  } catch (_) { /* silent */ }
}

// ---------------------------------------------------------------------------
// Loading / State helpers
// ---------------------------------------------------------------------------

function showInlineLoading(show) {
  const el = document.getElementById('analyzeLoading');
  if (!el) return;

  if (show) {
    el.style.display = 'block';
    el.innerHTML = `
      <div class="inline-loading-banner">
        <span class="spinner" style="width:16px;height:16px;border-width:2px"></span>
        <span>${t('loading_profiles')}</span>
        <button class="inline-loading-cancel" onclick="cancelAnalyze()">${t('loading_cancel')}</button>
      </div>`;
    const b1 = document.getElementById('analyzeBtn');
    if (b1) b1.disabled = true;
    const b2 = document.getElementById('analyzeSelectedBtn');
    if (b2) b2.disabled = true;
  } else {
    el.style.display = 'none';
    el.innerHTML = '';
    updateAnalyzeBtn();
    updateAnalyzeSelectedBtn();
  }
}

function showError(msg) {
  const el = document.getElementById('metricCards');
  if (el) el.innerHTML = `
    <div class="metric-card" style="grid-column:1/-1;text-align:center;padding:30px">
      <div class="state-empty">
        <div class="state-empty-icon">${ICONS.warning}</div>
        <div class="state-empty-text">${escapeHtml(msg)}</div>
      </div>
    </div>`;
}

function clearDashboard() {
  ['metricCards', 'anomalyContainer', 'breakdownContainer'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
  hideFinopsSsoBanner();
}


// ---------------------------------------------------------------------------
// SSO / Credential Banner (FinOps)
// ---------------------------------------------------------------------------

function _isSsoError(errorMsg) {
  if (!errorMsg) return false;
  const m = errorMsg.toLowerCase();
  return m.includes('sso') || m.includes('expired') || m.includes('token') ||
         m.includes('unauthorizedsso') || m.includes('credential');
}

function showFinopsSsoBanner(profiles) {
  const banner = document.getElementById('finopsSsoBanner');
  const msg    = document.getElementById('finopsSsoBannerMsg');
  if (!banner || !msg) return;

  const ssoErrors = profiles.filter(p => p.status === 'error' && _isSsoError(p.error));
  if (!ssoErrors.length) { hideFinopsSsoBanner(); return; }

  const commands = ssoErrors.map(p => `aws sso login --profile ${p.profile}`);
  const uniqueCmds = [...new Set(commands)];

  const ssoMsg = t('secops_sso_expired') || 'SSO session expired for';
  const ssoRun = t('secops_sso_run') || 'Run:';
  const copyLabel = t('secops_copy') || 'Copy';
  const profileNames = ssoErrors.map(p => `<b>${escapeHtml(p.profile)}</b>`).join(', ');

  let cmdsHtml = uniqueCmds.map((cmd, i) =>
    `<div style="display:flex;align-items:center;gap:6px;margin-top:4px">
      <code class="finops-sso-cmd" style="background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.15);padding:3px 10px;border-radius:4px;font-size:11px;font-family:monospace;user-select:all">${escapeHtml(cmd)}</code>
      <button onclick="copyFinopsSsoCmd(this,'${escapeHtml(cmd)}')" style="padding:3px 10px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:4px;color:#f5c6c6;font-size:11px;cursor:pointer;white-space:nowrap">${copyLabel}</button>
    </div>`
  ).join('');

  msg.innerHTML = `<div>
    <span>${ssoMsg} ${profileNames}. ${ssoRun}</span>
    ${cmdsHtml}
  </div>`;

  banner.style.display = 'flex';
}

function hideFinopsSsoBanner() {
  const banner = document.getElementById('finopsSsoBanner');
  if (banner) banner.style.display = 'none';
}

function copyFinopsSsoCmd(btn, cmd) {
  navigator.clipboard.writeText(cmd).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✓ ' + (t('secops_copied') || 'Copied');
    setTimeout(() => { btn.textContent = orig; }, 2000);
  }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  // Show/hide sections based on hash
  const hash = location.hash || '#dashboard';
  showSection(hash.replace('#', ''));

  document.querySelectorAll('.nav-item').forEach(link => {
    link.addEventListener('click', () => {
      const section = link.dataset.section;
      if (section) showSection(section);
    });
  });

  loadProfiles();
});

function showSection(name) {
  document.querySelectorAll('.page-section').forEach(s => {
    s.style.display = s.id === `section-${name}` ? 'block' : 'none';
  });
  document.querySelectorAll('.nav-item').forEach(link => {
    link.classList.toggle('active', link.dataset.section === name);
  });
  location.hash = '#' + name;

  if (name === 'reports') {
    loadReportsList();
  }
}

// Re-render on theme/lang change
document.addEventListener('themechange', () => {
  if (_lastData) {
    renderHistoryChart(_lastData.profiles, _historyPeriod);
  }
});

document.addEventListener('langchange', () => {
  if (_lastData) renderDashboard(_lastData);
});
