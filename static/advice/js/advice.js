/* ============================================================
   AWS FinSecOps — Advice Module JavaScript
   Independent from other module JS files.
   ============================================================ */

'use strict';

/* ── Constants ── */
const ROWS_PER_COL = 10;
const FAV_KEY      = 'advice_favorites';

const RISK_COLORS  = { HIGH: '#dc2626', MEDIUM: '#d97706', LOW: '#65a30d' };
const PILLAR_COLORS = {
  SEC: '#dc2626', OPS: '#3b82f6', REL: '#8b5cf6',
  PERF: '#06b6d4', COST: '#f59e0b', SUS: '#10b981',
};

/* Module icons (matching sidebar SVGs) */
const MODULE_ICONS = {
  SecOps: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  MapInventory: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
  FinOps: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
};

const MODULE_LABELS = {
  SecOps:       { en: 'SecOps',        tr: 'SecOps' },
  MapInventory: { en: 'Map Inventory', tr: 'Harita Envanter' },
  FinOps:       { en: 'FinOps',        tr: 'FinOps' },
};

const MODULE_URLS = {
  SecOps:       '/secops',
  MapInventory: '/mapinventory',
  FinOps:       '/',
};

const STEP_LABELS = {
  authenticating:       { en: 'Authenticating...',          tr: 'Kimlik dogrulamasi...' },
  loading_secops:       { en: 'Loading SecOps data...',     tr: 'SecOps verileri yukleniyor...' },
  loading_mapinventory: { en: 'Loading MapInventory data...', tr: 'MapInventory verileri yukleniyor...' },
  loading_finops:       { en: 'Loading FinOps data...',     tr: 'FinOps verileri yukleniyor...' },
  analyzing:            { en: 'Analyzing WAFR compliance...', tr: 'WAFR uyumlulugu analiz ediliyor...' },
  summarizing:          { en: 'Generating report...',       tr: 'Rapor olusturuluyor...' },
  done:                 { en: 'Done',                       tr: 'Tamamlandi' },
};

/* ── State ── */
let _profiles         = [];        // sorted profile name strings
let _ssoSet           = new Set(); // SSO-enabled profile names
let _selectedProfile  = null;      // single selected profile
let _favorites        = new Set(JSON.parse(localStorage.getItem(FAV_KEY) || '[]'));
let _availableRegions = [];
let _selectedRegions  = [];
let _assessmentData   = null;
let _pollInterval     = null;
let _reportGroups     = {};   // base_key → { base, mtime, files: {html,pdf_tr,pdf_en} }

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  loadProfiles();
  loadAssessmentHistory();
  handleHash();
  window.addEventListener('hashchange', handleHash);

  // Close region dropdown on outside click
  document.addEventListener('click', (e) => {
    const dd = document.getElementById('regionDropdown');
    if (dd && dd.style.display === 'block') {
      if (!e.target.closest('#regionPicker')) dd.style.display = 'none';
    }
  });
});

function handleHash() {
  const hash = location.hash.replace('#', '');
  const isReports = hash === 'reports';
  document.getElementById('section-dashboard').style.display = isReports ? 'none' : '';
  document.getElementById('section-reports').style.display = isReports ? '' : 'none';
  if (isReports) loadReportList();

  document.querySelectorAll('.nav-item[data-section]').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-section') === (hash || 'dashboard'));
  });
}

/* ═══════════════════════════════════════════════════════════════
   Profile Loading & Grid
   ═══════════════════════════════════════════════════════════════ */

async function loadProfiles() {
  const container = document.getElementById('profileList');
  if (!container) return;
  container.innerHTML = '<div style="color:var(--text-muted);font-size:13px;padding:10px;grid-column:1/-1"><span class="spinner"></span> Loading...</div>';
  try {
    const resp = await fetch('/advice/api/profiles');
    const data = await resp.json();
    const raw  = data.profiles || [];
    _profiles = raw.map(p => typeof p === 'string' ? p : p.name)
                   .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
    _ssoSet   = new Set(raw.filter(p => p.sso).map(p => p.name));
    renderProfileGrid();
    renderFavoritesBar();
    updateAssessBtn();
  } catch (e) {
    container.innerHTML = `<div style="color:var(--red);padding:10px">${e.message}</div>`;
  }
}

function renderProfileGrid() {
  const container = document.getElementById('profileList');
  if (!container) return;
  if (!_profiles.length) {
    container.innerHTML = `<div style="color:var(--text-muted);font-size:13px">${t('advice_no_profiles')}</div>`;
    return;
  }
  const countEl = document.getElementById('profileCount');
  if (countEl) countEl.textContent = _profiles.length;

  const numCols = Math.ceil(_profiles.length / ROWS_PER_COL);
  const colsHtml = Array.from({ length: numCols }, (_, ci) => {
    const rows = _profiles.slice(ci * ROWS_PER_COL, ci * ROWS_PER_COL + ROWS_PER_COL)
      .map((p, ri) => {
        const idx     = ci * ROWS_PER_COL + ri;
        const sel     = p === _selectedProfile;
        const starred = _favorites.has(p);
        const sso     = _ssoSet.has(p) ? '<span class="sso-badge">SSO</span>' : '';
        return `<div class="profile-row${sel ? ' selected' : ''}" data-idx="${idx}">
          <div class="profile-row-check">${sel ? ICONS.check : ''}</div>
          <div class="profile-row-name" title="${p}">${p}</div>
          ${sso}
          <button class="star-btn${starred ? ' starred' : ''}" data-star="1" title="${starred ? 'Remove favorite' : 'Add to favorites'}">
            ${starred ? ICONS.starFilled : ICONS.starOutline}
          </button>
        </div>`;
      }).join('');
    return `<div class="profile-col">${rows}</div>`;
  }).join('');

  container.innerHTML = colsHtml;

  // Event delegation
  container.onclick = (e) => {
    const row = e.target.closest('.profile-row[data-idx]');
    if (!row) return;
    const name = _profiles[parseInt(row.dataset.idx, 10)];
    if (e.target.closest('[data-star]')) {
      toggleFavorite(name);
    } else {
      selectProfile(name);
    }
  };
}

