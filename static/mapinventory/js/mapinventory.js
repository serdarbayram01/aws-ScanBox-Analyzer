/* ============================================================
   Map Inventory — Dashboard Logic
   Completely independent from FinOps & SecOps modules.
   ============================================================ */

/* global Chart, t, ICONS, formatNum, getTheme */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let _profiles = [];
let _profileSearch = '';
let _ssoSet = new Set();
let _selectedProfiles = new Set();
let _scanData = {};          // profile → scan results
let _activeProfile = null;   // currently displayed profile
let _detailService = null;   // currently shown service detail
let _allResources = [];      // flattened resources for active profile
let _filteredResources = []; // after filters
let _detailResources = [];   // resources for detail panel
let _detailFiltered = [];
let _detailPage = 0;
const DETAIL_PAGE_SIZE = 50;
let _svcSortCol = 'count';
let _svcSortAsc = false;
let _pollTimer = null;
let _charts = {};

// Chart colors — provided by i18n.js (getChartColors, applyChartDefaults, PALETTE)

function formatDuration(seconds) {
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem > 0 ? `${m}m ${rem}s` : `${m}m`;
}

// ---------------------------------------------------------------------------
// Favorites
// ---------------------------------------------------------------------------
const FAV_KEY = 'mapinventory_favorites';
function loadFavorites() {
  try { return new Set(JSON.parse(localStorage.getItem(FAV_KEY)) || []); }
  catch { return new Set(); }
}
function saveFavorites(s) { localStorage.setItem(FAV_KEY, JSON.stringify([...s])); }
let _favorites = loadFavorites();

function toggleFavorite(name) {
  if (_favorites.has(name)) _favorites.delete(name); else _favorites.add(name);
  saveFavorites(_favorites);
  renderProfileGrid();
  renderFavoritesBar();
}

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------
const ROWS_PER_COL = 10;

async function loadProfiles() {
  const container = document.getElementById('profileList');
  if (!container) return;
  container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:10px;grid-column:1/-1"><span class="spinner"></span> Loading...</div>`;
  try {
    const resp = await fetch('/mapinventory/api/profiles');
    const data = await resp.json();
    const raw = data.profiles || [];
    _profiles = raw.map(p => typeof p === 'string' ? p : p.name)
                    .sort((a,b) => a.toLowerCase().localeCompare(b.toLowerCase()));
    _ssoSet = new Set(raw.filter(p => p.sso).map(p => p.name));
    renderProfileGrid();
    updateScanBtn();
  } catch(e) {
    container.innerHTML = `<div style="color:var(--red);padding:10px">${e.message}</div>`;
  }
}

function getFilteredProfiles() {
  if (!_profileSearch) return _profiles;
  const q = _profileSearch.toLowerCase();
  return _profiles.filter(p => p.toLowerCase().includes(q));
}

function onMapinvProfileSearch(value) {
  _profileSearch = value || '';
  renderProfileGrid();
  const clearBtn = document.getElementById('mapinvProfileSearchClear');
  if (clearBtn) clearBtn.style.display = _profileSearch ? 'flex' : 'none';
}

function clearMapinvProfileSearch() {
  const input = document.getElementById('mapinvProfileSearchInput');
  if (input) input.value = '';
  _profileSearch = '';
  renderProfileGrid();
  const clearBtn = document.getElementById('mapinvProfileSearchClear');
  if (clearBtn) clearBtn.style.display = 'none';
}

function renderProfileGrid() {
  const container = document.getElementById('profileList');
  if (!container) return;

  const filtered = getFilteredProfiles();

  if (!_profiles.length) {
    container.innerHTML = `<div style="color:var(--text-muted);font-size:13px">${t('profile_none_found') || 'No profiles found'}</div>`;
    return;
  }

  if (_profileSearch && !filtered.length) {
    container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:10px;grid-column:1/-1">${t('profile_no_match') || 'No matching profiles found'}</div>`;
    return;
  }

  const countEl = document.getElementById('profileCount');
  if (countEl) countEl.textContent = _profiles.length;

  const numCols = Math.ceil(filtered.length / ROWS_PER_COL);
  const colsHtml = Array.from({length: numCols}, (_, ci) => {
    const rows = filtered.slice(ci*ROWS_PER_COL, ci*ROWS_PER_COL+ROWS_PER_COL)
      .map((p, ri) => {
        const idx = _profiles.indexOf(p);
        const sel = _selectedProfiles.has(p);
        const sso = _ssoSet.has(p) ? '<span class="sso-badge">SSO</span>' : '';
        return `<div class="profile-row${sel?' selected':''}" data-idx="${idx}">
          <div class="profile-row-check">${sel ? ICONS.check : ''}</div>
          <div class="profile-row-name" title="${p}">${p}</div>
          ${sso}
        </div>`;
      }).join('');
    return `<div class="profile-col">${rows}</div>`;
  }).join('');

  container.innerHTML = colsHtml;
  container.onclick = (e) => {
    const row = e.target.closest('.profile-row[data-idx]');
    if (!row) return;
    const name = _profiles[parseInt(row.dataset.idx, 10)];
    if (_selectedProfiles.has(name)) _selectedProfiles.delete(name);
    else _selectedProfiles.add(name);
    renderProfileGrid();
    updateScanBtn();
    updateSelectedLabel();
    if (_selectedProfiles.size === 1) loadRegions([..._selectedProfiles][0]);
  };
}

function renderFavoritesBar() {
  const container = document.getElementById('favoritesChips');
  const analyzeBtn = document.getElementById('analyzeFavBtn');
  if (!container) return;

  const favs = [..._favorites].filter(f => _profiles.includes(f));
  if (analyzeBtn) analyzeBtn.disabled = favs.length === 0;

  if (!favs.length) {
    container.innerHTML = `<span class="fav-empty" data-i18n="fav_empty">${t('fav_empty') || 'No favorites yet — star a profile below'}</span>`;
    return;
  }
  container.innerHTML = favs.map((f, i) => {
    const sso = _ssoSet.has(f) ? ' <span class="sso-badge" style="font-size:9px;vertical-align:middle">SSO</span>' : '';
    return `<div class="fav-chip" data-fav-idx="${i}" title="${f}">
      <span class="fav-chip-star">${ICONS.starFilled}</span>
      <span class="fav-chip-name">${f}${sso}</span>
      <button class="fav-chip-remove" data-remove="1">${ICONS.x || '&times;'}</button>
    </div>`;
  }).join('');

  container.onclick = (e) => {
    const btn = e.target.closest('[data-remove]');
    if (!btn) return;
    const chip = btn.closest('[data-fav-idx]');
    if (chip) {
      const name = favs[parseInt(chip.dataset.favIdx, 10)];
      toggleFavorite(name);
    }
  };
}

function selectAllProfiles() {
  _profiles.forEach(p => _selectedProfiles.add(p));
  renderProfileGrid();
  updateScanBtn();
  updateSelectedLabel();
}

function clearProfiles() {
  _selectedProfiles.clear();
  renderProfileGrid();
  updateScanBtn();
  updateSelectedLabel();
}

function favoriteSelected() {
  for (const p of _selectedProfiles) _favorites.add(p);
  saveFavorites(_favorites);
  renderProfileGrid();
  renderFavoritesBar();
}

function analyzeFavorites() {
  _selectedProfiles = new Set([..._favorites].filter(f => _profiles.includes(f)));
  renderProfileGrid();
  renderFavoritesBar();
  updateScanBtn();
  updateSelectedLabel();
  if (_selectedProfiles.size > 0) startScan();
}

function updateScanBtn() {
  const btn = document.getElementById('scanBtn');
  if (btn) btn.disabled = _selectedProfiles.size === 0;
}

function updateSelectedLabel() {
  const el = document.getElementById('selectedProfileLabel');
  if (el) el.textContent = _selectedProfiles.size > 0 ? `${_selectedProfiles.size} selected` : '';
}

// ---------------------------------------------------------------------------
// Regions
// ---------------------------------------------------------------------------
let _availableRegions = [];
let _selectedRegions = [];

async function loadRegions(profile) {
  const content = document.getElementById('regionDropdownContent');
  if (!content) return;
  content.innerHTML = '<span class="spinner" style="padding:8px"></span>';
  hideSsoBanner();
  try {
    const resp = await fetch(`/mapinventory/api/regions?profile=${encodeURIComponent(profile)}`);
    const data = await resp.json();
    if (data.error && _isSsoError(data.error)) {
      showSsoBanner(profile, data.error);
      _availableRegions = [];
      renderRegionDropdown();
      return;
    }
    _availableRegions = data.regions || [];
    renderRegionDropdown();
  } catch(e) {
    if (_isSsoError(e.message)) {
      showSsoBanner(profile, e.message);
    }
    content.innerHTML = `<span style="color:var(--red);padding:8px;font-size:11px">${e.message}</span>`;
  }
}

// ---------------------------------------------------------------------------
// SSO / Credential Banner
// ---------------------------------------------------------------------------
function _isSsoError(msg) {
  if (!msg) return false;
  const m = msg.toLowerCase();
  return m.includes('sso') || m.includes('expired') || m.includes('token') ||
         m.includes('unauthorizedsso') || m.includes('credential');
}

function showSsoBanner(profile, error) {
  const banner = document.getElementById('ssoBanner');
  const msg = document.getElementById('ssoBannerMsg');
  if (!banner || !msg) return;
  const cmd = `aws sso login --profile ${profile}`;
  const esc = typeof escapeHtml === 'function' ? escapeHtml : s => s.replace(/</g,'&lt;').replace(/>/g,'&gt;');
  msg.innerHTML = `<span>${t('secops_sso_expired') || 'SSO session expired for'} <b>${esc(profile)}</b>. ${t('secops_sso_run') || 'Run:'}</span>
    <code id="mapSsoCmd" style="background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.15);padding:3px 10px;border-radius:4px;font-size:11px;font-family:monospace;user-select:all;margin:0 6px">${esc(cmd)}</code>
    <button onclick="copyMapSsoCmd()" id="mapSsoCopyBtn" style="padding:3px 10px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:4px;color:#f5c6c6;font-size:11px;cursor:pointer;white-space:nowrap">${t('secops_copy') || 'Copy'}</button>`;
  banner.style.display = 'flex';
}

function hideSsoBanner() {
  const banner = document.getElementById('ssoBanner');
  if (banner) banner.style.display = 'none';
}

function copyMapSsoCmd() {
  const cmd = document.getElementById('mapSsoCmd');
  const btn = document.getElementById('mapSsoCopyBtn');
  if (!cmd) return;
  navigator.clipboard.writeText(cmd.textContent).then(() => {
    if (btn) { btn.textContent = '✓ ' + (t('secops_copied') || 'Copied'); setTimeout(() => { btn.textContent = t('secops_copy') || 'Copy'; }, 2000); }
  }).catch(() => {});
}