function saveFavorites() {
  localStorage.setItem(FAV_KEY, JSON.stringify([..._favorites]));
}

function toggleFavorite(name) {
  if (_favorites.has(name)) _favorites.delete(name); else _favorites.add(name);
  saveFavorites();
  renderProfileGrid();
  renderFavoritesBar();
}

/* ═══════════════════════════════════════════════════════════════
   Favorites Bar
   ═══════════════════════════════════════════════════════════════ */

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
    if (btn) {
      const chip = btn.closest('[data-fav-idx]');
      if (chip) {
        const name = favs[parseInt(chip.dataset.favIdx, 10)];
        toggleFavorite(name);
      }
      return;
    }
    // Click on chip itself → select that profile
    const chip = e.target.closest('[data-fav-idx]');
    if (chip) {
      const name = favs[parseInt(chip.dataset.favIdx, 10)];
      selectProfile(name);
    }
  };
}

function analyzeFavorites() {
  // Select first favorite and run assessment
  const favs = [..._favorites].filter(f => _profiles.includes(f));
  if (favs.length > 0) {
    selectProfile(favs[0]);
    setTimeout(() => startAssessment(), 500);
  }
}

/* ═══════════════════════════════════════════════════════════════
   Profile Selection
   ═══════════════════════════════════════════════════════════════ */

async function selectProfile(name) {
  _selectedProfile = name;
  _selectedRegions = [];
  _availableRegions = [];
  renderProfileGrid();
  renderFavoritesBar();
  updateSelectedLabel();
  updateAssessBtn();

  // Load regions
  await loadRegions(name);
  // Check prerequisites
  await checkPrerequisites(name);
  // Try loading last assessment
  await loadLastAssessment(name);
}

function updateSelectedLabel() {
  const el = document.getElementById('selectedProfileLabel');
  if (el) el.textContent = _selectedProfile || '';
}

function updateAssessBtn() {
  const btn = document.getElementById('assessBtn');
  const enabled = _selectedProfile && _selectedRegions.length > 0;
  btn.disabled = !enabled;
}

/* ═══════════════════════════════════════════════════════════════
   Region Dropdown
   ═══════════════════════════════════════════════════════════════ */

async function loadRegions(profile) {
  const content = document.getElementById('regionDropdownContent');
  if (content) content.innerHTML = `<span style="padding:8px;display:block;color:var(--text-muted);font-size:12px">${t('advice_loading_regions')}</span>`;
  updateRegionPickerLabel();

  try {
    const resp = await fetch(`/advice/api/regions?profile=${encodeURIComponent(profile)}`);
    if (resp.status === 401) {
      showSSOBanner(profile);
      _availableRegions = [];
      renderRegionDropdown();
      return;
    }
    hideSSOBanner();
    _availableRegions = await resp.json();
    // Default: select all
    _selectedRegions = [..._availableRegions];
    renderRegionDropdown();
    updateRegionPickerLabel();
    updateAssessBtn();
  } catch (e) {
    const isSso = e.message && (e.message.toLowerCase().includes('sso') || e.message.toLowerCase().includes('expired') || e.message.toLowerCase().includes('token') || e.message.toLowerCase().includes('credential'));
    if (isSso) {
      showSSOBanner(profile);
      _availableRegions = [];
      renderRegionDropdown();
      return;
    }
    if (content) content.innerHTML = `<span style="padding:8px;display:block;color:#dc2626;font-size:12px">${e.message}</span>`;
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

function renderRegionDropdown() {
  const content = document.getElementById('regionDropdownContent');
  if (!content) return;
  if (!_availableRegions.length) {
    content.innerHTML = '<span style="color:var(--text-muted);font-size:12px;padding:8px;display:block">No regions found</span>';
    return;
  }
  const sorted = [..._availableRegions].sort();
  let html = `
    <div style="padding:8px 10px 6px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg-card);z-index:1">
      <div style="display:flex;gap:6px;margin-bottom:6px">
        <button class="btn btn-outline btn-sm" onclick="selectAllRegions();event.stopPropagation()" style="font-size:10px;padding:2px 8px" data-i18n="advice_select_all">Select All</button>
        <button class="btn btn-outline btn-sm" onclick="clearAllRegions();event.stopPropagation()" style="font-size:10px;padding:2px 8px" data-i18n="advice_clear_all">Clear</button>
      </div>
      <input type="text" id="regionSearch" placeholder="Search regions..." oninput="filterRegionDropdown(this.value)"
        onclick="event.stopPropagation()"
        style="width:100%;box-sizing:border-box;padding:5px 9px;border:1px solid var(--border);border-radius:5px;
               background:var(--bg-base);color:var(--text-primary);font-size:12px;outline:none">
    </div>
    <div id="regionList" style="display:flex;flex-direction:column;max-height:320px;overflow-y:auto">`;
  for (const r of sorted) {
    const checked = _selectedRegions.includes(r);
    html += `<label class="region-label" data-region="${r}"
        style="display:flex;align-items:center;gap:8px;padding:6px 14px;font-size:12px;cursor:pointer;
               border-bottom:1px solid var(--border);white-space:nowrap;transition:background .1s"
        onmouseover="this.style.background='var(--bg-base)'" onmouseout="this.style.background=''">
      <input type="checkbox" class="region-cb" value="${r}" ${checked ? 'checked' : ''} onchange="onRegionChange()" style="accent-color:var(--accent);flex-shrink:0">
      <span style="color:var(--text-secondary);font-family:monospace;letter-spacing:.3px">${r}</span>
    </label>`;
  }
  html += '</div>';
  content.innerHTML = html;
}

function filterRegionDropdown(query) {
  const list = document.getElementById('regionList');
  if (!list) return;
  const q = query.toLowerCase();
  list.querySelectorAll('.region-label').forEach(lbl => {
    const region = lbl.dataset.region || '';
    lbl.style.display = region.toLowerCase().includes(q) ? 'flex' : 'none';
  });
}

function onRegionChange() {
  _selectedRegions = [];
  document.querySelectorAll('.region-cb:checked').forEach(cb => {
    _selectedRegions.push(cb.value);
  });
  updateRegionPickerLabel();
  updateAssessBtn();
}

function selectAllRegions() {
  _selectedRegions = [..._availableRegions];
  renderRegionDropdown();
  updateRegionPickerLabel();
  updateAssessBtn();
}

function clearAllRegions() {
  _selectedRegions = [];
  renderRegionDropdown();
  updateRegionPickerLabel();
  updateAssessBtn();
}

function updateRegionPickerLabel() {
  const el = document.getElementById('regionPickerLabel');
  if (!el) return;
  if (_selectedRegions.length === 0) {
    el.textContent = t('advice_select_regions');
  } else if (_selectedRegions.length === _availableRegions.length && _availableRegions.length > 0) {
    el.textContent = `All Regions (${_selectedRegions.length})`;
  } else {
    el.textContent = `${_selectedRegions.length} Regions`;
  }
}

/* ═══════════════════════════════════════════════════════════════
   Prerequisites Check
   ═══════════════════════════════════════════════════════════════ */

async function checkPrerequisites(profile) {
  try {
    const resp = await fetch(`/advice/api/prerequisites?profile=${encodeURIComponent(profile)}`);
    const data = await resp.json();
    renderPrereqBanner(data);
    return data;
  } catch (e) {
    return { ready: false, missing: [], available: {} };
  }
}

function renderPrereqBanner(data) {
  const banner  = document.getElementById('prereqBanner');
  const modsEl  = document.getElementById('prereqModules');
  const hintEl  = document.getElementById('prereqHint');
  const titleEl = document.getElementById('prereqTitle');
  if (!banner || !modsEl) return;

  const lang    = localStorage.getItem('finops_lang') || 'en';
  const missing = new Set(data.missing || []);
  const avail   = data.available || {};

  // All three modules to show
  const modules = ['SecOps', 'MapInventory', 'FinOps'];

  modsEl.innerHTML = modules.map(mod => {
    const key       = mod.toLowerCase().replace('inventory', 'inventory');
    const isReady   = !missing.has(mod) || avail[key];
    const isMissing = missing.has(mod);
    const icon      = MODULE_ICONS[mod] || '';
    const label     = MODULE_LABELS[mod] ? (MODULE_LABELS[mod][lang] || MODULE_LABELS[mod].en) : mod;
    const url       = MODULE_URLS[mod] || '#';

    // Build detail text
    let detail = '';
    if (isMissing) {
      detail = lang === 'tr' ? 'Tarama gerekli' : 'Scan required';
    } else if (avail[key]) {
      const info = avail[key];
      if (info.score !== undefined) {
        detail = `Score: ${info.score}%`;
      } else if (info.resource_count !== undefined) {
        detail = `${info.resource_count} ${lang === 'tr' ? 'kaynak' : 'resources'}`;
      } else if (info.status === 'live_fetch') {
        detail = lang === 'tr' ? 'Canlı veri' : 'Live data';
      }
      if (info.scan_time) {
        detail += ` · ${info.scan_time}`;
      }
    }

    const borderColor = isMissing ? '#d97706' : '#16a34a';
    const bgColor     = isMissing ? '#d9770610' : '#16a34a10';
    const statusIcon  = isMissing
      ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
      : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';

    return `<div style="flex:1;min-width:180px;max-width:280px;background:${bgColor};border:1px solid ${borderColor}44;border-radius:8px;padding:12px 14px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
        <span style="display:flex;color:${borderColor}">${icon}</span>
        <span style="font-size:13px;font-weight:600;color:var(--text-primary)">${label}</span>
        <span style="margin-left:auto;display:flex">${statusIcon}</span>
      </div>
      <div style="font-size:11px;color:var(--text-muted);line-height:1.4;margin-bottom:${isMissing ? '8' : '0'}px">${detail}</div>
      ${isMissing ? `<a href="${url}" style="font-size:11px;color:var(--accent);text-decoration:none;font-weight:600">${lang === 'tr' ? 'Taramaya Git →' : 'Go to Scan →'}</a>` : ''}
    </div>`;
  }).join('');

  // Title and hint
  if (missing.size > 0) {
    titleEl.textContent = lang === 'tr' ? 'Eksik Modül Taramaları' : 'Missing Module Scans';
    hintEl.textContent  = lang === 'tr'
      ? 'Analiz başlatmak için yukarıdaki eksik modüllerin taramalarını önce çalıştırmanız gerekiyor.'
      : 'You need to run the missing module scans before starting an assessment.';
    hintEl.style.display = '';
  } else {
    titleEl.textContent = lang === 'tr' ? 'Modül Durumu' : 'Module Status';
    hintEl.textContent  = lang === 'tr'
      ? 'Tüm modül taramaları mevcut. Analiz başlatabilirsiniz.'
      : 'All module scans are available. You can start the assessment.';
    hintEl.style.display = '';
  }

  banner.style.display = 'block';
}

/* ═══════════════════════════════════════════════════════════════
   SSO Banner
   ═══════════════════════════════════════════════════════════════ */

function showSSOBanner(profile) {
  const banner = document.getElementById('ssoBanner');
  document.getElementById('ssoCmd').textContent = `aws sso login --profile ${profile}`;
  banner.style.display = 'block';
}

function hideSSOBanner() {
  document.getElementById('ssoBanner').style.display = 'none';
}

/* ═══════════════════════════════════════════════════════════════
   Assessment
   ═══════════════════════════════════════════════════════════════ */

async function startAssessment() {
  if (!_selectedProfile) return;
  if (_selectedRegions.length === 0) {
    showInlineWarning(t('advice_select_regions_warning'));
    return;
  }

  const btn = document.getElementById('assessBtn');
  btn.disabled = true;

  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('resultsSection').style.display = 'none';
  showProgress();

  try {
    const resp = await fetch('/advice/api/assess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile: _selectedProfile,
        regions: _selectedRegions,
      }),
    });
    const data = await resp.json();

    if (data.error === 'prerequisites_missing') {
      hideProgress();
      // Re-check and show the inline prereq banner with module statuses
      const prereqs = await checkPrerequisites(_selectedProfile);
      updateAssessBtn();
      return;
    }

    if (data.error === 'regions required') {
      hideProgress();
      showInlineWarning(t('advice_select_regions_warning'));
      updateAssessBtn();
      return;
    }

    if (data.error) {
      hideProgress();
      showInlineWarning(data.error);
      updateAssessBtn();
      return;
    }

    // Start polling
    _pollInterval = setInterval(() => pollProgress(), 800);
  } catch (e) {
    hideProgress();
    showInlineWarning(e.message);
    updateAssessBtn();
  }
}