function renderRegionDropdown() {
  const content = document.getElementById('regionDropdownContent');
  if (!content) return;
  if (!_availableRegions.length) {
    content.innerHTML = '<span style="color:var(--text-muted);font-size:12px;padding:8px;display:block">No regions found</span>';
    return;
  }
  const sortedRegions = [..._availableRegions].sort();
  let html = `
    <div style="padding:8px 10px 6px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg-card);z-index:1">
      <input type="text" id="regionSearch" placeholder="Search regions..." oninput="filterRegionDropdown(this.value)"
        onclick="event.stopPropagation()"
        style="width:100%;box-sizing:border-box;padding:5px 9px;border:1px solid var(--border);border-radius:5px;
               background:var(--bg-base);color:var(--text-primary);font-size:12px;outline:none">
    </div>
    <div id="regionList" style="display:flex;flex-direction:column;max-height:320px;overflow-y:auto">`;
  for (const r of sortedRegions) {
    const checked = _selectedRegions.includes(r);
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

function onRegionChange() {
  const checked = [...document.querySelectorAll('.region-cb:checked')].map(cb => cb.value);
  if (checked.length === _availableRegions.length) {
    _selectedRegions = [];
  } else {
    _selectedRegions = checked;
  }
  updateRegionLabel();
}

function updateRegionLabel() {
  const el = document.getElementById('regionPickerLabel');
  if (!el) return;
  if (_selectedRegions.length === 0) {
    el.textContent = t('mapinv_all_regions') || 'All Regions';
  } else {
    el.textContent = `${_selectedRegions.length} Region${_selectedRegions.length > 1 ? 's' : ''}`;
  }
}

function toggleRegionDropdown() {
  const dd = document.getElementById('regionDropdown');
  if (!dd) return;
  const opening = dd.style.display === 'none' || dd.style.display === '';
  if (opening) {
    const search = document.getElementById('regionSearch');
    if (search) { search.value = ''; filterRegionDropdown(''); }
  }
  dd.style.display = opening ? 'block' : 'none';
}

// Close dropdowns on outside click
document.addEventListener('click', (e) => {
  const dd = document.getElementById('regionDropdown');
  const picker = document.getElementById('regionPicker');
  if (dd && picker && !picker.contains(e.target)) {
    dd.style.display = 'none';
  }
  const sd = document.getElementById('serviceDropdown');
  const sp = document.getElementById('servicePicker');
  if (sd && sp && !sp.contains(e.target)) {
    sd.style.display = 'none';
    _serviceSearch = '';
  }
});

// ---------------------------------------------------------------------------
// Service Picker (Quick Scan)
// ---------------------------------------------------------------------------
const QUICK_SCAN_SERVICES = [
  'iam', 's3', 'ec2', 'vpc', 'rds', 'lambda', 'ecs', 'eks', 'dynamodb',
  'sqs', 'sns', 'elb', 'elbv2', 'cloudfront', 'route53', 'kms',
  'ecr', 'acm', 'secretsmanager', 'cloudwatch',
];

let _allServices = [];
let _selectedServices = [...QUICK_SCAN_SERVICES]; // default: quick scan
let _serviceSearch = '';
let _serviceMode = 'quick'; // 'all' | 'quick' | 'custom'

async function loadServices() {
  try {
    const resp = await fetch('/mapinventory/api/services');
    const data = await resp.json();
    _allServices = data.services || [];
  } catch(e) { /* ignore */ }
}

function toggleServiceDropdown() {
  const dd = document.getElementById('serviceDropdown');
  if (!dd) return;
  const opening = dd.style.display === 'none';
  dd.style.display = opening ? 'block' : 'none';
  if (opening) {
    _serviceSearch = '';
    renderServiceDropdown();
  }
}

function setServiceMode(mode) {
  if (mode === 'clear') {
    _selectedServices = [];
    _serviceMode = 'custom';
  } else {
    _serviceMode = mode;
    if (mode === 'all') {
      _selectedServices = [];
    } else if (mode === 'quick') {
      _selectedServices = [...QUICK_SCAN_SERVICES];
    }
  }
  updateServiceLabel();
  renderServiceDropdown();
}

function toggleServiceSelect(svc, checked) {
  if (checked) {
    if (!_selectedServices.includes(svc)) _selectedServices.push(svc);
  } else {
    _selectedServices = _selectedServices.filter(s => s !== svc);
  }
  // Determine mode
  if (_selectedServices.length === 0) {
    _serviceMode = 'all';
  } else if (_selectedServices.length === QUICK_SCAN_SERVICES.length &&
    QUICK_SCAN_SERVICES.every(s => _selectedServices.includes(s)) &&
    _selectedServices.every(s => QUICK_SCAN_SERVICES.includes(s))) {
    _serviceMode = 'quick';
  } else {
    _serviceMode = 'custom';
  }
  updateServiceLabel();
}

function updateServiceLabel() {
  const el = document.getElementById('servicePickerLabel');
  if (!el) return;
  if (_serviceMode === 'all') el.textContent = `All Services (${_allServices.length})`;
  else if (_serviceMode === 'quick') el.textContent = `Quick Scan (${QUICK_SCAN_SERVICES.length})`;
  else el.textContent = `${_selectedServices.length} Services`;
}

function renderServiceDropdown() {
  const content = document.getElementById('serviceDropdownContent');
  if (!content) return;

  const filtered = _serviceSearch
    ? _allServices.filter(s => s.toLowerCase().includes(_serviceSearch.toLowerCase()))
    : _allServices;

  let html = `<div style="position:sticky;top:0;z-index:1;background:var(--bg-card);padding:8px 10px 6px;border-bottom:1px solid var(--border)">
    <input type="text" id="serviceSearchInput" placeholder="Search services..." value="${_serviceSearch}"
      oninput="_serviceSearch=this.value;renderServiceDropdown()"
      style="width:100%;padding:5px 8px;font-size:11px;border:1px solid var(--border);border-radius:4px;background:var(--bg-base);color:var(--text-primary);outline:none;box-sizing:border-box;margin-bottom:6px">
    <div style="display:flex;gap:6px;margin-bottom:4px">
      <button class="btn btn-sm ${_serviceMode==='all'?'btn-primary':'btn-outline'}" onclick="setServiceMode('all')" style="font-size:10px;padding:2px 8px">All (${_allServices.length})</button>
      <button class="btn btn-sm ${_serviceMode==='quick'?'btn-primary':'btn-outline'}" onclick="setServiceMode('quick')" style="font-size:10px;padding:2px 8px">Quick (${QUICK_SCAN_SERVICES.length})</button>
      <button class="btn btn-sm btn-outline" onclick="setServiceMode('clear')" style="font-size:10px;padding:2px 8px">Clear</button>
    </div>
  </div>`;

  html += `<div style="max-height:300px;overflow-y:auto;padding:4px 0">`;
  for (const s of filtered) {
    const checked = (_serviceMode === 'all') ? false : _selectedServices.includes(s);
    const isQuick = QUICK_SCAN_SERVICES.includes(s);
    html += `<div style="padding:3px 10px">
      <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:11px;color:var(--text-secondary)">
        <input type="checkbox" value="${s}" ${_serviceMode==='all' ? '' : (checked?'checked':'')}
          onchange="toggleServiceSelect('${s}',this.checked)" style="accent-color:var(--accent)"
          ${_serviceMode==='all'?'disabled':''}> ${s}${isQuick ? ' <span style="color:var(--accent);font-size:9px;font-weight:600">&#9733;</span>' : ''}
      </label>
    </div>`;
  }
  if (filtered.length === 0 && _serviceSearch) {
    html += `<div style="padding:10px;font-size:11px;color:var(--text-muted);text-align:center">No matching services</div>`;
  }
  html += `</div>`;

  if (_serviceMode !== 'all' && _selectedServices.length > 0) {
    html += `<div style="padding:6px 10px;border-top:1px solid var(--border);font-size:10px;color:var(--accent);font-weight:600">${_selectedServices.length} selected</div>`;
  }

  content.innerHTML = html;

  const input = document.getElementById('serviceSearchInput');
  if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
}

// ---------------------------------------------------------------------------
// Scan
// ---------------------------------------------------------------------------
async function startScan() {
  const profiles = [..._selectedProfiles];
  if (!profiles.length) return;

  const excludeDefaults = document.getElementById('excludeDefaults')?.checked ?? true;
  const regions = _selectedRegions.length > 0 ? _selectedRegions : null;
  const services = (_serviceMode === 'all' || _selectedServices.length === 0) ? null : _selectedServices;

  // Show progress
  document.getElementById('progressSection').style.display = 'block';
  document.getElementById('scanBtn').disabled = true;

  try {
    await fetch('/mapinventory/api/scan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({profiles, exclude_defaults: excludeDefaults, regions, services}),
    });
    // Start polling progress for first profile
    _activeProfile = profiles[0];
    pollProgress(profiles);
  } catch(e) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('scanBtn').disabled = false;
  }
}

function pollProgress(profiles) {
  if (_pollTimer) clearInterval(_pollTimer);
  let doneProfiles = new Set();
  _pollTimer = setInterval(async () => {
    for (const profile of profiles) {
      if (doneProfiles.has(profile)) continue;
      try {
        const resp = await fetch(`/mapinventory/api/scan-progress?profile=${encodeURIComponent(profile)}`);
        const data = await resp.json();
        if (data.status === 'ok') {
          updateProgressUI(data);
          if (data.done) {
            doneProfiles.add(profile);
            if (data.error) {
              console.error(`Scan error for ${profile}:`, data.error);
            }
          }
        }
      } catch(e) { /* ignore */ }
    }
    if (doneProfiles.size >= profiles.length) {
      clearInterval(_pollTimer);
      _pollTimer = null;
      onScanComplete(profiles);
    }
  }, 800);
}

function updateProgressUI(data) {
  const pct = data.percent || 0;
  document.getElementById('progressBar').style.width = `${pct}%`;
  document.getElementById('progressLabel').textContent = `${Math.round(pct)}%`;
  document.getElementById('progressService').textContent = data.service || '—';
  document.getElementById('progressCount').textContent = `${data.completed || 0} / ${data.total || 0}`;
}

async function onScanComplete(profiles) {
  document.getElementById('progressSection').style.display = 'none';
  document.getElementById('scanBtn').disabled = false;

  // Load results for each profile
  for (const profile of profiles) {
    try {
      const resp = await fetch(`/mapinventory/api/last-scan?profile=${encodeURIComponent(profile)}`);
      const data = await resp.json();
      if (data.status !== 'not_found') {
        _scanData[profile] = data;
      }
    } catch(e) { /* ignore */ }
  }

  // Display first profile by default
  if (profiles.length > 0 && _scanData[profiles[0]]) {
    displayScanResults(profiles[0]);
  }

  // Refresh scan history to show new scan
  loadScanHistory();

  // If exactly 2 profiles, offer comparison
  if (profiles.length === 2 && _scanData[profiles[0]] && _scanData[profiles[1]]) {
    showComparePanel(profiles[0], profiles[1]);
  }
}

// ---------------------------------------------------------------------------
// Display Results
// ---------------------------------------------------------------------------
function displayScanResults(profile) {
  _activeProfile = profile;
  const data = _scanData[profile];
  if (!data) return;

  const meta = data.metadata || {};
  const stats = data.scan_stats || {};
  _allResources = data.resources || [];
  _filteredResources = [..._allResources];

  // Info bar
  const infoBar = document.getElementById('scanInfoBar');
  infoBar.style.display = 'flex';
  document.getElementById('infoProfile').textContent = profile;
  document.getElementById('infoAccountId').textContent = meta.account_id || '—';
  document.getElementById('infoScanTime').textContent = meta.timestamp || '—';
  const cacheAge = data._cache_age_seconds;
  if (cacheAge != null) {
    const mins = Math.round(cacheAge / 60);
    document.getElementById('infoCacheAge').textContent = mins < 60 ? `${mins}m ago` : `${Math.round(mins/60)}h ago`;
  }

  // Scan statistics dashboard
  renderScanStats(meta, stats);
  // Metric cards
  renderMetricCards(meta);
  // Charts
  renderCharts(meta, _allResources);
  // Filters
  populateFilterOptions(meta);
  document.getElementById('filtersRow').style.display = 'block';
  // Service table
  renderServiceTable(meta);
  // Hide detail panel
  closeDetailPanel();
}