async function pollProgress() {
  try {
    const resp = await fetch(`/advice/api/assess-progress?profile=${encodeURIComponent(_selectedProfile)}`);
    const data = await resp.json();

    if (data.done) {
      clearInterval(_pollInterval);
      _pollInterval = null;
      hideProgress();
      await loadLastAssessment(_selectedProfile);
      loadAssessmentHistory();
      updateAssessBtn();
      // Auto-generate all report formats (HTML + PDF TR + PDF EN)
      autoGenerateReports(_selectedProfile);
      return;
    }

    const pct = data.percent || 0;
    document.getElementById('progressBar').style.width = pct + '%';
    document.getElementById('progressLabel').textContent = pct + '%';

    const step = data.step || '';
    const lang = localStorage.getItem('finops_lang') || 'en';
    const label = STEP_LABELS[step] ? (STEP_LABELS[step][lang] || STEP_LABELS[step].en) : step;
    document.getElementById('progressStep').textContent = label;
    document.getElementById('progressCount').textContent = `${data.completed || 0} / ${data.total || 0}`;
  } catch (e) {
    // ignore poll errors
  }
}

function showProgress() {
  document.getElementById('progressSection').style.display = 'block';
  document.getElementById('progressBar').style.width = '0%';
  document.getElementById('progressLabel').textContent = '0%';
  document.getElementById('progressStep').textContent = '\u2014';
  document.getElementById('progressCount').textContent = '0 / 0';
}

function hideProgress() {
  document.getElementById('progressSection').style.display = 'none';
}

async function autoGenerateReports(profile) {
  if (!profile) return;
  try {
    await fetch('/advice/api/reports/generate_all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile }),
    });
    // Refresh report list if on reports page
    if (location.hash === '#reports') loadReportList();
  } catch (e) {
    console.error('Auto report generation failed:', e);
  }
}

function showInlineWarning(msg) {
  const banner = document.getElementById('prereqBanner');
  const modsEl = document.getElementById('prereqModules');
  const hintEl = document.getElementById('prereqHint');
  const titleEl = document.getElementById('prereqTitle');
  if (!banner) return;

  const lang = localStorage.getItem('finops_lang') || 'en';
  titleEl.textContent = lang === 'tr' ? 'Uyarı' : 'Warning';
  modsEl.innerHTML = '';
  hintEl.textContent = msg;
  hintEl.style.display = '';
  banner.style.display = 'block';
}