// ---------------------------------------------------------------------------
// Scan Statistics Dashboard
// ---------------------------------------------------------------------------
function renderScanStats(meta, stats) {
  const section = document.getElementById('scanStatsSection');
  if (!section) return;
  section.style.display = 'block';

  const duration = meta.scan_duration_seconds || 0;
  const scanned = stats.scanned_services || meta.services_scanned || 0;
  const withRes = stats.services_with_resources || meta.services_with_resources || 0;
  const failed = stats.failed_services_count || 0;
  const partial = stats.partial_services_count || 0;
  const empty = stats.empty_services_count || 0;
  const totalRes = meta.resource_count || 0;
  const regions = meta.regions_scanned || 0;

  const cards = document.getElementById('scanStatsCards');
  cards.innerHTML = `
    <div class="metric-card scan-stat-card" data-stat="duration" style="cursor:default">
      <div class="metric-icon" style="color:var(--accent)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      </div>
      <div class="metric-value">${formatDuration(duration)}</div>
      <div class="metric-label" data-i18n="mapinv_scan_duration">Scan Duration</div>
    </div>
    <div class="metric-card scan-stat-card" data-stat="scanned" style="cursor:pointer" onclick="showScanStatDetail('scanned')">
      <div class="metric-icon" style="color:#4da6ff">${ICONS.barChart}</div>
      <div class="metric-value">${scanned}</div>
      <div class="metric-label" data-i18n="mapinv_scanned_services">Scanned Services</div>
    </div>
    <div class="metric-card scan-stat-card" data-stat="found" style="cursor:pointer" onclick="showScanStatDetail('found')">
      <div class="metric-icon" style="color:#00c87a">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
      </div>
      <div class="metric-value">${withRes}</div>
      <div class="metric-label" data-i18n="mapinv_services_found">Services Found</div>
    </div>
    <div class="metric-card scan-stat-card" data-stat="failed" style="cursor:pointer;${failed > 0 ? 'border-color:#f87171' : ''}" onclick="showScanStatDetail('failed')">
      <div class="metric-icon" style="color:${failed > 0 ? '#f87171' : 'var(--text-muted)'}">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      </div>
      <div class="metric-value" style="${failed > 0 ? 'color:#f87171' : ''}">${failed}</div>
      <div class="metric-label" data-i18n="mapinv_failed_services">Failed Services</div>
    </div>
    <div class="metric-card scan-stat-card" data-stat="empty" style="cursor:pointer" onclick="showScanStatDetail('empty')">
      <div class="metric-icon" style="color:var(--text-muted)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
      </div>
      <div class="metric-value">${empty}</div>
      <div class="metric-label" data-i18n="mapinv_empty_services">Empty Services</div>
    </div>
    <div class="metric-card scan-stat-card" data-stat="regions" style="cursor:pointer" onclick="showScanStatDetail('regions')">
      <div class="metric-icon" style="color:#b07aff">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      </div>
      <div class="metric-value">${regions}</div>
      <div class="metric-label" data-i18n="mapinv_regions_scanned">Regions</div>
    </div>
  `;
}

function showScanStatDetail(type) {
  const data = _scanData[_activeProfile];
  if (!data) return;
  const stats = data.scan_stats || {};
  const meta = data.metadata || {};

  const detail = document.getElementById('scanStatsDetail');
  const title = document.getElementById('scanStatsDetailTitle');
  const body = document.getElementById('scanStatsDetailBody');
  detail.style.display = 'block';

  let html = '';

  if (type === 'scanned') {
    title.textContent = t('mapinv_scanned_services_detail') || `Scanned Services (${stats.scanned_services || 0})`;
    const list = meta.services_scanned_list || [];
    html = '<div style="display:flex;flex-wrap:wrap;gap:6px">';
    for (const s of list) {
      const hasRes = (meta.service_counts || {})[s];
      const failed = (stats.failed_services || []).find(f => f.service === s);
      let color = 'var(--text-muted)';
      let bg = 'var(--bg-base)';
      if (hasRes) { color = '#00c87a'; bg = 'rgba(0,200,122,0.08)'; }
      else if (failed) { color = '#f87171'; bg = 'rgba(248,113,113,0.08)'; }
      html += `<span style="display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;background:${bg};color:${color};border:1px solid ${color}30">${s}</span>`;
    }
    html += '</div>';
    html += '<div style="margin-top:10px;font-size:11px;color:var(--text-muted)">';
    html += '<span style="color:#00c87a">&#9679;</span> Resources found &nbsp; <span style="color:#f87171">&#9679;</span> Failed &nbsp; <span style="color:var(--text-muted)">&#9679;</span> Empty';
    html += '</div>';
  }
  else if (type === 'found') {
    title.textContent = t('mapinv_services_with_resources') || `Services with Resources (${stats.services_with_resources || 0})`;
    const svcCounts = meta.service_counts || {};
    const sorted = Object.entries(svcCounts).sort((a,b) => b[1] - a[1]);
    html = '<table style="width:100%;font-size:12px;border-collapse:collapse">';
    html += '<tr style="border-bottom:1px solid var(--border)"><th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Service</th><th style="text-align:right;padding:4px 8px;color:var(--text-muted)">Resources</th></tr>';
    for (const [svc, count] of sorted) {
      html += `<tr style="border-bottom:1px solid var(--border)"><td style="padding:4px 8px;color:var(--text-primary)">${svc}</td><td style="text-align:right;padding:4px 8px;color:var(--accent);font-weight:600">${count}</td></tr>`;
    }
    html += '</table>';
  }
  else if (type === 'failed') {
    const failedList = stats.failed_services || [];
    const partialList = stats.partial_services || [];
    title.textContent = t('mapinv_failed_services_detail') || `Failed Services (${failedList.length})`;
    if (failedList.length === 0 && partialList.length === 0) {
      html = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px">' + (t('mapinv_no_failures') || 'No failures detected') + '</div>';
    } else {
      html = '<table style="width:100%;font-size:12px;border-collapse:collapse">';
      html += '<tr style="border-bottom:1px solid var(--border)"><th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Service</th><th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Status</th><th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Error</th></tr>';
      for (const f of failedList) {
        const firstErr = (f.errors || [])[0] || {};
        html += `<tr style="border-bottom:1px solid var(--border)">
          <td style="padding:4px 8px;color:#f87171;font-weight:600">${f.service}</td>
          <td style="padding:4px 8px"><span style="background:rgba(248,113,113,0.15);color:#f87171;padding:1px 6px;border-radius:3px;font-size:10px">FAILED</span></td>
          <td style="padding:4px 8px;color:var(--text-muted);font-size:11px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${(firstErr.error || '').replace(/"/g, '&quot;')}">${firstErr.type || ''}: ${(firstErr.error || '').substring(0, 80)}</td>
        </tr>`;
      }
      for (const p of partialList) {
        const errCount = (p.errors || []).length;
        const firstErr = (p.errors || [])[0] || {};
        html += `<tr style="border-bottom:1px solid var(--border)">
          <td style="padding:4px 8px;color:#fbbf24;font-weight:600">${p.service}</td>
          <td style="padding:4px 8px"><span style="background:rgba(251,191,36,0.15);color:#fbbf24;padding:1px 6px;border-radius:3px;font-size:10px">PARTIAL (${errCount})</span></td>
          <td style="padding:4px 8px;color:var(--text-muted);font-size:11px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${(firstErr.error || '').replace(/"/g, '&quot;')}">${firstErr.type || ''}: ${(firstErr.error || '').substring(0, 80)}</td>
        </tr>`;
      }
      html += '</table>';
    }
  }
  else if (type === 'empty') {
    const emptyList = stats.empty_services || [];
    title.textContent = t('mapinv_empty_services_detail') || `Empty Services (${emptyList.length})`;
    if (emptyList.length === 0) {
      html = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px">All scanned services returned resources</div>';
    } else {
      html = '<div style="display:flex;flex-wrap:wrap;gap:6px">';
      for (const s of emptyList) {
        html += `<span style="display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;background:var(--bg-base);color:var(--text-muted);border:1px solid var(--border)">${s}</span>`;
      }
      html += '</div>';
    }
  }
  else if (type === 'regions') {
    const regList = meta.regions_scanned_list || [];
    const regCounts = meta.region_counts || {};
    title.textContent = t('mapinv_regions_detail') || `Regions (${regList.length})`;
    html = '<table style="width:100%;font-size:12px;border-collapse:collapse">';
    html += '<tr style="border-bottom:1px solid var(--border)"><th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Region</th><th style="text-align:right;padding:4px 8px;color:var(--text-muted)">Resources</th></tr>';
    for (const r of regList) {
      const cnt = regCounts[r] || 0;
      html += `<tr style="border-bottom:1px solid var(--border)"><td style="padding:4px 8px;color:var(--text-primary)">${r}</td><td style="text-align:right;padding:4px 8px;color:${cnt > 0 ? 'var(--accent)' : 'var(--text-muted)'};font-weight:${cnt > 0 ? '600' : '400'}">${cnt}</td></tr>`;
    }
    html += '</table>';
  }

  body.innerHTML = html;
}

function renderMetricCards(meta) {
  const grid = document.getElementById('metricCards');
  const svcCount = meta.services_with_resources || Object.keys(meta.service_counts || {}).length;
  const regCount = Object.keys(meta.region_counts || {}).length;
  const resCount = meta.resource_count || 0;

  // Update collapsible header
  const countEl = document.getElementById('overviewResourceCount');
  if (countEl) countEl.textContent = formatNum(resCount);
  const summaryEl = document.getElementById('overviewSummaryLabel');
  if (summaryEl) summaryEl.textContent = `${svcCount} services · ${regCount} regions · ${formatDuration(meta.scan_duration_seconds || 0)}`;

  grid.innerHTML = `
    <div class="metric-card">
      <div class="metric-icon" style="color:var(--accent)">${ICONS.layers}</div>
      <div class="metric-value">${formatNum(meta.resource_count || 0)}</div>
      <div class="metric-label" data-i18n="mapinv_total_resources">Total Resources</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon" style="color:#4da6ff">${ICONS.barChart}</div>
      <div class="metric-value">${svcCount}</div>
      <div class="metric-label" data-i18n="mapinv_services_found">Services</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon" style="color:#00c87a">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      </div>
      <div class="metric-value">${regCount}</div>
      <div class="metric-label" data-i18n="mapinv_regions_found">Regions</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon" style="color:#b07aff">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      </div>
      <div class="metric-value">${formatDuration(meta.scan_duration_seconds || 0)}</div>
      <div class="metric-label" data-i18n="mapinv_scan_duration">Scan Duration</div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------
function destroyCharts() {
  Object.values(_charts).forEach(c => { try { c.destroy(); } catch(e){} });
  _charts = {};
}

function renderCharts(meta, resources) {
  destroyCharts();
  applyChartDefaults();
  const cc = getChartColors();

  // Filter out zero-count entries
  const svcCounts = {};
  for (const [k, v] of Object.entries(meta.service_counts || {})) { if (v > 0) svcCounts[k] = v; }
  const regCounts = {};
  for (const [k, v] of Object.entries(meta.region_counts || {})) { if (v > 0) regCounts[k] = v; }
  const typeCounts = {};
  for (const [k, v] of Object.entries(meta.type_counts || {})) { if (v > 0) typeCounts[k] = v; }

  const hasSvc = Object.keys(svcCounts).length > 0;
  const hasReg = Object.keys(regCounts).length > 0;

  // Show chart rows only if we have data
  document.getElementById('chartsRow1').style.display = (hasSvc || hasReg) ? 'block' : 'none';
  document.getElementById('chartsRow2').style.display = Object.keys(typeCounts).length > 0 ? 'block' : 'none';

  // --- Radar Chart ---
  const RADAR_EXCLUDE = new Set(['config']);
  const radarSorted = Object.entries(svcCounts).filter(([k]) => !RADAR_EXCLUDE.has(k.toLowerCase())).sort((a,b) => b[1] - a[1]).slice(0, 12);
  const radarLabels = radarSorted.map(e => e[0]);
  const radarData = radarSorted.map(e => e[1]);
  const radarCtx = document.getElementById('radarChart');
  if (radarCtx && radarLabels.length >= 3) {
    _charts.radar = new Chart(radarCtx, {
      type: 'radar',
      data: {
        labels: radarLabels.map(l => l.toUpperCase()),
        datasets: [{
          label: t('mapinv_resources'),
          data: radarData,
          backgroundColor: 'rgba(255,153,0,0.15)',
          borderColor: '#ff9900',
          pointBackgroundColor: '#ff9900',
          pointRadius: 4,
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { r: { beginAtZero: true, grid: { color: cc.grid }, ticks: { display: false }, pointLabels: { font: { size: 12 }, color: cc.text } } },
        plugins: { legend: { display: false } },
      }
    });
  }

  // --- Region Bar Chart ---
  const regSorted = Object.entries(regCounts).sort((a,b) => b[1] - a[1]);
  const regLabels = regSorted.map(e => e[0]);
  const regData = regSorted.map(e => e[1]);
  const regWrap = document.getElementById('regionBarChart')?.parentElement;
  if (regWrap) regWrap.style.height = `${Math.max(250, regLabels.length * 30 + 50)}px`;
  const regCtx = document.getElementById('regionBarChart');
  if (regCtx && regLabels.length > 0) {
    _charts.regionBar = new Chart(regCtx, {
      type: 'bar',
      data: {
        labels: regLabels,
        datasets: [{
          data: regData,
          backgroundColor: regLabels.map((_, i) => PALETTE[i % PALETTE.length]),
          borderRadius: 4,
          maxBarThickness: 28,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        scales: {
          x: { grid: { color: cc.grid }, ticks: { color: cc.text, font: { size: 12 } } },
          y: { grid: { display: false }, ticks: { color: cc.text, font: { size: 12 } } }
        },
        plugins: { legend: { display: false } },
      }
    });
  }

  // --- Service Donut ---
  const svcLabels = Object.entries(svcCounts).sort((a,b) => b[1] - a[1]).slice(0, 10).map(e => e[0]);
  const svcData = svcLabels.map(k => svcCounts[k]);
  const donutCtx = document.getElementById('serviceDonutChart');
  if (donutCtx && svcLabels.length > 0) {
    _charts.serviceDonut = new Chart(donutCtx, {
      type: 'doughnut',
      data: {
        labels: svcLabels.map(l => l.toUpperCase()),
        datasets: [{
          data: svcData,
          backgroundColor: svcLabels.map((_, i) => PALETTE[i % PALETTE.length]),
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '55%',
        plugins: {
          legend: { position: 'right', labels: { font: { size: 12 }, color: cc.text, padding: 8, boxWidth: 14 } },
        },
      }
    });
  }

  // --- Type Bar Chart ---
  const typeEntries = Object.entries(typeCounts).sort((a,b) => b[1] - a[1]).slice(0, 20);
  const typeLabels = typeEntries.map(e => e[0]);
  const typeData = typeEntries.map(e => e[1]);
  const typeWrap = document.getElementById('typeBarWrap');
  if (typeWrap) typeWrap.style.height = `${Math.max(250, typeEntries.length * 30 + 50)}px`;
  const typeCtx = document.getElementById('typeBarChart');
  if (typeCtx && typeEntries.length > 0) {
    _charts.typeBar = new Chart(typeCtx, {
      type: 'bar',
      data: {
        labels: typeLabels,
        datasets: [{
          data: typeData,
          backgroundColor: typeLabels.map((_, i) => PALETTE[i % PALETTE.length]),
          borderRadius: 3,
          maxBarThickness: 20,
        }]
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        scales: {
          x: { grid: { color: cc.grid }, ticks: { color: cc.text, font: { size: 12 } } },
          y: { grid: { display: false }, ticks: { color: cc.text, font: { size: 12 } } }
        },
        plugins: { legend: { display: false } },
        maintainAspectRatio: false,
      }
    });
  }

  // --- Default Donut ---
  let defaultCount = 0, customCount = 0;
  for (const r of resources) {
    if (r.is_default) defaultCount++; else customCount++;
  }
  const defCtx = document.getElementById('defaultDonutChart');
  if (defCtx && (defaultCount > 0 || customCount > 0)) {
    // Filter out zero segments
    const defLabels = [], defData = [], defColors = [];
    if (customCount > 0) { defLabels.push(t('mapinv_custom')); defData.push(customCount); defColors.push('#00c87a'); }
    if (defaultCount > 0) { defLabels.push(t('mapinv_default')); defData.push(defaultCount); defColors.push('#7a90a8'); }
    _charts.defaultDonut = new Chart(defCtx, {
      type: 'doughnut',
      data: {
        labels: defLabels,
        datasets: [{ data: defData, backgroundColor: defColors, borderWidth: 0 }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '55%',
        plugins: { legend: { position: 'bottom', labels: { font: { size: 13 }, color: cc.text, padding: 12 } } },
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------
// --- Filter dropdown state (multi-select with checkboxes) ---
let _filterSelected = { service: new Set(), region: new Set(), type: new Set() };
let _filterOptions = { service: [], region: [], type: [] };
let _openFilter = null;

function _fk(kind) { return 'filter' + kind.charAt(0).toUpperCase() + kind.slice(1); }

function populateFilterOptions(meta) {
  const svcCounts = meta.service_counts || {};
  const regCounts = meta.region_counts || {};
  const typeCounts = meta.type_counts || {};

  _filterOptions.service = Object.keys(svcCounts).sort().map(s => ({ value: s, label: s.toUpperCase(), count: svcCounts[s] }));
  _filterOptions.region = Object.keys(regCounts).sort().map(r => ({ value: r, label: r, count: regCounts[r] }));
  _filterOptions.type = Object.keys(typeCounts).sort().map(t2 => ({ value: t2, label: t2, count: typeCounts[t2] }));

  // Reset selections
  _filterSelected = { service: new Set(), region: new Set(), type: new Set() };
  updateFilterLabel('service');
  updateFilterLabel('region');
  updateFilterLabel('type');
}

function renderFilterList(kind) {
  const list = document.getElementById(`${_fk(kind)}List`);
  if (!list) return;
  const opts = _filterOptions[kind] || [];
  const sel = _filterSelected[kind];

  let html = '';
  for (const o of opts) {
    const checked = sel.has(o.value) ? 'checked' : '';
    html += `<label class="filter-dd-item" data-val="${o.value}" data-search="${o.label.toLowerCase()}"
      style="padding:5px 12px;cursor:pointer;font-size:12px;color:var(--text-primary);display:flex;align-items:center;gap:8px">
      <input type="checkbox" ${checked} value="${o.value}" onchange="onFilterCheck('${kind}',this)"
        style="accent-color:var(--accent);width:14px;height:14px;cursor:pointer;flex-shrink:0">
      <span style="font-family:'JetBrains Mono',monospace;font-size:11px;flex:1">${o.label}</span>
      <span style="font-size:10px;color:var(--accent);font-weight:600">${o.count}</span>
    </label>`;
  }
  list.innerHTML = html;
}

function onFilterCheck(kind, cb) {
  if (cb.checked) {
    _filterSelected[kind].add(cb.value);
  } else {
    _filterSelected[kind].delete(cb.value);
  }
  updateFilterLabel(kind);
  applyFilters();
}

function filterSelectAll(kind) {
  _filterSelected[kind] = new Set(_filterOptions[kind].map(o => o.value));
  updateFilterLabel(kind);
  // Update checkboxes in DOM
  const list = document.getElementById(`${_fk(kind)}List`);
  if (list) list.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = true);
  applyFilters();
}

function filterClear(kind) {
  _filterSelected[kind].clear();
  updateFilterLabel(kind);
  const list = document.getElementById(`${_fk(kind)}List`);
  if (list) list.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = false);
  applyFilters();
}

function updateFilterLabel(kind) {
  const labelEl = document.getElementById(`${_fk(kind)}Label`);
  if (!labelEl) return;
  const sel = _filterSelected[kind];
  const total = _filterOptions[kind].length;
  if (sel.size === 0) {
    const allLabel = kind === 'service' ? t('mapinv_all_services') : kind === 'region' ? t('mapinv_all_regions') : t('mapinv_all_types');
    labelEl.textContent = allLabel;
  } else {
    labelEl.textContent = `${sel.size} / ${total}`;
  }
  // Update footer count
  const footer = document.getElementById(`${_fk(kind)}Footer`);
  if (footer) {
    footer.textContent = sel.size > 0 ? `${sel.size} selected` : '';
    footer.style.display = sel.size > 0 ? 'block' : 'none';
  }
}

function toggleFilterDropdown(kind) {
  const dd = document.getElementById(`${_fk(kind)}Dropdown`);
  if (!dd) return;
  const isOpen = dd.style.display !== 'none';
  closeAllFilterDropdowns();
  if (!isOpen) {
    dd.style.display = 'block';
    _openFilter = kind;
    const search = dd.querySelector('.filter-dd-search');
    if (search) { search.value = ''; search.focus(); }
    renderFilterList(kind);
  }
}

function closeAllFilterDropdowns() {
  ['service', 'region', 'type'].forEach(k => {
    const dd = document.getElementById(`${_fk(k)}Dropdown`);
    if (dd) dd.style.display = 'none';
  });
  _openFilter = null;
}

function filterDropdownSearch(kind) {
  const search = document.getElementById(`${_fk(kind)}Search`);
  const list = document.getElementById(`${_fk(kind)}List`);
  if (!search || !list) return;
  const q = search.value.toLowerCase();
  list.querySelectorAll('.filter-dd-item').forEach(item => {
    const searchText = item.dataset.search || '';
    item.style.display = searchText.includes(q) ? '' : 'none';
  });
}

// Close filter dropdown on outside click
document.addEventListener('click', (e) => {
  if (_openFilter && !e.target.closest('.filter-dropdown')) {
    closeAllFilterDropdowns();
  }
});

function applyFilters() {
  const search = (document.getElementById('resourceSearch')?.value || '').toLowerCase();
  const svcSet = _filterSelected.service;
  const regSet = _filterSelected.region;
  const typSet = _filterSelected.type;

  _filteredResources = _allResources.filter(r => {
    if (svcSet.size > 0 && !svcSet.has(r.service)) return false;
    if (regSet.size > 0 && !regSet.has(r.region)) return false;
    if (typSet.size > 0 && !typSet.has(`${r.service}/${r.type}`)) return false;
    if (search) {
      const hay = `${r.service} ${r.type} ${r.name} ${r.id} ${r.region} ${JSON.stringify(r.tags)}`.toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });

  document.getElementById('filterResultCount').textContent = `${_filteredResources.length} resources`;

  // Re-render service table with filtered data
  const meta = _scanData[_activeProfile]?.metadata || {};
  renderServiceTable(meta, _filteredResources);

  // Update charts
  updateChartsForFilter();
}

function clearResourceFilters() {
  document.getElementById('resourceSearch').value = '';
  _filterSelected = { service: new Set(), region: new Set(), type: new Set() };
  updateFilterLabel('service');
  updateFilterLabel('region');
  updateFilterLabel('type');
  _filteredResources = [..._allResources];
  document.getElementById('filterResultCount').textContent = '';
  const meta = _scanData[_activeProfile]?.metadata || {};
  renderServiceTable(meta);
  renderCharts(meta, _allResources);
}

function updateChartsForFilter() {
  // Rebuild counts from filtered resources
  const svcCounts = {}, regCounts = {}, typeCounts = {};
  for (const r of _filteredResources) {
    svcCounts[r.service] = (svcCounts[r.service] || 0) + 1;
    regCounts[r.region] = (regCounts[r.region] || 0) + 1;
    const tk = `${r.service}/${r.type}`;
    typeCounts[tk] = (typeCounts[tk] || 0) + 1;
  }
  const fakeMeta = { service_counts: svcCounts, region_counts: regCounts, type_counts: typeCounts, resource_count: _filteredResources.length };
  renderCharts(fakeMeta, _filteredResources);
}

// ---------------------------------------------------------------------------
// Service Table
// ---------------------------------------------------------------------------
function renderServiceTable(meta, resources) {
  const section = document.getElementById('serviceTableSection');
  section.style.display = 'block';
  const tbody = document.getElementById('serviceTableBody');

  const res = resources || _allResources;
  // Aggregate by service
  const svcMap = {};
  for (const r of res) {
    if (!svcMap[r.service]) svcMap[r.service] = { count: 0, types: new Set(), regions: new Set() };
    svcMap[r.service].count++;
    svcMap[r.service].types.add(r.type);
    svcMap[r.service].regions.add(r.region);
  }

  let entries = Object.entries(svcMap).map(([svc, d]) => ({ service: svc, count: d.count, types: [...d.types], regions: [...d.regions] }));

  // Sort
  entries.sort((a, b) => {
    const va = a[_svcSortCol] ?? '', vb = b[_svcSortCol] ?? '';
    if (typeof va === 'number') return _svcSortAsc ? va - vb : vb - va;
    return _svcSortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });

  tbody.innerHTML = entries.map(e => {
    const icon = SERVICE_ICONS[e.service] || SERVICE_ICONS._default;
    return `<tr class="svc-row" onclick="openServiceDetail('${e.service}')" style="cursor:pointer">
      <td style="text-align:center"><span style="display:flex;align-items:center;justify-content:center;color:var(--accent)">${icon}</span></td>
      <td style="font-weight:600;color:var(--text-primary)">${e.service.toUpperCase()}</td>
      <td><span style="font-weight:700;color:var(--accent)">${e.count}</span></td>
      <td style="font-size:11px;color:var(--text-muted)">${e.types.join(', ')}</td>
      <td style="font-size:11px;color:var(--text-muted)">${e.regions.length > 3 ? e.regions.length + ' regions' : e.regions.join(', ')}</td>
      <td><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></td>
    </tr>`;
  }).join('');
}

function sortServiceTable(col) {
  if (_svcSortCol === col) _svcSortAsc = !_svcSortAsc;
  else { _svcSortCol = col; _svcSortAsc = col === 'service'; }
  const meta = _scanData[_activeProfile]?.metadata || {};
  renderServiceTable(meta, _filteredResources.length < _allResources.length ? _filteredResources : undefined);
}

// ---------------------------------------------------------------------------
// Service Detail Panel
// ---------------------------------------------------------------------------
let _detailSortCol = -1;  // column index, -1 = default
let _detailSortAsc = true;
let _detailCols = [];     // current columns
let _detailTypeSelected = new Set();  // selected resource types for detail filter
let _detailTypeOptions = [];          // available types [{value, count}]

function openServiceDetail(service) {
  _detailService = service;
  _detailResources = (_filteredResources.length < _allResources.length ? _filteredResources : _allResources)
    .filter(r => r.service === service);
  _detailFiltered = [..._detailResources];
  _detailPage = 0;
  _detailCols = getServiceColumns(service);

  // Default sort for S3: by size_bytes descending
  _detailSortCol = -1;
  _detailSortAsc = true;
  if (service === 's3') {
    const sizeIdx = _detailCols.findIndex(c => c.sortKey === 'size_bytes');
    if (sizeIdx >= 0) {
      _detailSortCol = sizeIdx;
      _detailSortAsc = false;
      sortDetailData();
    }
  }

  // Build type filter options
  const typeCounts = {};
  for (const r of _detailResources) {
    typeCounts[r.type] = (typeCounts[r.type] || 0) + 1;
  }
  _detailTypeOptions = Object.entries(typeCounts).sort((a,b) => b[1] - a[1]).map(([v, c]) => ({ value: v, count: c }));
  _detailTypeSelected.clear();

  // Show type filter for all services
  const typeWrap = document.getElementById('detailTypeWrap');
  if (typeWrap) {
    typeWrap.style.display = _detailTypeOptions.length > 0 ? '' : 'none';
  }
  updateDetailTypeLabel();

  document.getElementById('serviceTableSection').style.display = 'none';
  document.getElementById('detailPanel').style.display = 'block';
  document.getElementById('detailTitle').textContent = `${service.toUpperCase()} (${_detailResources.length})`;
  document.getElementById('detailCount').textContent = `${_detailResources.length} resources`;
  document.getElementById('detailSearch').value = '';

  renderDetailTable();
}

function closeDetailPanel() {
  document.getElementById('detailPanel').style.display = 'none';
  document.getElementById('serviceTableSection').style.display = _activeProfile ? 'block' : 'none';
  _detailService = null;
}

function renderDetailTable() {
  const thead = document.getElementById('detailTableHead');
  const tbody = document.getElementById('detailTableBody');
  const cols = _detailCols;

  thead.innerHTML = '<tr>' + cols.map((c, idx) => {
    const arrow = _detailSortCol === idx ? (_detailSortAsc ? ' ↑' : ' ↓') : ' <span style="opacity:.35">↕</span>';
    return `<th style="white-space:nowrap;cursor:pointer;user-select:none" onclick="sortDetailByCol(${idx})">${c.label}${arrow}</th>`;
  }).join('') + '<th style="width:40px"></th></tr>';

  const start = _detailPage * DETAIL_PAGE_SIZE;
  const pageItems = _detailFiltered.slice(start, start + DETAIL_PAGE_SIZE);

  tbody.innerHTML = pageItems.map((r, i) => {
    const globalIdx = start + i;
    const cells = cols.map(c => {
      let val = c.getter(r);
      if (val === null || val === undefined) val = '—';
      if (typeof val === 'boolean') val = val ? '✓' : '—';
      if (typeof val === 'object') val = JSON.stringify(val).slice(0, 80);
      const titleVal = c.html ? String(val).replace(/<[^>]*>/g, '') : String(val);
      return `<td style="font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${titleVal.replace(/"/g, '&quot;')}">${val}</td>`;
    }).join('');
    return `<tr>${cells}<td>
      <button class="btn btn-outline btn-sm" style="padding:2px 6px" onclick="showResourceJson(${globalIdx})" title="View details">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
    </td></tr>`;
  }).join('');

  renderDetailPagination();
}