/* ═══════════════════════════════════════════════════════════════
   Load Last Assessment & Info Bar
   ═══════════════════════════════════════════════════════════════ */

async function loadLastAssessment(profile) {
  if (!profile) return;
  try {
    const resp = await fetch(`/advice/api/last-assessment?profile=${encodeURIComponent(profile)}`);
    const data = await resp.json();
    if (data.status === 'no_data') {
      document.getElementById('emptyState').style.display = 'block';
      document.getElementById('resultsSection').style.display = 'none';
      document.getElementById('scanInfoBar').style.display = 'none';
      return;
    }
    if (data.status === 'ok') {
      _assessmentData = data;
      renderScanInfoBar(data);
      renderResults(data);
    }
  } catch (e) {
    console.error('Failed to load assessment:', e);
  }
}

function renderScanInfoBar(data) {
  const bar = document.getElementById('scanInfoBar');
  bar.style.display = 'flex';

  document.getElementById('infoProfile').textContent = data.profile || '\u2014';
  document.getElementById('infoAccountId').textContent = data.account_id || '\u2014';
  document.getElementById('infoScanTime').textContent = data.timestamp || '\u2014';

  const ageSec = data.cache_age_seconds || 0;
  const ageMins = Math.round(ageSec / 60);
  const ageStr = ageMins < 60 ? `${ageMins}m ago` : `${Math.round(ageMins / 60)}h ago`;
  document.getElementById('infoCacheAge').textContent = ageStr;
}

/* ═══════════════════════════════════════════════════════════════
   Assessment History
   ═══════════════════════════════════════════════════════════════ */

async function loadAssessmentHistory() {
  const list    = document.getElementById('historyList');
  const countEl = document.getElementById('historyCount');
  try {
    const resp  = await fetch('/advice/api/assessment-history');
    const scans = await resp.json();
    if (countEl) countEl.textContent = scans.length;

    if (scans.length === 0) {
      list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px">' +
        (t('advice_no_reports') || 'No assessments yet') + '</div>';
      return;
    }

    const delSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

    let html = '<div style="max-height:400px;overflow-y:auto">';
    html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
    html += '<thead style="position:sticky;top:0;z-index:1;background:var(--bg-card)"><tr style="border-bottom:1px solid var(--border)">' +
      `<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Profile</th>` +
      `<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Account</th>` +
      `<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">${t('advice_high_risk')}</th>` +
      `<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">${t('advice_medium_risk')}</th>` +
      `<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">${t('advice_low_risk')}</th>` +
      `<th style="text-align:right;padding:6px 12px;color:var(--text-muted);font-weight:600">${t('advice_positive')}</th>` +
      `<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Scan</th>` +
      `<th style="text-align:left;padding:6px 12px;color:var(--text-muted);font-weight:600">Age</th>` +
      `<th style="width:100px"></th>` +
      '</tr></thead><tbody>';

    for (const s of scans) {
      const ageMins  = Math.round(s.age_seconds / 60);
      const ageStr   = ageMins < 60 ? `${ageMins}m ago` : `${Math.round(ageMins / 60)}h ago`;
      const isActive = _selectedProfile === s.profile;
      const safeProfile = s.profile.replace(/'/g, "\\'");
      html += `<tr style="border-bottom:1px solid var(--border);${isActive ? 'background:var(--accent-dim)' : ''}">
        <td style="padding:6px 12px;font-weight:600;color:var(--text-primary)">${s.profile}</td>
        <td style="padding:6px 12px;font-family:monospace;font-size:11px;color:var(--text-muted)">${s.account_id || '\u2014'}</td>
        <td style="padding:6px 12px;text-align:right;color:#dc2626;font-weight:700">${s.risk_high || 0}</td>
        <td style="padding:6px 12px;text-align:right;color:#d97706;font-weight:700">${s.risk_medium || 0}</td>
        <td style="padding:6px 12px;text-align:right;color:#65a30d;font-weight:700">${s.risk_low || 0}</td>
        <td style="padding:6px 12px;text-align:right;color:#16a34a;font-weight:700">${s.total_positive || 0}</td>
        <td style="padding:6px 12px;color:var(--text-muted);font-size:11px">${s.timestamp || '\u2014'}</td>
        <td style="padding:6px 12px;color:var(--text-muted);font-size:11px">${ageStr}</td>
        <td style="padding:4px 12px;text-align:right;white-space:nowrap;min-width:100px">
          <button class="btn ${isActive ? 'btn-primary' : 'btn-outline'} btn-sm" style="font-size:10px;padding:2px 10px"
            onclick="viewHistory('${safeProfile}')">${isActive ? 'Active' : 'View'}</button>
          <button class="report-delete-btn" style="margin-left:6px" title="Delete assessment"
            onclick="event.stopPropagation();deleteAssessmentHistory('${safeProfile}')">${delSvg}</button>
        </td>
      </tr>`;
    }
    html += '</tbody></table></div>';
    list.innerHTML = html;
  } catch (e) {
    list.innerHTML = `<div style="text-align:center;padding:16px;color:#f87171;font-size:12px">${e.message}</div>`;
  }
}

async function viewHistory(profile) {
  _selectedProfile = profile;
  renderProfileGrid();
  updateSelectedLabel();
  await loadLastAssessment(profile);
  loadAssessmentHistory();
}

async function deleteAssessmentHistory(profile) {
  try {
    const resp = await fetch('/advice/api/assessment-history/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile }),
    });
    const data = await resp.json();
    if (data.status === 'ok') {
      loadAssessmentHistory();
      // If deleted assessment was active, clear dashboard
      if (_selectedProfile === profile) {
        _selectedProfile = '';
        _assessmentData = null;
        const resultsEl = document.getElementById('resultsSection');
        if (resultsEl) resultsEl.style.display = 'none';
        const emptyEl = document.getElementById('emptyState');
        if (emptyEl) emptyEl.style.display = '';
      }
    }
  } catch (_) { /* silent */ }
}