function sortDetailByCol(colIdx) {
  if (_detailSortCol === colIdx) {
    _detailSortAsc = !_detailSortAsc;
  } else {
    _detailSortCol = colIdx;
    _detailSortAsc = true;
  }
  sortDetailData();
  _detailPage = 0;
  renderDetailTable();
}

function sortDetailData() {
  if (_detailSortCol < 0 || _detailSortCol >= _detailCols.length) return;
  const col = _detailCols[_detailSortCol];
  const rawGet = col.rawGetter || col.getter;

  _detailFiltered.sort((a, b) => {
    let va = rawGet(a);
    let vb = rawGet(b);
    // Nulls/undefined always sort to bottom
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    // Boolean
    if (typeof va === 'boolean') { va = va ? 1 : 0; vb = vb ? 1 : 0; }
    // Number
    if (typeof va === 'number' && typeof vb === 'number') {
      return _detailSortAsc ? va - vb : vb - va;
    }
    // String
    const sa = String(va).toLowerCase();
    const sb = String(vb).toLowerCase();
    return _detailSortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
  });
}

function renderDetailPagination() {
  const container = document.getElementById('detailPagination');
  const total = _detailFiltered.length;
  const totalPages = Math.ceil(total / DETAIL_PAGE_SIZE);
  if (totalPages <= 1) { container.innerHTML = ''; return; }

  let html = `<span style="font-size:12px;color:var(--text-muted)">Page ${_detailPage+1} of ${totalPages}</span>`;
  html += `<button class="btn btn-outline btn-sm" ${_detailPage===0?'disabled':''} onclick="detailGoPage(${_detailPage-1})">←</button>`;
  for (let i = 0; i < Math.min(totalPages, 10); i++) {
    html += `<button class="btn btn-sm ${i===_detailPage?'btn-primary':'btn-outline'}" onclick="detailGoPage(${i})">${i+1}</button>`;
  }
  if (totalPages > 10) html += `<span style="color:var(--text-muted)">...</span>`;
  html += `<button class="btn btn-outline btn-sm" ${_detailPage>=totalPages-1?'disabled':''} onclick="detailGoPage(${_detailPage+1})">→</button>`;
  container.innerHTML = html;
}

function detailGoPage(page) {
  _detailPage = page;
  renderDetailTable();
}

function filterDetailTable() {
  const search = (document.getElementById('detailSearch')?.value || '').toLowerCase();
  const typeSet = _detailTypeSelected;
  _detailFiltered = _detailResources.filter(r => {
    if (typeSet.size > 0 && !typeSet.has(r.type)) return false;
    if (search) {
      const hay = `${r.name} ${r.id} ${r.region} ${r.type} ${JSON.stringify(r.details)} ${JSON.stringify(r.tags)}`.toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });
  // Re-apply current sort
  if (_detailSortCol >= 0) sortDetailData();
  _detailPage = 0;
  document.getElementById('detailCount').textContent = `${_detailFiltered.length} resources`;
  renderDetailTable();
}

// ---------------------------------------------------------------------------
// Detail Type Filter (checkbox dropdown)
// ---------------------------------------------------------------------------
function toggleDetailTypeDropdown() {
  const dd = document.getElementById('detailTypeDropdown');
  if (!dd) return;
  const isOpen = dd.style.display !== 'none';
  dd.style.display = isOpen ? 'none' : 'block';
  if (!isOpen) {
    const search = document.getElementById('detailTypeSearch');
    if (search) { search.value = ''; search.focus(); }
    renderDetailTypeList();
  }
}

function renderDetailTypeList() {
  const list = document.getElementById('detailTypeList');
  if (!list) return;
  let html = '';
  for (const o of _detailTypeOptions) {
    const checked = _detailTypeSelected.has(o.value) ? 'checked' : '';
    html += `<label class="filter-dd-item" data-search="${o.value.toLowerCase()}"
      style="padding:5px 12px;cursor:pointer;font-size:12px;color:var(--text-primary);display:flex;align-items:center;gap:8px">
      <input type="checkbox" ${checked} value="${o.value}" onchange="onDetailTypeCheck(this)"
        style="accent-color:var(--accent);width:14px;height:14px;cursor:pointer;flex-shrink:0">
      <span style="font-family:'JetBrains Mono',monospace;font-size:11px;flex:1">${o.value}</span>
      <span style="font-size:10px;color:var(--accent);font-weight:600">${o.count}</span>
    </label>`;
  }
  list.innerHTML = html;
}

function onDetailTypeCheck(cb) {
  if (cb.checked) _detailTypeSelected.add(cb.value);
  else _detailTypeSelected.delete(cb.value);
  updateDetailTypeLabel();
  filterDetailTable();
}

function detailTypeSelectAll() {
  _detailTypeSelected = new Set(_detailTypeOptions.map(o => o.value));
  updateDetailTypeLabel();
  const list = document.getElementById('detailTypeList');
  if (list) list.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = true);
  filterDetailTable();
}

function detailTypeClear() {
  _detailTypeSelected.clear();
  updateDetailTypeLabel();
  const list = document.getElementById('detailTypeList');
  if (list) list.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = false);
  filterDetailTable();
}

function updateDetailTypeLabel() {
  const label = document.getElementById('detailTypeLabel');
  if (!label) return;
  const sel = _detailTypeSelected.size;
  const total = _detailTypeOptions.length;
  label.textContent = sel === 0 ? 'All Types' : `${sel} / ${total}`;
  const footer = document.getElementById('detailTypeFooter');
  if (footer) {
    footer.textContent = sel > 0 ? `${sel} selected` : '';
    footer.style.display = sel > 0 ? 'block' : 'none';
  }
}