/* ═══════════════════════════════════════════════════════════════
   Collapsible Sections
   ═══════════════════════════════════════════════════════════════ */

function toggleProfileSection() {
  const section = document.getElementById('profileSection');
  if (section) section.classList.toggle('open');
}

function toggleHistorySection() {
  const section = document.getElementById('historySection');
  if (section) section.classList.toggle('open');
}

/* ═══════════════════════════════════════════════════════════════
   Render Results
   ═══════════════════════════════════════════════════════════════ */

function renderResults(data) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('resultsSection').style.display = 'block';

  renderSummaryCards(data);
  renderPillarBars(data.pillar_scores || {});
  renderServiceAssessments(data.services || []);
}

function renderSummaryCards(data) {
  const s    = data.summary || {};
  const risk = s.risk_counts || {};

  const html = `
    <div class="chart-card" style="padding:14px 20px;min-width:120px">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px">${t('advice_profile')}</div>
      <div style="font-size:16px;font-weight:700;color:var(--accent);margin-top:4px">${data.profile || ''}</div>
      <div style="font-size:10px;color:var(--text-muted);margin-top:2px">Account: ${data.account_id || ''}</div>
    </div>
    <div class="chart-card" style="padding:14px 20px;min-width:100px">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px">${t('advice_high_risk')}</div>
      <div style="font-size:28px;font-weight:700;color:#dc2626;margin-top:4px">${risk.HIGH || 0}</div>
    </div>
    <div class="chart-card" style="padding:14px 20px;min-width:100px">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px">${t('advice_medium_risk')}</div>
      <div style="font-size:28px;font-weight:700;color:#d97706;margin-top:4px">${risk.MEDIUM || 0}</div>
    </div>
    <div class="chart-card" style="padding:14px 20px;min-width:100px">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px">${t('advice_low_risk')}</div>
      <div style="font-size:28px;font-weight:700;color:#65a30d;margin-top:4px">${risk.LOW || 0}</div>
    </div>
    <div class="chart-card" style="padding:14px 20px;min-width:100px">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px">${t('advice_positive')}</div>
      <div style="font-size:28px;font-weight:700;color:#16a34a;margin-top:4px">${s.total_positive || 0}</div>
    </div>
    <div class="chart-card" style="padding:14px 20px;min-width:100px">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px">${t('advice_services')}</div>
      <div style="font-size:28px;font-weight:700;color:#3b82f6;margin-top:4px">${s.services_analyzed || 0}</div>
    </div>`;

  document.getElementById('summaryCards').innerHTML = html;
}

function renderPillarBars(pillars) {
  const el   = document.getElementById('pillarBars');
  const lang = localStorage.getItem('finops_lang') || 'en';
  let html   = '';

  for (const [code, info] of Object.entries(pillars)) {
    const color = PILLAR_COLORS[code] || '#888';
    const name  = lang === 'tr' ? (info.name_tr || info.name_en) : info.name_en;
    const score = info.score || 0;
    html += `
    <div style="flex:1;min-width:140px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-size:11px;font-weight:600;color:var(--text-primary)">${name}</span>
        <span style="font-size:11px;font-weight:600;color:${color}">${score}%</span>
      </div>
      <div style="height:8px;background:var(--bg-base);border-radius:4px;overflow:hidden">
        <div style="height:100%;width:${score}%;background:${color};border-radius:4px;transition:width .5s"></div>
      </div>
      <div style="font-size:9px;color:var(--text-muted);margin-top:2px">${info.findings || 0} ${t('advice_findings_label')} / ${info.positive || 0} ${t('advice_positive_label')}</div>
    </div>`;
  }

  el.innerHTML = html;
}

function renderServiceAssessments(services) {
  const el   = document.getElementById('serviceAssessments');
  const lang = localStorage.getItem('finops_lang') || 'en';
  let html   = '';

  for (const svc of services) {
    const catName  = lang === 'tr' ? (svc.category_tr || svc.category_en) : svc.category_en;
    const findings = svc.findings || [];
    const recs     = svc.recommendations || [];
    const positive = svc.positive || [];

    html += `<div class="chart-card" style="margin-bottom:10px;overflow:hidden;padding:0">`;
    html += `<div style="padding:10px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;cursor:pointer" onclick="toggleSvcSection(this)">
      <div style="font-size:13px;font-weight:600;color:var(--accent)">${catName}</div>
      <div style="display:flex;gap:6px;align-items:center">
        ${findings.length ? `<span style="background:#dc262620;color:#dc2626;padding:1px 7px;border-radius:8px;font-size:9px;font-weight:600">${findings.length} ${t('advice_findings_label')}</span>` : ''}
        ${recs.length ? `<span style="background:#10b98120;color:#10b981;padding:1px 7px;border-radius:8px;font-size:9px;font-weight:600">${recs.length} ${t('advice_recs_label')}</span>` : ''}
        ${positive.length ? `<span style="background:#16a34a20;color:#16a34a;padding:1px 7px;border-radius:8px;font-size:9px;font-weight:600">${positive.length} ${t('advice_positive_label')}</span>` : ''}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transition:transform .2s;transform:rotate(180deg)"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
    </div>`;

    html += '<div class="svc-body" style="padding:12px 16px">';

    // Findings
    if (findings.length) {
      html += `<div style="margin-bottom:10px">
        <div style="font-size:11px;font-weight:600;color:#f87171;margin-bottom:6px">${t('advice_findings_title')} (${findings.length})</div>`;
      for (const f of findings) {
        const rc = RISK_COLORS[f.risk] || '#888';
        const text = lang === 'tr' ? (f.text_tr || f.text_en) : f.text_en;
        const wafrLinks = (f.wafr_codes || []).map(c =>
          `<a href="${getWafrDocUrl(c)}" target="_blank" style="color:var(--accent);text-decoration:none;font-weight:600;font-size:11px">${c}</a>`
        ).join(' ');
        const resource = f.resource_id ? `<span style="font-family:monospace;font-size:10px;color:var(--text-muted);margin-left:6px">[${f.resource_id}]</span>` : '';
        const region   = f.region ? `<span style="font-size:10px;color:var(--text-muted);margin-left:4px">(${f.region})</span>` : '';

        html += `<div style="margin-bottom:6px;padding:8px 12px;background:var(--bg-base);border-left:3px solid ${rc};border-radius:4px">
          <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap">
            <span style="background:${rc};color:#fff;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:600">${f.risk}</span>
            ${wafrLinks}${region}${resource}
          </div>
          <div style="margin-top:4px;font-size:12px;line-height:1.5;color:var(--text-primary)">${text}</div>
        </div>`;
      }
      html += '</div>';
    }

    // Recommendations
    if (recs.length) {
      html += `<div style="margin-bottom:10px">
        <div style="font-size:11px;font-weight:600;color:#10b981;margin-bottom:6px">${t('advice_recs_title')} (${recs.length})</div>`;
      for (const r of recs) {
        const text = lang === 'tr' ? (r.text_tr || r.text_en) : r.text_en;
        const wafrLinks = (r.wafr_codes || []).map(c =>
          `<a href="${getWafrDocUrl(c)}" target="_blank" style="color:var(--accent);text-decoration:none;font-weight:600;font-size:10px">${c}</a>`
        ).join(' ');
        html += `<div style="margin-bottom:5px;padding:7px 12px;background:var(--bg-base);border-left:3px solid #10b981;border-radius:4px">
          <div>${wafrLinks}</div>
          <div style="margin-top:3px;font-size:12px;line-height:1.5;color:var(--text-primary)">${text}</div>
        </div>`;
      }
      html += '</div>';
    }

    // Positive
    if (positive.length) {
      html += `<div>
        <div style="font-size:11px;font-weight:600;color:#16a34a;margin-bottom:6px">${t('advice_positive_title')} (${positive.length})</div>`;
      for (const p of positive) {
        const text = lang === 'tr' ? (p.text_tr || p.text_en) : p.text_en;
        html += `<div style="margin-bottom:3px;padding:5px 12px;background:var(--bg-base);border-left:3px solid #16a34a;border-radius:4px;font-size:11px;color:var(--text-primary)">&#10003; ${text}</div>`;
      }
      html += '</div>';
    }

    html += '</div></div>';
  }

  el.innerHTML = html;
}

function toggleSvcSection(header) {
  const body  = header.nextElementSibling;
  const arrow = header.querySelector('svg');
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (arrow) arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
}

/* ═══════════════════════════════════════════════════════════════
   WAFR Doc URL helper
   ═══════════════════════════════════════════════════════════════ */

function getWafrDocUrl(code) {
  const pillar = code.replace(/[0-9]/g, '');
  const pillarMap = {
    SEC:  'security-pillar',
    OPS:  'operational-excellence-pillar',
    REL:  'reliability-pillar',
    PERF: 'performance-efficiency-pillar',
    COST: 'cost-optimization-pillar',
    SUS:  'sustainability-pillar',
  };
  const base = pillarMap[pillar] || 'framework';
  return `https://docs.aws.amazon.com/wellarchitected/latest/${base}/welcome.html`;
}

/* ═══════════════════════════════════════════════════════════════
   Reports (SecOps-style)
   ═══════════════════════════════════════════════════════════════ */