function filterDetailTypeSearch() {
  const search = document.getElementById('detailTypeSearch');
  const list = document.getElementById('detailTypeList');
  if (!search || !list) return;
  const q = search.value.toLowerCase();
  list.querySelectorAll('.filter-dd-item').forEach(item => {
    item.style.display = (item.dataset.search || '').includes(q) ? '' : 'none';
  });
}

// Close detail type dropdown on outside click
document.addEventListener('click', (e) => {
  const dd = document.getElementById('detailTypeDropdown');
  if (dd && dd.style.display !== 'none' && !e.target.closest('#detailTypeWrap')) {
    dd.style.display = 'none';
  }
});

function getServiceColumns(service) {
  const base = [
    { label: 'Type', getter: r => r.type, rawGetter: r => r.type },
    { label: 'Name', getter: r => r.name, rawGetter: r => r.name },
    { label: 'ID', getter: r => r.id, rawGetter: r => r.id },
    { label: 'Region', getter: r => r.region, rawGetter: r => r.region },
  ];

  const svcCols = SERVICE_DETAIL_COLS[service];
  if (svcCols) return [...base, ...svcCols];

  // Generic: show top detail keys
  const allKeys = new Set();
  _detailResources.slice(0, 20).forEach(r => Object.keys(r.details || {}).forEach(k => allKeys.add(k)));
  const extraCols = [...allKeys].slice(0, 5).map(k => ({
    label: k.replace(/_/g, ' '),
    getter: r => (r.details || {})[k],
    rawGetter: r => (r.details || {})[k],
  }));
  return [...base, ...extraCols];
}

// Service-specific detail columns
const SERVICE_DETAIL_COLS = {
  s3: [
    { label: 'Versioning', getter: r => r.details?.versioning || '—', rawGetter: r => r.details?.versioning },
    { label: 'Encryption', getter: r => r.details?.encryption || '—', rawGetter: r => r.details?.encryption },
    { label: 'Public Block', getter: r => r.details?.public_access_blocked, rawGetter: r => r.details?.public_access_blocked },
    { label: 'Policy', getter: r => r.details?.has_policy ? 'Yes' : 'No', rawGetter: r => r.details?.has_policy },
    { label: 'Logging', getter: r => r.details?.logging_target || '—', rawGetter: r => r.details?.logging_target },
    { label: 'Size', sortKey: 'size_bytes', getter: r => r.details?.size_bytes != null ? formatBytes(r.details.size_bytes) : '—', rawGetter: r => r.details?.size_bytes },
    { label: 'Objects', getter: r => r.details?.object_count != null ? formatNum(r.details.object_count) : '—', rawGetter: r => r.details?.object_count },
  ],
  ec2: [
    { label: 'State', getter: r => r.details?.state },
    { label: 'Type', getter: r => r.details?.instance_type },
    { label: 'vCPU', getter: r => {
        const v = r.details?.vcpu;
        return (v && r.type === 'instance') ? `<span style="font-weight:600">${v}</span>` : '—';
      }, rawGetter: r => r.details?.vcpu || 0, html: true },
    { label: 'RAM', getter: r => {
        const v = r.details?.ram_gb;
        return (v && r.type === 'instance') ? `<span style="font-weight:600">${v} GB</span>` : '—';
      }, rawGetter: r => r.details?.ram_gb || 0, html: true },
    { label: 'Private IP', getter: r => r.details?.private_ip },
    { label: 'Public IP', getter: r => r.details?.public_ip },
    { label: 'VPC', getter: r => r.details?.vpc_id },
    { label: 'Disks', getter: r => {
        const dc = r.details?.disk_count;
        if (dc == null || r.type !== 'instance') return '—';
        const disks = r.details?.disks || [];
        const tip = disks.map(d => `${d.device}: ${d.size_gb}GB ${d.type}${d.encrypted ? ' enc' : ''}`).join(', ');
        return `<span title="${tip}" style="cursor:default;font-weight:600;color:var(--accent)">${dc}</span>`;
      }, rawGetter: r => r.details?.disk_count || 0, html: true },
    { label: 'Storage', getter: r => {
        const gb = r.details?.total_disk_gb;
        if (gb == null || r.type !== 'instance') return '—';
        return `<span style="font-weight:600">${gb} GB</span>`;
      }, rawGetter: r => r.details?.total_disk_gb || 0, html: true },
  ],
  rds: [
    { label: 'Engine', getter: r => r.details?.engine },
    { label: 'Version', getter: r => r.details?.engine_version },
    { label: 'Class', getter: r => r.details?.instance_class },
    { label: 'Status', getter: r => r.details?.status },
    { label: 'Multi-AZ', getter: r => r.details?.multi_az },
    { label: 'Encrypted', getter: r => r.details?.encrypted },
  ],
  iam: [
    { label: 'Path', getter: r => r.details?.path },
    { label: 'Created', getter: r => r.details?.create_date },
    { label: 'MFA', getter: r => r.details?.mfa_enabled },
    { label: 'Policies', getter: r => (r.details?.attached_policies || []).length },
  ],
  lambda: [
    { label: 'Runtime', getter: r => r.details?.runtime },
    { label: 'Memory', getter: r => r.details?.memory_size },
    { label: 'Timeout', getter: r => r.details?.timeout },
    { label: 'Code Size', getter: r => r.details?.code_size ? formatBytes(r.details.code_size) : '—' },
  ],
  vpc: [
    { label: 'CIDR', getter: r => r.details?.cidr_block },
    { label: 'State', getter: r => r.details?.state },
    { label: 'Default', getter: r => r.is_default },
  ],
  dynamodb: [
    { label: 'Status', getter: r => r.details?.status },
    { label: 'Billing', getter: r => r.details?.billing_mode },
    { label: 'Items', getter: r => r.details?.item_count != null ? formatNum(r.details.item_count) : '—' },
    { label: 'Size', getter: r => r.details?.size_bytes != null ? formatBytes(r.details.size_bytes) : '—' },
  ],
  eks: [
    { label: 'Status', getter: r => r.details?.status },
    { label: 'Version', getter: r => r.details?.version },
    { label: 'Endpoint', getter: r => r.details?.endpoint_public_access },
  ],
  ecs: [
    { label: 'Status', getter: r => r.details?.status },
    { label: 'Running', getter: r => r.details?.running_tasks_count },
    { label: 'Services', getter: r => r.details?.active_services_count },
  ],
};

// ---------------------------------------------------------------------------
// JSON Popup
// ---------------------------------------------------------------------------
let _jsonPopupData = null;

function showResourceJson(idx) {
  const r = _detailFiltered[idx];
  if (!r) return;
  _jsonPopupData = r;
  document.getElementById('jsonPopupTitle').textContent = `${r.service}/${r.type}: ${r.name}`;
  document.getElementById('jsonPopupContent').textContent = JSON.stringify(r, null, 2);
  document.getElementById('jsonPopup').style.display = 'flex';
}

function closeJsonPopup() {
  document.getElementById('jsonPopup').style.display = 'none';
  _jsonPopupData = null;
}