async function loadReportList() {
  const statusEl = document.getElementById('reportStatus');
  try {
    const resp = await fetch('/advice/api/reports/list');
    const data = await resp.json();

    const tbody = document.getElementById('reportListBody');
    const table = document.getElementById('reportListTable');
    const empty = document.getElementById('reportListEmpty');
    const selAll = document.getElementById('reportSelectAll');
    if (!tbody || !table || !empty) return;

    if (!data.length) {
      table.style.display = 'none';
      empty.style.display = 'block';
      _reportGroups = {};
      return;
    }

    // Group files by base key: advice_{profile}_{YYYYMMDD}_{HHMMSS}
    // Files: .html, _tr.pdf, _en.pdf (new) or .html/.csv/.pdf (legacy)
    const groups = {};
    for (const r of data) {
      // New naming: advice_xxx_20260312_143000.html, advice_xxx_20260312_143000_tr.pdf, advice_xxx_20260312_143000_en.pdf
      let base, ftype;
      const mNew = r.filename.match(/^(advice_.+_\d{8}_\d{6})_(tr|en)\.pdf$/);
      if (mNew) {
        base = mNew[1];
        ftype = 'pdf_' + mNew[2]; // pdf_tr or pdf_en
      } else {
        const mOld = r.filename.match(/^(advice_.+_\d{8}_\d{6})\.(html|csv|pdf)$/);
        if (!mOld) continue;
        base = mOld[1];
        ftype = mOld[2]; // html, csv, pdf (legacy)
      }
      if (!groups[base]) groups[base] = { base, mtime: r.modified, files: {} };
      groups[base].files[ftype] = r;
      if (r.modified > groups[base].mtime) groups[base].mtime = r.modified;
    }

    _reportGroups = groups;
    const sorted = Object.values(groups).sort((a, b) => b.mtime - a.mtime);
    if (!sorted.length) { table.style.display = 'none'; empty.style.display = 'block'; return; }

    const fmtDate = ts => new Date(ts * 1000).toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });

    const profileFromBase = base => {
      const m = base.match(/^advice_(.+)_\d{8}_\d{6}$/);
      return m ? m[1] : base;
    };

    const fmtBadge = (label, color, file, target) => file
      ? `<a href="/advice/reports/download/${file.filename}" ${target === '_blank' ? 'target="_blank" rel="noopener"' : `download="${file.filename}"`}
            title="Download ${label}"
            style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;background:${color}22;color:${color};border:1px solid ${color}44;text-decoration:none;transition:background .15s"
            onmouseover="this.style.background='${color}44'" onmouseout="this.style.background='${color}22'">${label}</a>`
      : `<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;background:var(--bg-card);color:var(--text-muted);border:1px solid var(--border);opacity:.4">${label}</span>`;

    tbody.innerHTML = sorted.map(g => {
      const safe    = g.base.replace(/'/g, "\\'");
      const html    = g.files['html'];
      const pdfTr   = g.files['pdf_tr'];
      const pdfEn   = g.files['pdf_en'];
      const pdfLegacy = g.files['pdf'];  // legacy single pdf
      const profile = profileFromBase(g.base);

      const delSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

      return `<tr class="report-row">
        <td style="text-align:center;width:36px">
          <input type="checkbox" class="report-check" data-base="${safe}"
                 style="accent-color:var(--accent);width:14px;height:14px;cursor:pointer"
                 onchange="onReportCheckChange()">
        </td>
        <td style="font-size:12px">
          <div style="font-weight:600;color:var(--text-primary)">${fmtDate(g.mtime)}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px">${profile}</div>
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:nowrap">
            ${fmtBadge('HTML', '#3b82f6', html, '_blank')}
            ${pdfTr || pdfEn
              ? `${fmtBadge('PDF TR', '#f97316', pdfTr)}${fmtBadge('PDF EN', '#f97316', pdfEn)}`
              : fmtBadge('PDF', '#f97316', pdfLegacy)}
          </div>
        </td>
        <td style="text-align:center;width:40px">
          <button class="report-delete-btn" onclick="deleteReportGroup('${safe}')" title="${t('advice_delete') || 'Delete'}">
            ${delSvg}
          </button>
        </td>
      </tr>`;
    }).join('');

    if (selAll) selAll.checked = false;
    table.style.display = '';
    empty.style.display = 'none';
    updateExportStatus();
  } catch (e) { /* silent */ }
}

function toggleSelectAllReports(masterCb) {
  document.querySelectorAll('.report-check').forEach(cb => { cb.checked = masterCb.checked; });
  updateExportStatus();
}

function onReportCheckChange() {
  const all     = document.querySelectorAll('.report-check');
  const checked = document.querySelectorAll('.report-check:checked');
  const master  = document.getElementById('reportSelectAll');
  if (master) {
    master.indeterminate = checked.length > 0 && checked.length < all.length;
    master.checked       = checked.length === all.length && all.length > 0;
  }
  updateExportStatus();
}

function updateExportStatus() {
  const n  = document.querySelectorAll('.report-check:checked').length;
  const btn = document.getElementById('deleteSelectedBtn');
  if (btn) btn.style.display = n >= 2 ? 'inline-flex' : 'none';
}

async function deleteReportGroup(base) {
  try {
    const resp = await fetch('/advice/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases: [base] }),
    });
    const data = await resp.json();
    if (data.status === 'ok') {
      loadReportList();
    }
  } catch (e) {
    console.error('Delete failed:', e);
  }
}

async function deleteSelectedReports() {
  const checked = [...document.querySelectorAll('.report-check:checked')];
  if (checked.length < 2) return;

  const bases = checked.map(cb => cb.dataset.base).filter(Boolean);
  if (!bases.length) return;

  try {
    const resp = await fetch('/advice/api/reports/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bases }),
    });
    const data = await resp.json();
    if (data.status === 'ok') loadReportList();
  } catch (e) {
    console.error('Bulk delete failed:', e);
  }
}