function downloadJsonPopup() {
  if (!_jsonPopupData) return;
  const blob = new Blob([JSON.stringify(_jsonPopupData, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${_jsonPopupData.service}_${_jsonPopupData.id}.json`;
  a.click();
}

// Close popup on ESC or outside click
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeJsonPopup(); });
document.getElementById('jsonPopup')?.addEventListener('click', e => { if (e.target.id === 'jsonPopup') closeJsonPopup(); });

// ---------------------------------------------------------------------------
// Compare Panel
// ---------------------------------------------------------------------------
function showComparePanel(p1, p2) {
  const panel = document.getElementById('comparePanel');
  const content = document.getElementById('compareContent');
  panel.style.display = 'block';

  const d1 = _scanData[p1], d2 = _scanData[p2];
  const sc1 = d1?.metadata?.service_counts || {};
  const sc2 = d2?.metadata?.service_counts || {};

  const allSvcs = new Set([...Object.keys(sc1), ...Object.keys(sc2)]);
  const matching = [], only1 = [], only2 = [];

  for (const svc of allSvcs) {
    if (sc1[svc] && sc2[svc]) matching.push(svc);
    else if (sc1[svc]) only1.push(svc);
    else only2.push(svc);
  }

  let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div class="metric-card"><div class="metric-label">${p1}</div><div class="metric-value" style="color:var(--accent)">${d1?.metadata?.resource_count || 0}</div></div>
    <div class="metric-card"><div class="metric-label">${p2}</div><div class="metric-value" style="color:#4da6ff">${d2?.metadata?.resource_count || 0}</div></div>
  </div>`;

  if (matching.length) {
    html += `<h4 style="color:var(--text-primary);margin:12px 0 8px">${t('mapinv_matching_services')} (${matching.length})</h4>`;
    html += '<table class="data-table"><thead><tr><th>Service</th><th>' + p1 + '</th><th>' + p2 + '</th><th>Diff</th></tr></thead><tbody>';
    for (const svc of matching.sort()) {
      const diff = (sc1[svc] || 0) - (sc2[svc] || 0);
      const diffColor = diff > 0 ? 'color:#00c87a' : diff < 0 ? 'color:#ff4d6a' : '';
      html += `<tr><td style="font-weight:600">${svc.toUpperCase()}</td><td>${sc1[svc]}</td><td>${sc2[svc]}</td><td style="${diffColor};font-weight:600">${diff > 0 ? '+' : ''}${diff}</td></tr>`;
    }
    html += '</tbody></table>';
  }

  if (only1.length) {
    html += `<h4 style="color:var(--accent);margin:16px 0 8px">${t('mapinv_only_in')} ${p1} (${only1.length})</h4>`;
    html += only1.sort().map(s => `<span class="tag" style="background:rgba(255,153,0,.15);color:var(--accent);margin:2px">${s.toUpperCase()} (${sc1[s]})</span>`).join('');
  }
  if (only2.length) {
    html += `<h4 style="color:#4da6ff;margin:16px 0 8px">${t('mapinv_only_in')} ${p2} (${only2.length})</h4>`;
    html += only2.sort().map(s => `<span class="tag" style="background:rgba(77,166,255,.15);color:#4da6ff;margin:2px">${s.toUpperCase()} (${sc2[s]})</span>`).join('');
  }

  content.innerHTML = html;
}

function closeComparePanel() {
  document.getElementById('comparePanel').style.display = 'none';
}

// ---------------------------------------------------------------------------
// Cache Management
// ---------------------------------------------------------------------------
async function clearProfileCache() {
  if (!_activeProfile) return;
  try {
    await fetch('/mapinventory/api/cache/clear', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ profile: _activeProfile }),
    });
    delete _scanData[_activeProfile];
    // Reset all dashboard state
    _allResources = [];
    _filteredResources = [];
    _filterSelected = { service: new Set(), region: new Set(), type: new Set() };
    destroyCharts();
    // Reset UI sections
    document.getElementById('scanInfoBar').style.display = 'none';
    document.getElementById('scanStatsSection').style.display = 'none';
    document.getElementById('chartsRow1').style.display = 'none';
    document.getElementById('chartsRow2').style.display = 'none';
    document.getElementById('filtersRow').style.display = 'none';
    document.getElementById('serviceTableSection').style.display = 'none';
    document.getElementById('detailPanel').style.display = 'none';
    // Reset overview header
    const countEl = document.getElementById('overviewResourceCount');
    if (countEl) countEl.textContent = '—';
    const summaryEl = document.getElementById('overviewSummaryLabel');
    if (summaryEl) summaryEl.textContent = '';
    // Reset metric cards to empty state
    document.getElementById('metricCards').innerHTML = `
      <div class="metric-card" style="grid-column:1/-1;text-align:center;padding:40px">
        <div class="state-empty">
          <div class="state-empty-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.3"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></div>
          <div class="state-empty-text">${t('mapinv_cache_cleared')}</div>
        </div>
      </div>`;
    _activeProfile = null;
    // Refresh scan history
    loadScanHistory();
  } catch(e) { console.error(e); }
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
let _reportGroups = {};

async function loadReportList() {
  try {
    const resp = await fetch('/mapinventory/api/reports/list');
    const data = await resp.json();
    if (data.status !== 'ok') return;

    const tbody = document.getElementById('reportListBody');
    const table = document.getElementById('reportListTable');
    const empty = document.getElementById('reportListEmpty');
    const selAll = document.getElementById('reportSelectAll');
    if (!tbody || !table || !empty) return;

    if (!data.reports || !data.reports.length) {
      table.style.display = 'none'; empty.style.display = 'block';
      _reportGroups = {};
      return;
    }

    // Group files by base key: mapinventory_{profile}_{YYYYMMDD}_{HHMMSS}
    const groups = {};
    for (const r of data.reports) {
      const m = r.filename.match(/^(mapinventory_.+_\d{8}_\d{6})\.(html|csv|pdf)$/);
      if (!m) continue;
      const base = m[1];
      if (!groups[base]) groups[base] = { base, mtime: r.mtime || 0, files: {} };
      groups[base].files[m[2]] = r;
      if ((r.mtime || 0) > groups[base].mtime) groups[base].mtime = r.mtime;
    }

    _reportGroups = groups;
    const sorted = Object.values(groups).sort((a, b) => b.mtime - a.mtime);
    if (!sorted.length) { table.style.display = 'none'; empty.style.display = 'block'; return; }

    const _esc = s => { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; };

    const fmtDate = ts => {
      if (!ts) return '—';
      return new Date(ts * 1000).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      });
    };

    const profileFromBase = base => {
      const m = base.match(/^mapinventory_(.+)_\d{8}_\d{6}$/);
      return m ? m[1] : base;
    };

    const fmtBadge = (label, color, file, target) => file
      ? `<a href="/mapinventory/reports/download/${encodeURIComponent(file.filename)}" ${target === '_blank' ? 'target="_blank" rel="noopener"' : `download="${_esc(file.filename)}"`}
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
          <div style="font-size:11px;color:var(--accent);margin-top:2px;font-weight:600">${_esc(profile)}</div>
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

function toggleSelectAllReports(cb) {
  document.querySelectorAll('.report-check').forEach(c => { c.checked = cb.checked; });
  updateDeleteBtnVisibility();
}

function onReportCheckChange() {
  const all = document.querySelectorAll('.report-check');
  const checked = document.querySelectorAll('.report-check:checked');
  const master = document.getElementById('reportSelectAll');
  if (master) {
    master.indeterminate = checked.length > 0 && checked.length < all.length;
    master.checked = checked.length === all.length && all.length > 0;
  }
  updateDeleteBtnVisibility();
}

function updateDeleteBtnVisibility() {
  const n = document.querySelectorAll('.report-check:checked').length;
  const btn = document.getElementById('deleteSelectedBtn');
  if (btn) btn.style.display = n >= 1 ? 'inline-flex' : 'none';
}

async function deleteReportGroup(base) {
  try {
    const resp = await fetch('/mapinventory/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases: [base] }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportList();
  } catch (_) { /* silent */ }
}

async function deleteSelectedReports() {
  const checked = [...document.querySelectorAll('.report-check:checked')];
  if (checked.length < 1) return;
  const bases = checked.map(cb => cb.dataset.base).filter(Boolean);
  if (!bases.length) return;
  try {
    const resp = await fetch('/mapinventory/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportList();
  } catch (_) { /* silent */ }
}

async function exportFormat(fmt) {
  if (!_activeProfile) return;
  try {
    const resp = await fetch('/mapinventory/api/reports/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ profile: _activeProfile, format: fmt }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportList();
  } catch(e) { /* silent */ }
}

function saveAndGoToReports() {
  if (!_activeProfile) return;
  fetch('/mapinventory/api/reports/generate_all', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ profile: _activeProfile }),
  }).then(() => {
    navigateTo('reports');
    loadReportList();
  });
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------
function navigateTo(section) {
  document.querySelectorAll('.page-section').forEach(s => s.style.display = 'none');
  const target = document.getElementById(`section-${section}`);
  if (target) target.style.display = 'block';

  document.querySelectorAll('.nav-item[data-section]').forEach(a => {
    a.classList.toggle('active', a.dataset.section === section);
  });

  if (section === 'reports') loadReportList();
}

function toggleProfileSection() {
  const section = document.getElementById('profileSection');
  if (section) section.classList.toggle('open');
}

function toggleChartsSection() {
  const section = document.getElementById('chartsSection');
  if (section) section.classList.toggle('open');
}

function toggleScanHistory() {
  const section = document.getElementById('scanHistorySection');
  if (section) section.classList.toggle('open');
}

function _fmtDuration(seconds) {
  if (!seconds || seconds <= 0) return '—';
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem > 0 ? `${m}m ${rem}s` : `${m}m`;
}

async function loadScanHistory() {
  const list = document.getElementById('scanHistoryList');
  const countEl = document.getElementById('scanHistoryCount');
  try {
    const resp = await fetch('/mapinventory/api/scan-history');
    const data = await resp.json();
    const scans = data.scans || [];
    if (countEl) countEl.textContent = scans.length;

    if (scans.length === 0) {
      list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px">' +
        (t('mapinv_no_scan_history') || 'No cached scans found') + '</div>';
      return;
    }

    const delSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

    // Show max 20 scans, table height fits ~10 rows then scrolls
    const displayScans = scans.slice(0, 20);
    let html = '<div style="max-height:370px;overflow-y:auto">';
    html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
    html += '<thead style="position:sticky;top:0;z-index:1;background:var(--bg-card)"><tr style="border-bottom:1px solid var(--border)">' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Profile</th>' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Account</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Resources</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Services</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Regions</th>' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Scan Time</th>' +
      '<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">Duration</th>' +
      '<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Age</th>' +
      '<th style="width:100px"></th>' +
      '</tr></thead><tbody>';

    for (const s of displayScans) {
      const ageMins = Math.round(s.age_seconds / 60);
      const ageStr = ageMins < 60 ? `${ageMins}m ago` : `${Math.round(ageMins / 60)}h ago`;
      const isActive = _activeProfile === s.profile;
      const safeProfile = s.profile.replace(/'/g, "\\'");
      html += `<tr style="border-bottom:1px solid var(--border);${isActive ? 'background:var(--accent-dim)' : ''}">
        <td style="padding:6px 12px;font-weight:600;color:var(--text-primary)">${s.profile}</td>
        <td style="padding:6px 12px;font-family:monospace;font-size:11px;color:var(--text-muted)">${s.account_id || '—'}</td>
        <td style="padding:6px 12px;text-align:right;color:var(--accent);font-weight:700">${formatNum(s.resource_count)}</td>
        <td style="padding:6px 12px;text-align:right;color:var(--text-secondary)">${s.services_count}</td>
        <td style="padding:6px 12px;text-align:right;color:var(--text-secondary)">${s.regions_count}</td>
        <td style="padding:6px 12px;color:var(--text-muted);font-size:11px">${s.timestamp || '—'}</td>
        <td style="padding:6px 12px;text-align:right;color:var(--text-secondary);font-size:11px;font-weight:600">${_fmtDuration(s.duration_seconds)}</td>
        <td style="padding:6px 12px;color:var(--text-muted);font-size:11px">${ageStr}</td>
        <td style="padding:4px 8px;text-align:right;white-space:nowrap">
          <button class="btn ${isActive ? 'btn-primary' : 'btn-outline'} btn-sm" style="font-size:10px;padding:2px 10px"
            onclick="viewScanHistory('${safeProfile}')">${isActive ? 'Active' : 'View'}</button>
          <button class="report-delete-btn" style="margin-left:4px;width:24px;height:24px" title="Delete scan"
            onclick="deleteScanHistoryItem('${safeProfile}')">${delSvg}</button>
        </td>
      </tr>`;
    }
    html += '</tbody></table></div>';
    list.innerHTML = html;
  } catch(e) {
    list.innerHTML = `<div style="text-align:center;padding:16px;color:#f87171;font-size:12px">${e.message}</div>`;
  }
}

async function viewScanHistory(profile) {
  // Load cached scan data and display
  try {
    const resp = await fetch(`/mapinventory/api/last-scan?profile=${encodeURIComponent(profile)}`);
    const data = await resp.json();
    if (data.status !== 'not_found' && data.metadata) {
      _scanData[profile] = data;
      displayScanResults(profile);
      loadScanHistory(); // refresh active state
    }
  } catch(e) { /* ignore */ }
}

async function deleteScanHistoryItem(profile) {
  try {
    await fetch('/mapinventory/api/cache/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile }),
    });
    loadScanHistory();
  } catch (_) {}
}

// ---------------------------------------------------------------------------
// Service Icons (SVG) — AWS-style distinctive icons per service
// ---------------------------------------------------------------------------
const _I = (d, w=16, h=16) => `<svg width="${w}" height="${h}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const SERVICE_ICONS = {
  _default:    _I('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'),
  // Compute
  ec2:         _I('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'),
  lambda:      _I('<path d="M4 20l5-16h2l3 10 3-10h2"/><line x1="3" y1="20" x2="21" y2="20"/>'),
  lightsail:   _I('<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'),
  autoscaling: _I('<path d="M16 3h5v5"/><path d="M8 21H3v-5"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>'),
  batch:       _I('<rect x="2" y="3" width="8" height="8" rx="1"/><rect x="14" y="3" width="8" height="8" rx="1"/><rect x="2" y="13" width="8" height="8" rx="1"/><rect x="14" y="13" width="8" height="8" rx="1"/>'),
  apprunner:   _I('<circle cx="12" cy="12" r="3"/><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/>'),
  elasticbeanstalk: _I('<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>'),
  // Containers
  ecs:         _I('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="22"/><line x1="2" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="22" y2="12"/>'),
  eks:         _I('<path d="M12 2l9 5v10l-9 5-9-5V7z"/><circle cx="12" cy="12" r="3"/>'),
  ecr:         _I('<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'),
  'ecr-public': _I('<path d="M22 12h-4l-3 9L9 3l-3 9H2"/><circle cx="12" cy="3" r="1"/>'),
  // Storage
  s3:          _I('<path d="M4 6c0-1.1 3.6-2 8-2s8 .9 8 2"/><path d="M4 6v12c0 1.1 3.6 2 8 2s8-.9 8-2V6"/><path d="M4 12c0 1.1 3.6 2 8 2s8-.9 8-2"/>'),
  efs:         _I('<path d="M3 7h18l-2 13H5z"/><path d="M8 7V4h8v3"/>'),
  fsx:         _I('<rect x="2" y="3" width="20" height="7" rx="1"/><rect x="2" y="14" width="20" height="7" rx="1"/><circle cx="6" cy="6.5" r="1"/><circle cx="6" cy="17.5" r="1"/>'),
  storagegateway: _I('<rect x="2" y="3" width="20" height="7" rx="1"/><rect x="2" y="14" width="20" height="7" rx="1"/><path d="M6 10v4"/>'),
  backup:      _I('<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>'),
  dlm:         _I('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'),
  datasync:    _I('<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
  // Database
  rds:         _I('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'),
  dynamodb:    _I('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>'),
  elasticache: _I('<circle cx="12" cy="12" r="10"/><path d="M8 12l2 2 4-4"/>'),
  redshift:    _I('<path d="M12 2L2 7v10l10 5 10-5V7z"/>'),
  'redshift-serverless': _I('<path d="M12 2L2 7v10l10 5 10-5V7z"/><circle cx="12" cy="12" r="2"/>'),
  neptune:     _I('<path d="M12 22c5.52 0 10-4.48 10-10S17.52 2 12 2 2 6.48 2 12s4.48 10 10 10z"/><path d="M8 12c0-2.21 1.79-4 4-4s4 1.79 4 4-1.79 4-4 4"/>'),
  docdb:       _I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><ellipse cx="12" cy="15" rx="4" ry="2"/>'),
  opensearch:  _I('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/><line x1="11" y1="8" x2="11" y2="14"/>'),
  'opensearch-serverless': _I('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'),
  memorydb:    _I('<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6"/><path d="M9 13h6"/><path d="M9 17h4"/>'),
  dax:         _I('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'),
  keyspaces:   _I('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'),
  timestream:  _I('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'),
  'timestream-influxdb': _I('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 8 14"/>'),
  dsql:        _I('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M9 12h6"/>'),
  // Networking
  vpc:         _I('<rect x="2" y="2" width="20" height="20" rx="3"/><rect x="6" y="6" width="12" height="12" rx="2" stroke-dasharray="3 2"/>'),
  'vpc-lattice': _I('<rect x="2" y="2" width="20" height="20" rx="3"/><path d="M7 12h10"/><path d="M12 7v10"/>'),
  elb:         _I('<path d="M12 2v6"/><path d="M6 14l6-6 6 6"/><path d="M4 20h16"/><circle cx="6" cy="20" r="1.5"/><circle cx="12" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/>'),
  elbv2:       _I('<path d="M12 2v6"/><path d="M6 14l6-6 6 6"/><path d="M4 20h16"/><circle cx="6" cy="20" r="1.5"/><circle cx="12" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/>'),
  cloudfront:  _I('<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'),
  route53:     _I('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10"/>'),
  route53domains: _I('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2c2.5 2.5 4 6 4 10s-1.5 7.5-4 10"/>'),
  route53resolver: _I('<circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/>'),
  apigateway:  _I('<path d="M4 4h16v16H4z"/><path d="M4 12h16"/><path d="M12 4v16"/>'),
  apigatewayv2: _I('<path d="M4 4h16v16H4z"/><path d="M4 12h16"/><path d="M12 4v16"/><circle cx="12" cy="12" r="2"/>'),
  directconnect: _I('<line x1="2" y1="12" x2="22" y2="12"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="12" r="3"/>'),
  'network-firewall': _I('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
  networkmanager: _I('<circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/>'),
  globalaccelerator: _I('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2v20"/><circle cx="12" cy="12" r="3"/>'),
  transfer:    _I('<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
  // Security & Identity
  iam:         _I('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
  kms:         _I('<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>'),
  secretsmanager: _I('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1"/>'),
  acm:         _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>'),
  'acm-pca':   _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><circle cx="12" cy="12" r="2"/>'),
  wafv2:       _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'),
  shield:      _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="16"/>'),
  guardduty:   _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><circle cx="12" cy="10" r="1"/><path d="M12 13v3"/>'),
  securityhub: _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M8 12h8"/><path d="M12 8v8"/>'),
  securitylake: _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M8 14c0-2.21 1.79-4 4-4s4 1.79 4 4"/>'),
  macie2:      _I('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><path d="M11 8v6"/><path d="M8 11h6"/>'),
  inspector2:  _I('<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>'),
  detective:   _I('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'),
  fms:         _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12h6"/>'),
  accessanalyzer: _I('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><circle cx="12" cy="7" r="1.5"/>'),
  cognito:     _I('<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>'),
  sso:         _I('<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>'),
  cloudhsmv2:  _I('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><rect x="10" y="14" width="4" height="4"/>'),
  // Management & Monitoring
  cloudwatch:  _I('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'),
  cloudtrail:  _I('<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>'),
  config:      _I('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
  ssm:         _I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M10 13l2 2 4-4"/>'),
  organizations: _I('<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M12 8v4"/><path d="M5 16v-2a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v2"/>'),
  cloudformation: _I('<path d="M12 2L2 7v10l10 5 10-5V7z"/><path d="M12 22V12"/><path d="M22 7L12 12 2 7"/>'),
  logs:        _I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="12" y2="17"/>'),
  'service-quotas': _I('<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>'),
  'resource-groups': _I('<rect x="2" y="7" width="8" height="8" rx="1"/><rect x="14" y="7" width="8" height="8" rx="1"/><rect x="8" y="14" width="8" height="8" rx="1"/>'),
  'resource-explorer': _I('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><rect x="8" y="8" width="6" height="6" rx="1"/>'),
  'compute-optimizer': _I('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/><path d="M12 2v4"/>'),
  auditmanager: _I('<path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 14l2 2 4-4"/>'),
  resiliencehub: _I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="8 12 12 16 16 8"/>'),
  synthetics:  _I('<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/><circle cx="12" cy="12" r="2"/>'),
  fis:         _I('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'),
  xray:        _I('<circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 0 20"/><circle cx="12" cy="12" r="4"/>'),
  health:      _I('<path d="M20.42 4.58a5.4 5.4 0 0 0-7.65 0L12 5.34l-.77-.76a5.4 5.4 0 0 0-7.65 0C1.46 6.7 1.33 10.28 4 13l8 8 8-8c2.67-2.72 2.54-6.3.42-8.42z"/>'),
  // Developer Tools
  codebuild:   _I('<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/><rect x="5" y="10" width="14" height="4" rx="1"/>'),
  codepipeline: _I('<circle cx="12" cy="5" r="3"/><circle cx="12" cy="19" r="3"/><line x1="12" y1="8" x2="12" y2="16"/><polyline points="8 13 12 16 16 13"/>'),
  codedeploy:  _I('<circle cx="12" cy="12" r="10"/><path d="M16 12l-4 4-4-4"/><path d="M12 8v8"/>'),
  codeartifact: _I('<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'),
  // Application Integration
  sqs:         _I('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'),
  sns:         _I('<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>'),
  events:      _I('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'),
  'eventbridge-scheduler': _I('<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><circle cx="12" cy="15" r="2"/>'),
  'eventbridge-pipes': _I('<path d="M4 12h16"/><circle cx="8" cy="12" r="3"/><circle cx="16" cy="12" r="3"/>'),
  schemas:     _I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h3"/><path d="M8 17h3"/>'),
  stepfunctions: _I('<circle cx="12" cy="4" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="20" r="2"/><line x1="12" y1="6" x2="12" y2="10"/><line x1="12" y1="14" x2="12" y2="18"/>'),
  mq:          _I('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 10h8"/><path d="M8 14h4"/>'),
  appsync:     _I('<circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/><circle cx="12" cy="12" r="3"/>'),
  appflow:     _I('<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
  // Analytics
  athena:      _I('<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>'),
  kinesis:     _I('<path d="M4 4c4 0 4 8 8 8s4-8 8-8"/><path d="M4 12c4 0 4 8 8 8s4-8 8-8"/><path d="M4 20c4 0 4-8 8-8"/>'),
  firehose:    _I('<path d="M4 4c4 0 4 8 8 8s4-8 8-8"/><path d="M4 12c4 0 4 8 8 8s4-8 8-8"/>'),
  glue:        _I('<circle cx="12" cy="12" r="3"/><line x1="12" y1="3" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="21"/><line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/>'),
  emr:         _I('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>'),
  'emr-serverless': _I('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/>'),
  redshift:    _I('<path d="M12 2L2 7v10l10 5 10-5V7z"/>'),
  lakeformation: _I('<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 15v7"/>'),
  datazone:    _I('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10"/>'),
  cleanrooms:  _I('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>'),
  quicksight:  _I('<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>'),
  grafana:     _I('<rect x="3" y="3" width="18" height="18" rx="2"/><polyline points="7 14 10 10 13 13 17 8"/>'),
  kafka:       _I('<circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/><line x1="5" y1="19" x2="19" y2="19"/>'),
  // ML & AI
  sagemaker:   _I('<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>'),
  bedrock:     _I('<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>'),
  comprehend:  _I('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 13h5"/>'),
  textract:    _I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h5"/><path d="M8 9h3"/>'),
  transcribe:  _I('<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>'),
  translate:   _I('<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'),
  polly:       _I('<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>'),
  rekognition: _I('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'),
  personalize: _I('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><path d="M16 11l2 2 4-4"/>'),
  frauddetector: _I('<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'),
  lexv2:       _I('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><circle cx="9" cy="10" r="1"/><circle cx="15" cy="10" r="1"/>'),
  kendra:      _I('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><path d="M11 7v8"/><path d="M7 11h8"/>'),
  // Email & Messaging
  sesv2:       _I('<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22 6 12 13 2 6"/>'),
  // Media
  mediatailor:  _I('<rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/>'),
  mediaconvert: _I('<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/>'),
  medialive:   _I('<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/><circle cx="8" cy="12" r="2"/>'),
  mediaconnect: _I('<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>'),
  mediapackage: _I('<rect x="2" y="7" width="20" height="15" rx="2"/><polyline points="17 2 12 7 7 2"/>'),
  mediastore:  _I('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/><path d="M6 8h4"/>'),
  // IoT
  iot:         _I('<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8" stroke-dasharray="4 3"/>'),
  iotsitewise: _I('<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 12h4l2-4 2 6 2-4h2"/>'),
  connect:     _I('<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.11 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>'),
  // End User / Workspaces
  workspaces:  _I('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/><rect x="6" y="7" width="12" height="6" rx="1"/>'),
  // Migration
  dms:         _I('<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
  // Cost
  budgets:     _I('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'),
  ce:          _I('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/><circle cx="12" cy="12" r="10"/>'),
  // Misc
  ram:         _I('<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>'),
  ds:          _I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6"/><path d="M9 15h6"/>'),
  imagebuilder: _I('<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>'),
  appconfig:   _I('<circle cx="12" cy="12" r="3"/><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/>'),
  amplify:     _I('<path d="M12 2L2 19h20z"/>'),
  amp:         _I('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/><circle cx="12" cy="12" r="2"/>'),
  mwaa:        _I('<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/><path d="M12 12v4"/>'),
  ivs:         _I('<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/>'),
  gamelift:    _I('<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>'),
  outposts:    _I('<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="8" y="8" width="8" height="8" rx="1"/>'),
  location:    _I('<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'),
  devicefarm:  _I('<rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>'),
  servicediscovery: _I('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>'),
  servicecatalog: _I('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'),
  serverlessrepo: _I('<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><circle cx="12" cy="12" r="3"/>'),
  'application-autoscaling': _I('<path d="M16 3h5v5"/><path d="M8 21H3v-5"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>'),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatBytes(bytes) {
  if (bytes == null) return '—';
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// ---------------------------------------------------------------------------
// Theme change handler
// ---------------------------------------------------------------------------
document.addEventListener('themechange', () => {
  if (_activeProfile && _scanData[_activeProfile]) {
    const meta = _scanData[_activeProfile].metadata || {};
    renderCharts(meta, _filteredResources.length < _allResources.length ? _filteredResources : _allResources);
  }
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  // Hash navigation
  const hash = location.hash.replace('#', '') || 'dashboard';
  navigateTo(hash);

  // Nav click handlers
  document.querySelectorAll('.nav-item[data-section]').forEach(a => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const section = a.dataset.section;
      history.pushState(null, '', `/mapinventory#${section}`);
      navigateTo(section);
    });
  });

  // Load profiles and services
  loadProfiles();
  loadServices().then(() => updateServiceLabel());

  // Load scan history and auto-load last scanned profile
  setTimeout(async () => {
    loadScanHistory();
    try {
      const resp = await fetch('/mapinventory/api/last-scanned-profile');
      const info = await resp.json();
      if (info.status === 'ok' && info.profile) {
        const profile = info.profile;
        const scanResp = await fetch(`/mapinventory/api/last-scan?profile=${encodeURIComponent(profile)}`);
        const data = await scanResp.json();
        if (data.status !== 'not_found' && data.metadata) {
          _scanData[profile] = data;
          displayScanResults(profile);
          loadScanHistory(); // refresh active state
        }
      }
    } catch(e) { /* ignore */ }
  }, 300);
});
