/* ============================================================
   Topology Module — Main JavaScript
   JointJS + ELK.js interactive network topology visualization
   Independent from FinOps, SecOps, MapInventory
   ============================================================ */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────
  let _profiles = [];
  let _profileSearch = '';
  let _ssoSet = new Set();
  let _selectedProfile = null;
  let _selectedRegions = [];
  let _availableRegions = [];
  let _scanData = null;
  let _paper = null;
  let _graph = null;
  let _currentView = 'basic';
  let _currentDiagram = 'vpc-arch';
  let _visibleTypes = new Set();
  let _pollInterval = null;
  let _customLabels = {};   // nodeId → user label
  let _highlightedNodeId = null;  // connection highlight state
  let _contextMenuData = null;    // right-click context data
  let _minimapVisible = true;
  let _selectedRegionFilter = ''; // region filter for diagram
  const ROWS_PER_COL = 10;

  // Pan/zoom state
  let _currentScale = 1;
  let _isPanning = false;
  let _panStart = { x: 0, y: 0 };
  const MIN_SCALE = 0.15;
  const MAX_SCALE = 3;

  // ELK instance
  const _elk = new ELK();

  // Profile search helpers
  function getFilteredProfiles() {
    if (!_profileSearch) return _profiles;
    const q = _profileSearch.toLowerCase();
    return _profiles.filter(p => p.toLowerCase().includes(q));
  }

  // AWS-style colors for resource types
  const TYPE_COLORS = {
    vpc:             '#ff9900',
    subnet:          '#1a73e8',
    igw:             '#e53935',
    nat:             '#43a047',
    route_table:     '#8e24aa',
    peering:         '#00acc1',
    security_group:  '#f4511e',
    nacl:            '#6d4c41',
    vpc_endpoint:    '#546e7a',
    eip:             '#fdd835',
    eni:             '#6b7280',
    ec2:             '#ff9900',
    ecs_cluster:     '#ff9900',
    ecs_service:     '#ff6600',
    rds:             '#2e7d32',
    elb:             '#7b1fa2',
    lambda:          '#ff6f00',
    transit_gateway: '#d32f2f',
    tgw_attachment:  '#c62828',
    direct_connect:  '#1565c0',
    dx_gateway:      '#0d47a1',
    vpn_gateway:     '#8c4fff',
    vpn_connection:  '#7c3aed',
    customer_gateway:'#6d28d9',
    network_firewall:'#dc2626',
    acm:             '#00897b',
    eks:             '#ff9900',
    api_gateway:     '#8b5cf6',
    cloudfront:      '#7c4dff',
    s3:              '#43a047',
    hosted_zone:     '#2563eb',
    organization:    '#ff9900',
    org_account:     '#ffa726',
  };

  const TYPE_LABELS = {
    vpc: 'VPC', subnet: 'Subnet', igw: 'Internet GW', nat: 'NAT GW',
    route_table: 'Route Table', peering: 'VPC Peering', security_group: 'Security Group',
    nacl: 'NACL', vpc_endpoint: 'VPC Endpoint', eip: 'Elastic IP', eni: 'ENI',
    ec2: 'EC2', ecs_cluster: 'ECS Cluster', ecs_service: 'ECS Service',
    rds: 'RDS', elb: 'Load Balancer', lambda: 'Lambda',
    transit_gateway: 'Transit GW', tgw_attachment: 'TGW Attach', direct_connect: 'Direct Connect',
    dx_gateway: 'DX Gateway', vpn_gateway: 'VPN GW', vpn_connection: 'VPN',
    customer_gateway: 'Customer GW', network_firewall: 'Network FW',
    acm: 'ACM', eks: 'EKS', api_gateway: 'API Gateway', cloudfront: 'CloudFront',
    s3: 'S3', hosted_zone: 'Route53 Zone', organization: 'Organization', org_account: 'Account',
  };

  const VIEW_LEVELS = {
    basic:    ['vpc', 'subnet', 'igw', 'nat', 'route_table', 'peering'],
    medium:   ['vpc', 'subnet', 'igw', 'nat', 'route_table', 'peering',
               'security_group', 'nacl', 'vpc_endpoint', 'eip'],
    detailed: Object.keys(TYPE_COLORS),
  };

  // ── Section Navigation (SecOps pattern) ──────────────────
  function showSection(name) {
    // Hide all page sections
    document.querySelectorAll('.page-section').forEach(s => s.style.display = 'none');
    // Show target section
    const target = document.getElementById('section-' + name);
    if (target) target.style.display = '';
    // Update sidebar active state
    document.querySelectorAll('.nav-item[data-section]').forEach(a => a.classList.remove('active'));
    const link = document.querySelector(`.nav-item[data-section="${name}"]`);
    if (link) link.classList.add('active');
    // Update hash without scroll
    history.replaceState(null, '', '#' + name);
    // Auto-load reports when navigating to reports
    if (name === 'reports') loadReports();
  }

  // ── Init ──────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    loadProfiles();
    setupEventListeners();
    loadLastScan();
    loadScanHistory();
    setupSectionNav();
  }

  // ── Profiles (MapInventory column-major grid pattern) ─────
  async function loadProfiles() {
    const container = document.getElementById('profileList');
    if (!container) return;
    container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:10px;grid-column:1/-1"><span class="spinner"></span> Loading...</div>`;
    try {
      const resp = await fetch('/topology/api/profiles');
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
        .map((p) => {
          const idx = _profiles.indexOf(p);
          const sel = _selectedProfile === p;
          const sso = _ssoSet.has(p) ? '<span class="sso-badge">SSO</span>' : '';
          return `<div class="profile-row${sel?' selected':''}" data-idx="${idx}">
            <div class="profile-row-check">${sel ? (typeof ICONS !== 'undefined' ? ICONS.check : '&#10003;') : ''}</div>
            <div class="profile-row-name" title="${escHtml(p)}">${escHtml(p)}</div>
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
      selectProfile(name);
    };
  }

  function selectProfile(name) {
    _selectedProfile = name;
    _selectedRegions = [];
    renderProfileGrid();
    updateScanBtn();
    updateSelectedLabel();
    // Clear any previous SSO banner
    const ssoBanner = document.querySelector('.topo-sso-banner');
    if (ssoBanner) ssoBanner.remove();
    loadRegions(name);
    loadCachedScan(name);
  }

  function updateScanBtn() {
    const btn = document.getElementById('scanBtn');
    if (btn) btn.disabled = !_selectedProfile;
  }

  function updateSelectedLabel() {
    const el = document.getElementById('selectedProfileLabel');
    if (el) el.textContent = _selectedProfile || '';
  }

  function selectAllProfiles() {
    // Topology is single-select, so select the first profile
    if (_profiles.length > 0) selectProfile(_profiles[0]);
  }

  function clearProfiles() {
    _selectedProfile = null;
    _selectedRegions = [];
    renderProfileGrid();
    updateScanBtn();
    updateSelectedLabel();
  }

  // ── Profile search ─────────────────────────────────────────
  function onProfileSearch(value) {
    _profileSearch = value || '';
    renderProfileGrid();
    const clearBtn = document.getElementById('topoProfileSearchClear');
    if (clearBtn) clearBtn.style.display = _profileSearch ? 'flex' : 'none';
  }

  function clearProfileSearch() {
    const input = document.getElementById('topoProfileSearchInput');
    if (input) input.value = '';
    _profileSearch = '';
    renderProfileGrid();
    const clearBtn = document.getElementById('topoProfileSearchClear');
    if (clearBtn) clearBtn.style.display = 'none';
  }

  // ── Collapse toggles (exposed globally for onclick) ───────
  window._topoToggleProfileSection = function() {
    const section = document.getElementById('profileSection');
    if (section) section.classList.toggle('open');
  };
  window._topoToggleScanHistory = function() {
    const section = document.getElementById('scanHistorySection');
    if (section) section.classList.toggle('open');
  };
  window._topoRefreshHistory = function() { loadScanHistory(); };
  window._topoToggleRegionDropdown = function() {
    const dd = document.getElementById('regionDropdown');
    if (!dd) return;
    const opening = dd.style.display === 'none' || dd.style.display === '';
    if (opening) {
      const search = document.getElementById('regionSearch');
      if (search) { search.value = ''; filterRegionDropdown(''); }
    }
    dd.style.display = opening ? 'block' : 'none';
  };

  // ── Regions (MapInventory pattern) ────────────────────────
  async function loadRegions(profile) {
    const content = document.getElementById('regionDropdownContent');
    if (!content) return;
    content.innerHTML = '<span class="spinner" style="padding:8px"></span>';
    try {
      const resp = await fetch(`/topology/api/regions?profile=${encodeURIComponent(profile)}`);
      const data = await resp.json();
      if (data.status === 'ok') {
        _availableRegions = data.regions || [];
        _selectedRegions = [];
        renderRegionDropdown();
        updateRegionLabel();
      } else if (data.error && _isSsoError(data.error)) {
        showSSOBanner(profile, data.error);
        _availableRegions = [];
        renderRegionDropdown();
      } else if (data.error) {
        content.innerHTML = `<span style="color:var(--red);padding:8px;font-size:11px">${escHtml(data.error)}</span>`;
      }
    } catch(e) {
      if (_isSsoError(e.message)) {
        showSSOBanner(profile, e.message);
      }
      content.innerHTML = `<span style="color:var(--red);padding:8px;font-size:11px">${escHtml(e.message)}</span>`;
    }
  }

  function renderRegionDropdown() {
    const content = document.getElementById('regionDropdownContent');
    if (!content) return;
    if (!_availableRegions.length) {
      content.innerHTML = '<span style="color:var(--text-muted);font-size:12px;padding:8px;display:block">No regions found</span>';
      return;
    }
    const sorted = [..._availableRegions].sort();
    let html = `<div style="padding:8px 10px 6px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg-card);z-index:1">
      <input type="text" id="regionSearch" placeholder="Search regions..."
        onclick="event.stopPropagation()"
        style="width:100%;box-sizing:border-box;padding:5px 9px;border:1px solid var(--border);border-radius:5px;background:var(--bg-base);color:var(--text-primary);font-size:12px;outline:none">
    </div>
    <div id="regionList" style="display:flex;flex-direction:column;max-height:320px;overflow-y:auto">`;
    for (const r of sorted) {
      const checked = _selectedRegions.includes(r);
      html += `<label class="region-label" data-region="${r}"
        style="display:flex;align-items:center;gap:8px;padding:6px 14px;font-size:12px;cursor:pointer;border-bottom:1px solid var(--border);white-space:nowrap;transition:background .1s"
        onmouseover="this.style.background='var(--bg-base)'" onmouseout="this.style.background=''">
        <input type="checkbox" class="region-cb" value="${r}" ${checked ? 'checked' : ''} style="accent-color:var(--accent);flex-shrink:0">
        <span style="color:var(--text-secondary);font-family:monospace;letter-spacing:.3px">${r}</span>
      </label>`;
    }
    html += '</div>';
    content.innerHTML = html;

    const searchInput = content.querySelector('#regionSearch');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => filterRegionDropdown(e.target.value));
    }
    content.addEventListener('change', (e) => {
      if (e.target.classList.contains('region-cb')) {
        onRegionChange();
      }
    });
  }

  function filterRegionDropdown(query) {
    const q = query.toLowerCase().trim();
    document.querySelectorAll('.region-label').forEach(label => {
      const region = label.dataset.region || '';
      label.style.display = region.includes(q) ? '' : 'none';
    });
  }

  function onRegionChange() {
    _selectedRegions = [...document.querySelectorAll('.region-cb:checked')].map(cb => cb.value);
    updateRegionLabel();
  }

  function updateRegionLabel() {
    const el = document.getElementById('regionPickerLabel');
    if (!el) return;
    if (_selectedRegions.length === 0) {
      el.textContent = t('topo_select_regions') || 'Select Regions';
    } else {
      el.textContent = `${_selectedRegions.length} Region${_selectedRegions.length > 1 ? 's' : ''}`;
    }
  }

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    const dd = document.getElementById('regionDropdown');
    const picker = document.getElementById('regionPicker');
    if (dd && picker && !picker.contains(e.target)) {
      dd.style.display = 'none';
    }
  });

  function _isSsoError(msg) {
    if (!msg) return false;
    const m = msg.toLowerCase();
    return m.includes('sso') || m.includes('expired') || m.includes('token') ||
           m.includes('unauthorizedsso') || m.includes('credential');
  }

  function showSSOBanner(profile, error) {
    const existing = document.querySelector('.topo-sso-banner');
    if (existing) existing.remove();
    const cmd = `aws sso login --profile ${profile}`;
    const banner = document.createElement('div');
    banner.className = 'topo-sso-banner';
    banner.style.cssText = 'background:#3d1a1a;border:1px solid #c0392b;border-radius:8px;padding:8px 14px;margin-bottom:10px;font-size:12px;color:#f5c6c6;display:flex;align-items:center;gap:8px;flex-wrap:wrap';
    banner.innerHTML = `<span>${t('secops_sso_expired') || 'SSO session expired for'} <b>${escHtml(profile)}</b>. ${t('secops_sso_run') || 'Run:'}</span>
      <code id="topoSsoCmd" style="background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.15);padding:3px 10px;border-radius:4px;font-size:11px;font-family:monospace;user-select:all">${escHtml(cmd)}</code>
      <button onclick="navigator.clipboard.writeText('${escHtml(cmd)}').then(()=>{this.textContent='✓ ${t('secops_copied') || 'Copied'}';setTimeout(()=>{this.textContent='${t('secops_copy') || 'Copy'}'},2000)})"
        style="padding:3px 10px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:4px;color:#f5c6c6;font-size:11px;cursor:pointer;white-space:nowrap">${t('secops_copy') || 'Copy'}</button>`;
    document.getElementById('profileSection').after(banner);
  }

  // ── Scan ──────────────────────────────────────────────────
  async function clearProfileCache() {
    if (!_selectedProfile) return;
    try {
      await fetch('/topology/api/cache/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: _selectedProfile }),
      });
      document.getElementById('scanInfoBar').style.display = 'none';
      document.getElementById('topoResults').style.display = 'none';
      document.getElementById('emptyState').style.display = '';
      _scanData = null;
      loadScanHistory();
    } catch(e) { console.error(e); }
  }

  window._topoStartScan = startScan;

  async function startScan() {
    if (!_selectedProfile) return;
    if (_selectedRegions.length === 0) {
      alert(t('topo_select_regions_first') || 'Please select regions first');
      return;
    }

    const excludeDefaults = document.getElementById('excludeDefaults')?.checked ?? false;

    document.getElementById('progressSection').style.display = '';
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('scanBtn').disabled = true;

    try {
      await fetch('/topology/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: _selectedProfile, regions: _selectedRegions, exclude_defaults: excludeDefaults }),
      });
      pollProgress();
    } catch (e) {
      console.error('Scan failed', e);
      document.getElementById('scanBtn').disabled = false;
    }
  }

  function pollProgress() {
    if (_pollInterval) clearInterval(_pollInterval);
    _pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/topology/api/scan-progress?profile=${encodeURIComponent(_selectedProfile)}`);
        const data = await res.json();
        if (data.status !== 'ok') return;

        document.getElementById('progressPercent').textContent = `${data.percent}%`;
        document.getElementById('progressBar').style.width = `${data.percent}%`;
        document.getElementById('progressService').textContent = data.service || '';
        document.getElementById('progressCount').textContent = `${data.completed}/${data.total}`;

        if (data.done) {
          clearInterval(_pollInterval);
          _pollInterval = null;
          document.getElementById('progressSection').style.display = 'none';
          document.getElementById('scanBtn').disabled = false;

          if (data.error) {
            alert(data.error);
          } else {
            loadCachedScan(_selectedProfile);
            loadScanHistory();
          }
        }
      } catch (e) { /* ignore poll errors */ }
    }, 800);
  }

  async function loadCachedScan(profile) {
    try {
      const res = await fetch(`/topology/api/last-scan?profile=${encodeURIComponent(profile)}`);
      const data = await res.json();
      if (data.status === 'not_found') return;
      if (data.resources) {
        _scanData = data;
        showResults();
      }
    } catch (e) { console.error('Failed to load cached scan', e); }
  }

  async function loadLastScan() {
    try {
      const res = await fetch('/topology/api/last-scanned-profile');
      const data = await res.json();
      if (data.status === 'ok' && data.profile) {
        selectProfile(data.profile);
      }
    } catch (e) { /* no cached scan */ }
  }

  // ── Scan History ──────────────────────────────────────────
  async function loadScanHistory() {
    try {
      const res = await fetch('/topology/api/scan-history');
      const data = await res.json();
      if (data.status !== 'ok') return;
      const scans = data.scans || [];
      document.getElementById('scanHistoryCount').textContent = scans.length;
      const list = document.getElementById('scanHistoryList');
      if (scans.length === 0) {
        list.innerHTML = `<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:12px">${t('topo_no_scan_history') || 'No cached scans found'}</div>`;
        return;
      }
      const delSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';
      list.innerHTML = '<div style="max-height:400px;overflow-y:auto">' + scans.map(s => {
        const mins = Math.round(s.age_seconds / 60);
        const safeProfile = s.profile.replace(/'/g, "\\'");
        return `<div class="topo-history-row" data-profile="${escHtml(s.profile)}">
          <strong style="color:var(--accent);min-width:140px">${escHtml(s.profile)}</strong>
          <span style="color:var(--text-muted)">${s.account_id || ''}</span>
          <span style="color:var(--text-muted)">${s.resource_count} resources</span>
          <span style="color:var(--text-muted)">${s.regions_count} regions</span>
          <span style="color:var(--text-muted);margin-left:auto">${mins}m ago</span>
          <button class="btn-sm" onclick="event.stopPropagation()">${t('secops_report_open') || 'View'}</button>
          <button class="report-delete-btn" style="margin-left:4px;width:24px;height:24px;flex-shrink:0" title="Delete scan"
            onclick="event.stopPropagation();window._topoDeleteScanHistoryItem('${safeProfile}')">${delSvg}</button>
        </div>`;
      }).join('') + '</div>';
    } catch (e) { /* ignore */ }
  }

  async function deleteScanHistoryItem(profile) {
    try {
      await fetch('/topology/api/cache/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile }),
      });
      loadScanHistory();
    } catch (_) { /* silent */ }
  }
  window._topoDeleteScanHistoryItem = deleteScanHistoryItem;

  // ── Show Results ──────────────────────────────────────────
  function showResults() {
    if (!_scanData) return;
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('topoResults').style.display = '';

    const meta = _scanData.metadata || {};
    const resources = _scanData.resources || [];
    const tc = meta.type_counts || {};

    document.getElementById('metricVpcs').textContent = tc.vpc || 0;
    document.getElementById('metricSubnets').textContent = tc.subnet || 0;
    document.getElementById('metricResources').textContent = meta.resource_count || 0;
    document.getElementById('metricRegions').textContent = meta.regions_scanned || 0;
    document.getElementById('metricDuration').textContent = `${meta.scan_duration_seconds || 0}s`;

    const bar = document.getElementById('scanInfoBar');
    bar.style.display = 'flex';
    document.getElementById('infoProfile').textContent = _scanData.profile || '';
    document.getElementById('infoAccountId').textContent = _scanData.account_id || '';
    document.getElementById('infoScanTime').textContent = meta.timestamp || '';
    const cacheAge = _scanData._cache_age_seconds;
    if (cacheAge !== undefined) {
      const hrs = Math.floor(cacheAge / 3600);
      const mins = Math.round((cacheAge % 3600) / 60);
      document.getElementById('infoCacheAge').textContent = hrs > 0 ? `${hrs}h ago` : `${mins}m ago`;
    }

    const vpcs = resources.filter(r => r.type === 'vpc');
    const sel = document.getElementById('vpcSelector');
    sel.innerHTML = `<option value="">${t('topo_all_vpcs') || 'All VPCs'}</option>` +
      vpcs.map(v => `<option value="${v.id}">${escHtml(v.name)} (${v.cidr || ''})</option>`).join('');

    // Populate region filter
    const regionFilter = document.getElementById('regionFilter');
    if (regionFilter) {
      const regions = [...new Set(resources.map(r => r.region).filter(Boolean))].sort();
      regionFilter.innerHTML = `<option value="">${t('topo_all_regions') || 'All Regions'}</option>` +
        regions.map(r => `<option value="${r}">${r}</option>`).join('');
    }

    _visibleTypes = new Set(VIEW_LEVELS[_currentView]);
    renderFilterPanel();
    renderDiagram();
    updateWatermark();
  }

  // ── Filter Panel ──────────────────────────────────────────
  function renderFilterPanel() {
    const container = document.getElementById('filterChecks');
    if (!container) return;
    const types = VIEW_LEVELS.detailed;
    container.innerHTML = types.map(t => {
      const checked = _visibleTypes.has(t) ? 'checked' : '';
      const color = TYPE_COLORS[t] || '#888';
      return `<label class="topo-filter-check">
        <input type="checkbox" value="${t}" ${checked}>
        <span class="type-dot" style="background:${color}"></span>
        <span>${TYPE_LABELS[t] || t}</span>
      </label>`;
    }).join('');
  }

  // ── AWS Official Icons (CDN) ──────────────────────────────
  const _ICON_CDN = 'https://cdn.jsdelivr.net/npm/aws-icons@3.2.0/icons';
  const AWS_ICONS = {
    vpc:             `${_ICON_CDN}/architecture-service/AmazonVirtualPrivateCloud.svg`,
    igw:             `${_ICON_CDN}/resource/AmazonVPCInternetGateway.svg`,
    nat:             `${_ICON_CDN}/resource/AmazonVPCNATGateway.svg`,
    ec2:             `${_ICON_CDN}/architecture-service/AmazonEC2.svg`,
    rds:             `${_ICON_CDN}/architecture-service/AmazonRDS.svg`,
    elb:             `${_ICON_CDN}/architecture-service/ElasticLoadBalancing.svg`,
    lambda:          `${_ICON_CDN}/architecture-service/AWSLambda.svg`,
    eks:             `${_ICON_CDN}/architecture-service/AmazonElasticKubernetesService.svg`,
    s3:              `${_ICON_CDN}/architecture-service/AmazonSimpleStorageService.svg`,
    cloudfront:      `${_ICON_CDN}/architecture-service/AmazonCloudFront.svg`,
    transit_gateway: `${_ICON_CDN}/architecture-service/AWSTransitGateway.svg`,
    direct_connect:  `${_ICON_CDN}/architecture-service/AWSDirectConnect.svg`,
    acm:             `${_ICON_CDN}/architecture-service/AWSCertificateManager.svg`,
    security_group:  `${_ICON_CDN}/architecture-service/AWSSecurityHub.svg`,
    route_table:     `${_ICON_CDN}/resource/AmazonRoute53RouteTable.svg`,
    peering:         `${_ICON_CDN}/resource/AmazonVPCPeeringConnection.svg`,
    eip:             `${_ICON_CDN}/resource/AmazonEC2ElasticIPAddress.svg`,
    nacl:            `${_ICON_CDN}/resource/AmazonVPCNetworkAccessControlList.svg`,
    vpc_endpoint:    `${_ICON_CDN}/resource/AmazonVPCEndpoints.svg`,
    eni:             `${_ICON_CDN}/resource/AmazonEC2ElasticNetworkInterface.svg`,
    ecs_cluster:     `${_ICON_CDN}/architecture-service/AmazonElasticContainerService.svg`,
    ecs_service:     `${_ICON_CDN}/architecture-service/AmazonElasticContainerService.svg`,
    vpn_gateway:     `${_ICON_CDN}/resource/AmazonVPCVPNGateway.svg`,
    vpn_connection:  `${_ICON_CDN}/architecture-service/AWSSitetoSiteVPN.svg`,
    customer_gateway:`${_ICON_CDN}/resource/AmazonVPCCustomerGateway.svg`,
    network_firewall:`${_ICON_CDN}/architecture-service/AWSNetworkFirewall.svg`,
    api_gateway:     `${_ICON_CDN}/architecture-service/AmazonAPIGateway.svg`,
    hosted_zone:     `${_ICON_CDN}/architecture-service/AmazonRoute53.svg`,
    organization:    `${_ICON_CDN}/architecture-service/AWSOrganizations.svg`,
    org_account:     `${_ICON_CDN}/architecture-service/AWSOrganizations.svg`,
  };

  // ── Smart label truncation ────────────────────────────────
  function shortLabel(resource, maxLen) {
    if (_customLabels[resource.id]) return _customLabels[resource.id];
    maxLen = maxLen || 18;
    const name = resource.name || resource.id || '';
    const type = resource.type || '';

    if (type === 'subnet') {
      const azSuffix = (resource.az || '').split('-').pop() || '';
      const pubPriv = resource.is_public ? 'Public' : 'Private';
      let short = name;
      if (_selectedProfile) {
        const prefix = _selectedProfile.toLowerCase().replace(/[^a-z0-9]/g, '');
        const nameLower = name.toLowerCase().replace(/[^a-z0-9-]/g, '');
        if (nameLower.startsWith(prefix.substring(0, Math.min(prefix.length, 8)))) {
          short = name.replace(/^[^-]*-[^-]*-/, '');
        }
      }
      if (short.length > 20) {
        short = `${pubPriv} ${azSuffix}`;
      }
      return `${short}\n${resource.cidr || ''}`;
    }

    if (type === 'vpc') {
      const vpcName = name.length > 24 ? name.substring(0, 22) + '..' : name;
      return `${vpcName}\n${resource.cidr || ''}`;
    }

    if (type === 's3' && name.length > maxLen) {
      return name.substring(0, 8) + '..' + name.substring(name.length - 8);
    }

    if (name.length > maxLen) {
      return name.substring(0, maxLen - 2) + '..';
    }
    return name;
  }

  function typeTag(type) {
    return TYPE_LABELS[type] || type;
  }

  // ══════════════════════════════════════════════════════════
  //  JointJS + ELK.js Rendering Engine
  // ══════════════════════════════════════════════════════════

  // JointJS v4 doesn't ship CSS — inject essential paper styles
  // JointJS v4 paper styles — minimal, don't override SVG dimensions
  (function injectJointCSS() {
    const style = document.createElement('style');
    style.textContent = `
      .joint-paper { position: relative; }
    `;
    document.head.appendChild(style);
  })();

  const { dia, shapes, util } = joint;

  // ── Theme helpers ──
  function getThemeColors() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
      isDark,
      bg:       isDark ? '#0d1b2a' : '#f8fafc',
      bgCard:   isDark ? '#0f1b2d' : '#ffffff',
      text:     isDark ? '#e2e8f0' : '#1e293b',
      textMuted: isDark ? '#8899aa' : '#64748b',
      border:   isDark ? '#2d4a6f' : '#cbd5e1',
      // container backgrounds
      vpcBg:     isDark ? '#111d2e' : '#fffbf0',
      pubTierBg: isDark ? '#0a2212' : '#f0fdf4',
      privTierBg: isDark ? '#0a1628' : '#eff6ff',
      pubSubBg:  isDark ? '#0d2818' : '#dcfce7',
      privSubBg: isDark ? '#0d1a33' : '#dbeafe',
      azBg:      isDark ? '#0e1926' : '#f0f4f8',
      azBorder:  isDark ? '#2d4a6f' : '#94a3b8',
      iconBg:    isDark ? '#1a2332' : '#ffffff',
      iconBorder: isDark ? '#334155' : '#e2e8f0',
    };
  }

  // Use built-in standard shapes for maximum reliability

  // ── Create JointJS Paper ──
  function createPaper(container) {
    // Cleanup previous paper (preserve container in DOM — paper.remove() would detach it)
    if (_paper) {
      if (_paper._cleanupFns) _paper._cleanupFns.forEach(fn => fn());
      _paper.off();
      _graph = null;
      _paper = null;
    }
    // Clear old SVG content while keeping the container element
    container.innerHTML = '';

    const w = container.clientWidth || 1200;
    const h = container.clientHeight || 780;
    _graph = new dia.Graph({}, { cellNamespace: shapes });

    try {
      _paper = new dia.Paper({
        el: container,
        model: _graph,
        width: w,
        height: h,
        gridSize: 1,
        background: { color: 'transparent' },
        cellViewNamespace: shapes,
        interactive: { elementMove: true },
      });
    } catch (e) {
      console.error('[Topology] Paper creation failed:', e);
      return null;
    }

    // ── Pan & Zoom ──
    _currentScale = 1;

    _paper.on('blank:mousewheel', (evt, x, y, delta) => {
      evt.preventDefault();
      const oldScale = _paper.scale().sx;
      const factor = delta > 0 ? 1.08 : 0.93;
      const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, oldScale * factor));
      scaleToPoint(newScale, x, y);
      updateZoomSlider();
    });

    _paper.on('cell:mousewheel', (cellView, evt, x, y, delta) => {
      evt.preventDefault();
      const oldScale = _paper.scale().sx;
      const factor = delta > 0 ? 1.08 : 0.93;
      const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, oldScale * factor));
      scaleToPoint(newScale, x, y);
      updateZoomSlider();
    });

    _paper.on('blank:pointerdown', (evt) => {
      _isPanning = true;
      _panStart = { x: evt.clientX, y: evt.clientY };
      container.style.cursor = 'grabbing';
    });

    const onMouseMove = (evt) => {
      if (!_isPanning) return;
      const translate = _paper.translate();
      _paper.translate(
        translate.tx + (evt.clientX - _panStart.x),
        translate.ty + (evt.clientY - _panStart.y)
      );
      _panStart = { x: evt.clientX, y: evt.clientY };
    };

    const onMouseUp = () => {
      if (_isPanning) {
        _isPanning = false;
        container.style.cursor = 'default';
      }
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);

    // Store cleanup refs
    _paper._cleanupFns = [
      () => document.removeEventListener('mousemove', onMouseMove),
      () => document.removeEventListener('mouseup', onMouseUp),
    ];

    // ── Click events ──
    _paper.on('element:pointerclick', (elementView) => {
      const model = elementView.model;
      const d = model.prop('resourceData');
      if (d) showNodeDetail(d);
      clearHighlight();
    });

    _paper.on('blank:pointerclick', () => {
      hideNodeDetail();
      clearHighlight();
    });

    // ── Right-click context menu ──
    _paper.on('element:contextmenu', (elementView, evt) => {
      evt.preventDefault();
      const model = elementView.model;
      const d = model.prop('resourceData');
      if (d) showContextMenu(evt.clientX, evt.clientY, d);
    });

    // ── Pan/zoom → update minimap ──
    _paper.on('translate', () => updateMinimap());
    _paper.on('scale', () => updateMinimap());

    // ── Double-click for label edit ──
    _paper.on('element:pointerdblclick', (elementView) => {
      const model = elementView.model;
      if (model.prop('resourceData')) startLabelEdit(model, elementView);
    });

    // ── Hover tooltip ──
    const tooltip = document.getElementById('cyTooltip');
    let _tooltipTimer = null;

    _paper.on('element:mouseenter', (elementView) => {
      clearTimeout(_tooltipTimer);
      const model = elementView.model;
      const d = model.prop('resourceData');
      if (!d) return;
      _tooltipTimer = setTimeout(() => {
        const typeBadge = TYPE_LABELS[d.nodeType || d.type] || d.type || '';
        const color = TYPE_COLORS[d.nodeType || d.type] || '#888';
        const fields = [
          ['ID', d.id], ['Region', d.region], ['AZ', d.az], ['CIDR', d.cidr],
          ['VPC', d.vpc_id], ['State', d.state || d.status],
          ['Type', d.instance_type || d.engine || d.runtime || d.lb_type],
          ['Public IP', d.public_ip], ['Private IP', d.private_ip],
          ['DNS', d.dns_name], ['Scheme', d.scheme],
        ];
        let rows = '';
        fields.forEach(([k, v]) => {
          if (v !== undefined && v !== null && v !== '') {
            rows += `<div class="tt-row"><span class="tt-key">${k}</span><span class="tt-val">${escHtml(String(v))}</span></div>`;
          }
        });
        tooltip.innerHTML = `<div class="tt-title">${escHtml(d.name || d.id || '')}</div><span class="tt-type" style="background:${color};color:#000">${typeBadge}</span>${rows}`;
        tooltip.style.display = 'block';

        const bbox = elementView.getBBox();
        const ctm = _paper.matrix();
        const tx = bbox.x * ctm.a + ctm.e + bbox.width * ctm.a + 10;
        const ty = bbox.y * ctm.d + ctm.f;
        const cRect = _paper.el.getBoundingClientRect();
        let px = tx + cRect.left;
        let py = ty + cRect.top;
        const tw = tooltip.offsetWidth || 200;
        const th = tooltip.offsetHeight || 100;
        if (px + tw > window.innerWidth - 10) px = px - tw - bbox.width * ctm.a - 20;
        if (py + th > window.innerHeight - 10) py = window.innerHeight - th - 10;
        if (py < 10) py = 10;
        tooltip.style.left = px + 'px';
        tooltip.style.top = py + 'px';
      }, 350);
    });

    _paper.on('element:mouseleave', () => {
      clearTimeout(_tooltipTimer);
      tooltip.style.display = 'none';
    });

    return _paper;
  }

  function scaleToPoint(newScale, x, y) {
    const oldScale = _paper.scale().sx;
    const translate = _paper.translate();
    const beta = oldScale / newScale;
    const ax = x - (x * beta);
    const ay = y - (y * beta);
    _paper.translate(translate.tx - ax * newScale, translate.ty - ay * newScale);
    _paper.scale(newScale, newScale);
    _currentScale = newScale;
  }

  function fitContent() {
    if (!_paper || !_graph || _graph.getElements().length === 0) return;
    try {
      _paper.scaleContentToFit({ padding: 40, maxScale: 1.5, minScale: 0.15 });
      _currentScale = _paper.scale().sx;
      updateZoomSlider();
    } catch (e) {
      console.error('[Topology] fitContent error:', e);
    }
  }

  // ── Map Controls ──
  function updateZoomSlider() {
    const slider = document.getElementById('mapZoomSlider');
    if (slider && _paper) {
      slider.value = Math.round(_currentScale * 100);
    }
  }

  let _isFullscreen = false;
  function setupMapControls() {
    const zoomInBtn = document.getElementById('mapZoomInBtn');
    const zoomOutBtn = document.getElementById('mapZoomOutBtn');
    const fitBtn = document.getElementById('mapFitBtn');
    const fsBtn = document.getElementById('mapFullscreenBtn');
    const slider = document.getElementById('mapZoomSlider');

    zoomInBtn?.addEventListener('click', () => {
      if (!_paper) return;
      const s = Math.min(MAX_SCALE, _currentScale * 1.25);
      const cw = (_paper.el.clientWidth || 1200) / 2;
      const ch = (_paper.el.clientHeight || 780) / 2;
      scaleToPoint(s, cw, ch);
      updateZoomSlider();
    });

    zoomOutBtn?.addEventListener('click', () => {
      if (!_paper) return;
      const s = Math.max(MIN_SCALE, _currentScale * 0.8);
      const cw = (_paper.el.clientWidth || 1200) / 2;
      const ch = (_paper.el.clientHeight || 780) / 2;
      scaleToPoint(s, cw, ch);
      updateZoomSlider();
    });

    fitBtn?.addEventListener('click', () => fitContent());

    slider?.addEventListener('input', () => {
      if (!_paper) return;
      const newScale = parseInt(slider.value, 10) / 100;
      const cw = (_paper.el.clientWidth || 1200) / 2;
      const ch = (_paper.el.clientHeight || 780) / 2;
      scaleToPoint(newScale, cw, ch);
    });

    fsBtn?.addEventListener('click', () => {
      const card = document.getElementById('canvasCard');
      if (!card) return;
      _isFullscreen = !_isFullscreen;
      card.classList.toggle('topo-fullscreen', _isFullscreen);
      fsBtn.title = _isFullscreen ? 'Exit Fullscreen' : 'Fullscreen';
      fsBtn.innerHTML = _isFullscreen
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
      // Resize paper after transition
      setTimeout(() => {
        if (_paper) {
          const container = document.getElementById('cyContainer');
          _paper.setDimensions(container.clientWidth, container.clientHeight);
          fitContent();
        }
      }, 100);
    });

    // ESC exits fullscreen
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && _isFullscreen) {
        fsBtn?.click();
      }
    });
  }

  // Update slider when mouse-wheel zoom happens
  function onScaleChange() { updateZoomSlider(); }

  // ── Render Diagram (main entry) ──
  function renderDiagram() {
    if (!_scanData) return;
    const resources = _scanData.resources || [];
    const selectedVpc = document.getElementById('vpcSelector')?.value || '';

    let filtered = resources.filter(r => _visibleTypes.has(r.type));
    if (selectedVpc) {
      filtered = filtered.filter(r => r.vpc_id === selectedVpc || r.id === selectedVpc || r.type === 'peering' || r.type === 'igw' || r.type === 'transit_gateway' || r.type === 'cloudfront' || r.type === 's3');
    }
    // Region filter
    if (_selectedRegionFilter) {
      filtered = filtered.filter(r => r.region === _selectedRegionFilter || r.region === 'global');
    }

    const container = document.getElementById('cyContainer');
    if (!container) return;

    // Ensure the container is visible and laid out before creating paper
    requestAnimationFrame(() => {
      const paper = createPaper(container);
      if (!paper) return;

      try {
        buildVpcArchDiagram(filtered);
        console.log('[Topology] Rendered', _graph.getElements().length, 'elements,', _graph.getLinks().length, 'links');
        setTimeout(() => {
          fitContent();
          updateZoomSlider();
          updateMinimap();
        }, 150);
      } catch (e) {
        console.error('[Topology] Diagram build error:', e);
      }
    });
  }

  // ══════════════════════════════════════════════════════════
  //  Diagram Builders — produce JointJS elements
  // ══════════════════════════════════════════════════════════

  function addContainer(id, label, opts) {
    const tc = getThemeColors();
    const containerType = opts.containerType || 'vpc';
    let fill, stroke, strokeWidth, labelColor, headerFill;

    if (containerType === 'vpc') {
      fill = tc.vpcBg; stroke = '#ff9900'; strokeWidth = 2.5; labelColor = '#ff9900'; headerFill = '#ff990022';
    } else if (containerType === 'tier_public') {
      fill = tc.pubTierBg; stroke = '#22c55e'; strokeWidth = 2; labelColor = '#22c55e'; headerFill = '#22c55e22';
    } else if (containerType === 'tier_private') {
      fill = tc.privTierBg; stroke = '#3b82f6'; strokeWidth = 2; labelColor = '#3b82f6'; headerFill = '#3b82f622';
    } else if (containerType === 'az') {
      fill = tc.azBg; stroke = tc.azBorder; strokeWidth = 1.5; labelColor = tc.textMuted; headerFill = 'transparent';
    } else if (containerType === 'subnet_public') {
      fill = tc.pubSubBg; stroke = '#22c55e'; strokeWidth = 1.5; labelColor = tc.text; headerFill = '#22c55e18';
    } else if (containerType === 'subnet_private') {
      fill = tc.privSubBg; stroke = '#3b82f6'; strokeWidth = 1.5; labelColor = tc.text; headerFill = '#3b82f618';
    } else if (containerType === 'remote_vpc') {
      fill = tc.vpcBg; stroke = '#ff990088'; strokeWidth = 2; labelColor = '#ff990088'; headerFill = '#ff990011';
    } else {
      fill = tc.bgCard; stroke = tc.border; strokeWidth = 1; labelColor = tc.text; headerFill = 'transparent';
    }

    const w = opts.width || 200;
    const h = opts.height || 100;

    const rr = containerType === 'az' ? 4 : 8;
    const el = new shapes.standard.Rectangle({
      id,
      position: { x: opts.x || 0, y: opts.y || 0 },
      size: { width: w, height: h },
      attrs: {
        body: {
          fill, stroke, strokeWidth, rx: rr, ry: rr,
          strokeDasharray: containerType === 'az' ? '6,3' : containerType === 'remote_vpc' ? '8,4' : 'none',
        },
        label: {
          text: label, fill: labelColor,
          fontSize: 11, fontWeight: 700,
          fontFamily: "Inter, system-ui, sans-serif",
          textAnchor: 'start', textVerticalAnchor: 'top',
          refX: 10, refY: 8,
        },
      },
    });
    if (opts.resourceData) el.prop('resourceData', opts.resourceData);

    _graph.addCell(el);
    if (opts.parentId) {
      const parent = _graph.getCell(opts.parentId);
      if (parent) parent.embed(el);
    }
    return el;
  }

  function addResource(id, type, label, opts) {
    const tc = getThemeColors();
    const iconUrl = AWS_ICONS[type] || '';
    const w = opts.width || 56;
    const h = opts.height || 68;
    const iconSize = opts.iconSize || 36;

    const el = new shapes.standard.Image({
      id,
      position: { x: opts.x || 0, y: opts.y || 0 },
      size: { width: w, height: h },
      attrs: {
        body: {
          fill: tc.iconBg, stroke: tc.iconBorder, strokeWidth: 1,
          rx: 6, ry: 6,
        },
        image: {
          'xlink:href': iconUrl,
          width: iconSize, height: iconSize,
          x: (w - iconSize) / 2, y: 4,
        },
        label: {
          text: label,
          fill: tc.textMuted,
          fontSize: 9, fontWeight: '600',
          fontFamily: "Inter, system-ui, sans-serif",
          textAnchor: 'middle', textVerticalAnchor: 'top',
          refX: '50%', refY: 50,
        },
      },
    });
    if (opts.resourceData) el.prop('resourceData', opts.resourceData);

    _graph.addCell(el);
    if (opts.parentId) {
      const parent = _graph.getCell(opts.parentId);
      if (parent) parent.embed(el);
    }
    return el;
  }

  function addLink(sourceId, targetId, opts) {
    const tc = getThemeColors();
    opts = opts || {};
    const color = opts.color || tc.border;
    const strokeWidth = opts.strokeWidth || 1.5;
    const dashed = opts.dashed || false;

    const link = new shapes.standard.Link({
      source: { id: sourceId },
      target: { id: targetId },
      attrs: {
        line: {
          stroke: color,
          strokeWidth,
          strokeDasharray: dashed ? '6,3' : 'none',
          targetMarker: { type: 'path', d: opts.noArrow ? '' : 'M 10 -5 0 0 10 5 z', fill: color, stroke: color },
          sourceMarker: opts.biDir ? { type: 'path', d: 'M 10 -5 0 0 10 5 z', fill: color, stroke: color } : { d: '' },
        },
      },
      labels: opts.label ? [{
        position: 0.5,
        attrs: {
          text: { text: opts.label, fontSize: 9, fontWeight: '600', fill: color, fontFamily: "Inter, system-ui, sans-serif" },
        }
      }] : [],
    });
    _graph.addCell(link);
    return link;
  }

  // ── Types to exclude from VPC-level display (reduce clutter) ──
  // These types are only shown when user clicks "Detailed" view AND are inside subnets,
  // or they are shown as counts on the VPC card — not as individual nodes
  const VPC_LEVEL_CLUTTER_TYPES = new Set([
    'security_group', 'nacl', 'route_table', 'eip', 'eni',
  ]);

  // ── VPC Architecture Diagram ──
  function buildVpcArchDiagram(resources) {
    const vpcs = resources.filter(r => r.type === 'vpc');
    const subnets = resources.filter(r => r.type === 'subnet');
    const igws = resources.filter(r => r.type === 'igw');
    const nats = resources.filter(r => r.type === 'nat');
    const others = resources.filter(r =>
      !['vpc', 'subnet', 'igw', 'nat', 'peering', 'organization', 'org_account'].includes(r.type)
    );

    const vpcMap = {};
    vpcs.forEach(v => { vpcMap[v.id] = { vpc: v, azs: {} }; });
    subnets.forEach(s => {
      if (!vpcMap[s.vpc_id]) return;
      const az = s.az || 'unknown-az';
      if (!vpcMap[s.vpc_id].azs[az]) vpcMap[s.vpc_id].azs[az] = { public: [], private: [] };
      if (s.is_public) vpcMap[s.vpc_id].azs[az].public.push(s);
      else vpcMap[s.vpc_id].azs[az].private.push(s);
    });

    // Only place non-clutter resources inside subnets/VPCs
    const subnetResources = {};
    const vpcResources = {};
    others.forEach(r => {
      // Skip clutter types from being placed as individual nodes in VPC
      if (VPC_LEVEL_CLUTTER_TYPES.has(r.type)) return;
      if (r.subnet_id && subnets.find(s => s.id === r.subnet_id)) {
        if (!subnetResources[r.subnet_id]) subnetResources[r.subnet_id] = [];
        subnetResources[r.subnet_id].push(r);
      } else if (r.vpc_id && vpcMap[r.vpc_id]) {
        if (!vpcResources[r.vpc_id]) vpcResources[r.vpc_id] = [];
        vpcResources[r.vpc_id].push(r);
      }
    });

    const nodeIds = new Set();
    const SUB_W = 180, SUB_H = 60, RES_W = 56, RES_H = 68, PAD = 30;
    const AZ_GAP = 24, RES_GAP = 10, SUB_PAD = 14;

    let globalX = 40;

    vpcs.forEach((vpc) => {
      const vpcData = vpcMap[vpc.id];
      if (!vpcData) return;
      const azNames = Object.keys(vpcData.azs).sort();

      let vpcHasPublic = false, vpcHasPrivate = false;
      azNames.forEach(az => {
        const d = vpcData.azs[az];
        if (d.public.length) vpcHasPublic = true;
        if (d.private.length) vpcHasPrivate = true;
      });

      // Compute max resources in any subnet (cap at 4 cols for readability)
      let maxResInSub = 0;
      subnets.filter(s => s.vpc_id === vpc.id).forEach(s => {
        const cnt = (subnetResources[s.id] || []).length;
        maxResInSub = Math.max(maxResInSub, cnt);
      });

      const resColsPerSub = Math.max(1, Math.min(maxResInSub, 4));
      const subW = Math.max(SUB_W, resColsPerSub * (RES_W + RES_GAP) + SUB_PAD * 2);
      const azColW = subW + SUB_PAD * 2;

      // Only non-clutter VPC-level resources
      const vpcExtraRes = (vpcResources[vpc.id] || []).filter(r => !VPC_LEVEL_CLUTTER_TYPES.has(r.type));

      // Helper: resource rows needed
      const resRows = (cnt) => cnt <= 0 ? 0 : Math.ceil(cnt / resColsPerSub);

      // ── Calculate tier heights ──
      function calcTierH(tier) {
        let maxSubH = 0;
        azNames.forEach(az => {
          const azSubs = vpcData.azs[az][tier];
          let colH = 0;
          azSubs.forEach(s => {
            const sRes = (subnetResources[s.id] || []).length;
            const rowCount = resRows(sRes);
            const contentH = rowCount > 0 ? rowCount * (RES_H + RES_GAP) : 0;
            colH += SUB_H + contentH + 16;
          });
          maxSubH = Math.max(maxSubH, colH);
        });
        return maxSubH > 0 ? maxSubH + PAD + 36 : 0;
      }

      const pubTierH = vpcHasPublic ? calcTierH('public') : 0;
      const privTierH = vpcHasPrivate ? calcTierH('private') : 0;
      const natRowH = nats.some(n => n.vpc_id === vpc.id) && vpcHasPublic && vpcHasPrivate ? 80 : 0;
      const vpcResColsPerRow = 8;
      const vpcResRowH = vpcExtraRes.length > 0 ? Math.ceil(vpcExtraRes.length / vpcResColsPerRow) * (RES_H + 12) + 30 : 0;

      // Count AZs that actually have subnets per tier
      const pubAzCount = azNames.filter(az => vpcData.azs[az].public.length > 0).length;
      const privAzCount = azNames.filter(az => vpcData.azs[az].private.length > 0).length;
      const maxAzCount = Math.max(pubAzCount, privAzCount, 1);

      const totalAzW = maxAzCount * azColW + (maxAzCount - 1) * AZ_GAP;
      const vpcW = Math.max(totalAzW + PAD * 2 + 20, 340);
      const vpcH = PAD + 32 + pubTierH + natRowH + privTierH + vpcResRowH + PAD;

      // ── IGW above VPC ──
      const igwsForVpc = igws.filter(g => g.vpc_id === vpc.id);
      igwsForVpc.forEach((igw, i) => {
        const igwId = `igw_${igw.id}`;
        addResource(igwId, 'igw', 'Internet GW', {
          x: globalX + vpcW / 2 - 28 + (i - (igwsForVpc.length - 1) / 2) * 80,
          y: 20,
          resourceData: { ...igw, nodeType: 'igw' },
        });
        nodeIds.add(igwId);
      });

      const vpcY = igwsForVpc.length > 0 ? 110 : 40;

      // ── VPC container ──
      addContainer(vpc.id, shortLabel(vpc), {
        containerType: 'vpc', x: globalX, y: vpcY,
        width: vpcW, height: vpcH,
        resourceData: { ...vpc, nodeType: 'vpc' },
      });
      nodeIds.add(vpc.id);

      // Link IGW → VPC
      igwsForVpc.forEach((igw) => {
        addLink(`igw_${igw.id}`, vpc.id, { color: '#8c4fff', strokeWidth: 2 });
      });

      let tierY = vpcY + PAD + 32;

      // ── Helper: place subnets in a tier ──
      function placeTier(tierType, tierId, tierLabel, containerType, subContainerType, tierH) {
        addContainer(tierId, tierLabel, {
          containerType, x: globalX + PAD, y: tierY,
          width: vpcW - PAD * 2, height: tierH,
          parentId: vpc.id,
        });

        // Center AZ columns within the tier
        const activAzs = azNames.filter(az => vpcData.azs[az][tierType].length > 0);
        const usedWidth = activAzs.length * azColW + (activAzs.length - 1) * AZ_GAP;
        let azX = globalX + PAD + Math.max(10, ((vpcW - PAD * 2) - usedWidth) / 2);

        activAzs.forEach((az) => {
          const azData = vpcData.azs[az];
          const azSubs = azData[tierType];
          if (!azSubs.length) return;

          const azId = `${vpc.id}_${az}_${tierType}`;
          const azH = tierH - 40;
          addContainer(azId, az.replace(/.*-/, ''), {
            containerType: 'az', x: azX, y: tierY + 30,
            width: azColW, height: azH,
            parentId: tierId,
          });

          let subY = tierY + 56;
          azSubs.forEach((s) => {
            const sRes = subnetResources[s.id] || [];
            const countBadge = sRes.length > 0 ? ` [${sRes.length}]` : '';
            const sLabel = shortLabel(s) + countBadge;
            const rowCount = resRows(sRes.length);
            const contentH = rowCount > 0 ? rowCount * (RES_H + RES_GAP) : 0;
            const sH = SUB_H + contentH;

            // Center subnet horizontally within AZ
            const subX = azX + (azColW - subW) / 2;
            addContainer(s.id, sLabel.split('\n')[0], {
              containerType: subContainerType, x: subX, y: subY,
              width: subW, height: sH,
              parentId: azId,
              resourceData: { ...s, nodeType: 'subnet' },
            });
            nodeIds.add(s.id);

            if (s.cidr) {
              const cidrEl = _graph.getCell(s.id);
              if (cidrEl) cidrEl.attr('label/text', `${sLabel.split('\n')[0]}\n${s.cidr}`);
            }

            // Place resources inside subnet, centered
            if (sRes.length > 0) {
              const resStartX = subX + (subW - Math.min(sRes.length, resColsPerSub) * (RES_W + RES_GAP) + RES_GAP) / 2;
              sRes.forEach((r, ri) => {
                const col = ri % resColsPerSub;
                const row = Math.floor(ri / resColsPerSub);
                const rx = resStartX + col * (RES_W + RES_GAP);
                const ry = subY + SUB_H - 24 + row * (RES_H + RES_GAP);
                addResource(r.id, r.type, typeTag(r.type), {
                  x: rx, y: ry, parentId: s.id,
                  resourceData: { ...r, nodeType: r.type },
                });
                nodeIds.add(r.id);
              });
            }

            subY += sH + 12;
          });

          azX += azColW + AZ_GAP;
        });

        tierY += tierH;
      }

      // ── Public Tier ──
      if (vpcHasPublic && pubTierH > 0) {
        placeTier('public', `${vpc.id}_pub_tier`, 'Public Subnets',
          'tier_public', 'subnet_public', pubTierH);
      }

      // ── NAT Gateways (between tiers) ──
      if (vpcHasPublic && vpcHasPrivate && natRowH > 0) {
        const activAzs = azNames.filter(az => vpcData.azs[az].public.length > 0 || vpcData.azs[az].private.length > 0);
        const usedWidth = activAzs.length * azColW + (activAzs.length - 1) * AZ_GAP;
        let azX = globalX + PAD + Math.max(10, ((vpcW - PAD * 2) - usedWidth) / 2);

        activAzs.forEach((az) => {
          const azCx = azX + azColW / 2;
          const azNats = nats.filter(n => {
            const azData = vpcData.azs[az];
            if (n.subnet_id) return azData.public.some(s => s.id === n.subnet_id) || azData.private.some(s => s.id === n.subnet_id);
            return n.az === az && n.vpc_id === vpc.id;
          });
          azNats.forEach((nat, ni) => {
            const natId = `nat_${nat.id}`;
            addResource(natId, 'nat', 'NAT GW', {
              x: azCx - 28 + ni * 70, y: tierY + 8,
              parentId: vpc.id,
              resourceData: { ...nat, nodeType: 'nat' },
            });
            nodeIds.add(natId);
            if (nat.subnet_id && nodeIds.has(nat.subnet_id)) {
              addLink(natId, nat.subnet_id, { color: '#22c55e' });
            }
          });
          azX += azColW + AZ_GAP;
        });
        tierY += natRowH;
      }

      // ── Private Tier ──
      if (vpcHasPrivate && privTierH > 0) {
        placeTier('private', `${vpc.id}_priv_tier`, 'Private Subnets',
          'tier_private', 'subnet_private', privTierH);
      }

      // ── VPC-level resources (only non-clutter types) ──
      if (vpcExtraRes.length > 0) {
        const resStartY = tierY + 10;
        const colW = Math.max((vpcW - PAD * 2) / vpcResColsPerRow, 70);
        let placed = 0;
        vpcExtraRes.forEach((r) => {
          if (nodeIds.has(r.id)) return;
          const col = placed % vpcResColsPerRow;
          const row = Math.floor(placed / vpcResColsPerRow);
          addResource(r.id, r.type, typeTag(r.type), {
            x: globalX + PAD + col * colW, y: resStartY + row * (RES_H + 12),
            parentId: vpc.id,
            resourceData: { ...r, nodeType: r.type },
          });
          nodeIds.add(r.id);
          placed++;
        });
      }

      globalX += vpcW + 60;
    });

    // ── Global resources — grouped in a container ──
    const globalRes = others.filter(r => !r.vpc_id && !nodeIds.has(r.id) && !VPC_LEVEL_CLUTTER_TYPES.has(r.type));
    if (globalRes.length > 0) {
      const grouped = {};
      globalRes.forEach(r => {
        if (!grouped[r.type]) grouped[r.type] = [];
        grouped[r.type].push(r);
      });

      // Create a "Global Services" container
      const groupTypes = Object.keys(grouped);
      const GCOLS = 4;
      let totalGlobalItems = 0;
      groupTypes.forEach(t => { totalGlobalItems += grouped[t].length; });
      const globalRows = Math.ceil(totalGlobalItems / GCOLS);
      const globalContainerW = GCOLS * (RES_W + RES_GAP * 2) + PAD * 2;
      const globalContainerH = globalRows * (RES_H + RES_GAP + 16) + 50;

      addContainer('_global_services', 'Global Services', {
        containerType: 'vpc', x: globalX, y: 40,
        width: Math.max(globalContainerW, 300), height: Math.max(globalContainerH, 120),
      });

      let gIdx = 0;
      groupTypes.forEach((type) => {
        grouped[type].forEach((r) => {
          if (nodeIds.has(r.id)) return;
          const col = gIdx % GCOLS;
          const row = Math.floor(gIdx / GCOLS);
          addResource(r.id, r.type, shortLabel(r, 12), {
            x: globalX + PAD + col * (RES_W + RES_GAP * 2),
            y: 80 + row * (RES_H + RES_GAP + 8),
            parentId: '_global_services',
            resourceData: { ...r, nodeType: r.type },
          });
          nodeIds.add(r.id);
          gIdx++;
        });
      });
    }

    // Peering edges
    resources.filter(r => r.type === 'peering').forEach(p => {
      if (p.requester_vpc_id && p.accepter_vpc_id) {
        [{ id: p.requester_vpc_id, cidr: p.requester_cidr, acct: p.requester_account },
         { id: p.accepter_vpc_id, cidr: p.accepter_cidr, acct: p.accepter_account }].forEach(v => {
          if (v.id && !nodeIds.has(v.id)) {
            addContainer(v.id, `${(v.id||'').substring(0,12)}\n(${(v.acct||'remote').substring(0,12)})`, {
              containerType: 'remote_vpc', x: globalX, y: 100,
              width: 180, height: 80,
            });
            nodeIds.add(v.id);
            globalX += 200;
          }
        });
        if (nodeIds.has(p.requester_vpc_id) && nodeIds.has(p.accepter_vpc_id)) {
          addLink(p.requester_vpc_id, p.accepter_vpc_id, {
            color: p.is_cross_account ? '#e53935' : '#00acc1',
            strokeWidth: 2.5, biDir: true, dashed: p.is_cross_account,
            label: p.is_cross_account ? 'Cross-Acct' : 'Peering',
          });
        }
      }
    });

    // TGW / ELB edges
    resources.filter(r => r.type === 'tgw_attachment').forEach(att => {
      if (att.tgw_id && att.resource_id && nodeIds.has(att.tgw_id) && nodeIds.has(att.resource_id))
        addLink(att.tgw_id, att.resource_id, { color: '#8c4fff', label: 'TGW' });
    });
    resources.filter(r => r.type === 'elb').forEach(lb => {
      (lb.subnet_ids || []).forEach(sid => {
        if (nodeIds.has(lb.id) && nodeIds.has(sid))
          addLink(lb.id, sid, { color: getThemeColors().border, noArrow: true, dashed: true });
      });
    });

    // Route Table → Subnet associations
    resources.filter(r => r.type === 'route_table').forEach(rt => {
      (rt.associations || []).forEach(assoc => {
        if (assoc.subnet_id && nodeIds.has(rt.id) && nodeIds.has(assoc.subnet_id)) {
          addLink(rt.id, assoc.subnet_id, {
            color: rt.has_igw_route ? '#22c55e' : '#3b82f6',
            dashed: true, noArrow: true,
            label: assoc.main ? 'Main RT' : '',
          });
        }
      });
    });

    // Security Group → Resource connections
    const sgMap = {};
    resources.filter(r => r.type === 'security_group').forEach(sg => { sgMap[sg.id] = sg; });
    resources.forEach(r => {
      const sgs = r.security_groups || [];
      sgs.forEach(sg => {
        const sgId = typeof sg === 'string' ? sg : sg.id;
        if (sgId && sgMap[sgId] && nodeIds.has(r.id) && nodeIds.has(sgId)) {
          addLink(sgId, r.id, { color: '#f4511e', dashed: true, noArrow: true });
        }
      });
    });

    // CloudFront → Origin connections
    resources.filter(r => r.type === 'cloudfront').forEach(cf => {
      (cf.origins || []).forEach(origin => {
        const domain = origin.domain || '';
        // Try to match origin to an ELB or S3
        resources.forEach(r2 => {
          if (r2.type === 'elb' && r2.dns_name && domain.includes(r2.dns_name)) {
            if (nodeIds.has(cf.id) && nodeIds.has(r2.id))
              addLink(cf.id, r2.id, { color: '#7c4dff', label: 'Origin' });
          }
          if (r2.type === 's3' && domain.includes(r2.id + '.s3')) {
            if (nodeIds.has(cf.id) && nodeIds.has(r2.id))
              addLink(cf.id, r2.id, { color: '#7c4dff', label: 'Origin' });
          }
        });
      });
    });

    // VPC Endpoint → VPC connections
    resources.filter(r => r.type === 'vpc_endpoint').forEach(ep => {
      if (ep.vpc_id && nodeIds.has(ep.id) && nodeIds.has(ep.vpc_id)) {
        addLink(ep.id, ep.vpc_id, { color: '#546e7a', dashed: true, noArrow: true });
      }
    });

    // EKS → Subnet connections
    resources.filter(r => r.type === 'eks').forEach(eks => {
      (eks.subnet_ids || []).forEach(sid => {
        if (nodeIds.has(eks.id) && nodeIds.has(sid))
          addLink(eks.id, sid, { color: '#ff9900', dashed: true, noArrow: true });
      });
    });

    // Lambda → Subnet connections
    resources.filter(r => r.type === 'lambda').forEach(fn => {
      (fn.subnet_ids || []).forEach(sid => {
        if (nodeIds.has(fn.id) && nodeIds.has(sid))
          addLink(fn.id, sid, { color: '#ff6f00', dashed: true, noArrow: true });
      });
    });

    // VPN Gateway → VPC
    resources.filter(r => r.type === 'vpn_gateway').forEach(vgw => {
      if (vgw.vpc_id && nodeIds.has(vgw.id) && nodeIds.has(vgw.vpc_id)) {
        addLink(vgw.id, vgw.vpc_id, { color: '#8c4fff', strokeWidth: 2, label: 'VPN' });
      }
    });

    // VPN Connection → VPN Gateway / TGW
    resources.filter(r => r.type === 'vpn_connection').forEach(vpn => {
      if (vpn.vpn_gateway_id && nodeIds.has(vpn.id) && nodeIds.has(vpn.vpn_gateway_id))
        addLink(vpn.id, vpn.vpn_gateway_id, { color: '#7c3aed', label: 'S2S VPN' });
      if (vpn.transit_gateway_id && nodeIds.has(vpn.id) && nodeIds.has(vpn.transit_gateway_id))
        addLink(vpn.id, vpn.transit_gateway_id, { color: '#7c3aed', label: 'S2S VPN' });
      if (vpn.customer_gateway_id && nodeIds.has(vpn.id) && nodeIds.has(vpn.customer_gateway_id))
        addLink(vpn.customer_gateway_id, vpn.id, { color: '#6d28d9', dashed: true });
    });

    // Network Firewall → Subnet
    resources.filter(r => r.type === 'network_firewall').forEach(fw => {
      (fw.subnet_ids || []).forEach(sid => {
        if (nodeIds.has(fw.id) && nodeIds.has(sid))
          addLink(fw.id, sid, { color: '#dc2626', label: 'FW' });
      });
    });

    // ECS Service → Subnet
    resources.filter(r => r.type === 'ecs_service').forEach(svc => {
      (svc.subnet_ids || []).forEach(sid => {
        if (nodeIds.has(svc.id) && nodeIds.has(sid))
          addLink(svc.id, sid, { color: '#ff6600', dashed: true, noArrow: true });
      });
    });

    // Route53 Private Hosted Zone → VPC
    resources.filter(r => r.type === 'hosted_zone' && r.is_private).forEach(zone => {
      (zone.vpc_ids || []).forEach(vid => {
        if (nodeIds.has(zone.id) && nodeIds.has(vid))
          addLink(zone.id, vid, { color: '#2563eb', dashed: true, label: 'DNS' });
      });
    });
  }

  // ── Organization Diagram ──
  // (Peering Map and Organization diagrams removed — VPC Architecture only)

  // ══════════════════════════════════════════════════════════
  //  ELK.js Layout Engine
  // ══════════════════════════════════════════════════════════

  async function runElkLayout() {
    if (!_graph || !_paper) return;

    const layoutAlg = document.getElementById('layoutSelector')?.value || 'layered';

    // For preset diagrams, we already have positions — just skip ELK
    if (_currentDiagram === 'vpc-arch') {
      // VPC arch uses manual positions; no ELK needed
      return;
    }

    const elements = _graph.getElements();
    const links = _graph.getLinks();

    // Build ELK graph
    const elkChildren = [];
    const elkEdges = [];
    const elementMap = {};

    elements.forEach(el => {
      const parent = el.getParentCell();
      if (parent) return; // handled by parent's children

      const elkNode = buildElkNode(el);
      elkChildren.push(elkNode);
      elementMap[el.id] = elkNode;
    });

    links.forEach(link => {
      const src = link.source();
      const tgt = link.target();
      if (src.id && tgt.id) {
        elkEdges.push({
          id: link.id,
          sources: [src.id],
          targets: [tgt.id],
        });
      }
    });

    const elkGraph = {
      id: 'root',
      layoutOptions: {
        'elk.algorithm': layoutAlg,
        'elk.direction': 'DOWN',
        'elk.spacing.nodeNode': '60',
        'elk.layered.spacing.nodeNodeBetweenLayers': '80',
        'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
        'elk.padding': '[top=40,left=40,bottom=40,right=40]',
      },
      children: elkChildren,
      edges: elkEdges,
    };

    try {
      const result = await _elk.layout(elkGraph);
      applyElkPositions(result);
    } catch (e) {
      console.error('ELK layout failed:', e);
    }
  }

  function buildElkNode(element) {
    const size = element.size();
    const node = {
      id: element.id,
      width: size.width,
      height: size.height,
      children: [],
    };

    const embedded = element.getEmbeddedCells().filter(c => c.isElement());
    embedded.forEach(child => {
      node.children.push(buildElkNode(child));
    });

    return node;
  }

  function applyElkPositions(elkNode, offsetX, offsetY) {
    offsetX = offsetX || 0;
    offsetY = offsetY || 0;

    if (elkNode.id !== 'root') {
      const el = _graph.getCell(elkNode.id);
      if (el && el.isElement()) {
        el.position(elkNode.x + offsetX, elkNode.y + offsetY);
        if (elkNode.children && elkNode.children.length > 0) {
          el.resize(elkNode.width, elkNode.height);
        }
      }
    }

    if (elkNode.children) {
      elkNode.children.forEach(child => {
        const px = elkNode.id === 'root' ? 0 : elkNode.x + offsetX;
        const py = elkNode.id === 'root' ? 0 : elkNode.y + offsetY;
        applyElkPositions(child, px, py);
      });
    }
  }

  // ── Node Detail Panel ─────────────────────────────────────
  function showNodeDetail(data) {
    const panel = document.getElementById('nodeDetail');
    let rows = '';
    const displayKeys = ['type', 'name', 'id', 'region', 'vpc_id', 'az', 'cidr',
      'state', 'status', 'is_public', 'instance_type', 'engine', 'runtime',
      'public_ip', 'private_ip', 'dns_name', 'lb_type', 'scheme'];

    displayKeys.forEach(key => {
      const val = data[key];
      if (val !== undefined && val !== null && val !== '') {
        rows += `<div class="detail-row"><span class="detail-key">${key}</span><span class="detail-value">${escHtml(String(val))}</span></div>`;
      }
    });

    const typeBadge = TYPE_LABELS[data.nodeType || data.type] || data.type || '';
    const color = TYPE_COLORS[data.nodeType || data.type] || '#888';

    panel.innerHTML = `
      <div class="detail-header">
        <div class="detail-title">${escHtml(data.name || data.id || '')}</div>
        <button class="detail-close" onclick="document.getElementById('nodeDetail').style.display='none'">&times;</button>
      </div>
      <div class="detail-type-badge" style="background:${color}">${typeBadge}</div>
      ${rows}
    `;
    panel.style.display = '';
  }

  function hideNodeDetail() {
    document.getElementById('nodeDetail').style.display = 'none';
  }

  // ── Label Editing ─────────────────────────────────────────
  function startLabelEdit(model, elementView) {
    const container = document.getElementById('cyContainer');
    const bbox = elementView.getBBox();
    const ctm = _paper.matrix();
    const cRect = container.getBoundingClientRect();

    const px = bbox.x * ctm.a + ctm.e;
    const py = bbox.y * ctm.d + ctm.f;

    const input = document.createElement('input');
    input.className = 'topo-label-input';
    input.value = model.attr('label/text') || '';
    input.style.left = `${px}px`;
    input.style.top = `${py}px`;
    input.style.width = '140px';

    container.style.position = 'relative';
    container.appendChild(input);
    input.focus();
    input.select();

    function finish() {
      const newLabel = input.value.trim();
      if (newLabel) {
        model.attr('label/text', newLabel);
        _customLabels[model.id] = newLabel;
      }
      input.remove();
    }
    input.addEventListener('blur', finish);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') finish();
      if (e.key === 'Escape') input.remove();
    });
  }

  // ── Export ─────────────────────────────────────────────────
  function showExportStatus(msg) {
    const el = document.getElementById('exportStatusMsg');
    if (!el) return;
    el.textContent = msg;
    el.style.display = '';
    setTimeout(() => { el.style.display = 'none'; }, 3000);
  }

  function exportWithFeedback(format) {
    if (!_scanData && format !== 'json') {
      showExportStatus(t('topo_no_scan') || 'No scan data — run a scan first');
      return;
    }
    try {
      if (format === 'png') {
        if (!_paper) { showExportStatus('No diagram rendered'); return; }
        exportRasterHD();
      } else if (format === 'svg') {
        if (!_paper) { showExportStatus('No diagram rendered'); return; }
        const svgContent = generateSVG();
        downloadBlob(svgContent, `topology_${_selectedProfile || 'export'}.svg`, 'image/svg+xml');
      } else if (format === 'pdf-diagram') {
        if (!_paper) { showExportStatus('No diagram rendered'); return; }
        exportPdfDiagram();
      } else if (format === 'drawio') {
        if (!_paper) { showExportStatus('No diagram rendered'); return; }
        exportDrawIO();
      } else if (format === 'terraform') {
        exportTerraform();
      } else if (format === 'json') {
        exportJSON();
      }
      showExportStatus('Exported');
    } catch (e) {
      console.error('Export error:', e);
      showExportStatus('Export failed');
    }
  }

  function generateSVG() {
    if (!_paper) return '';
    // JointJS paper is SVG — we can serialize it directly
    const paperSvg = _paper.el.querySelector('svg') || _paper.svg || _paper.el;
    const svgEl = paperSvg.cloneNode(true);
    // Set viewBox for proper sizing
    const bbox = typeof _paper.getContentBBox === 'function' ? _paper.getContentBBox() : { x: 0, y: 0, width: 1200, height: 800 };
    const pad = 20;
    svgEl.setAttribute('viewBox', `${bbox.x - pad} ${bbox.y - pad} ${bbox.width + pad * 2} ${bbox.height + pad * 2}`);
    svgEl.setAttribute('width', bbox.width + pad * 2);
    svgEl.setAttribute('height', bbox.height + pad * 2);
    svgEl.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svgEl.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');

    // Add background
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg-base').trim() || '#0d1b2a';
    const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bgRect.setAttribute('x', bbox.x - pad);
    bgRect.setAttribute('y', bbox.y - pad);
    bgRect.setAttribute('width', bbox.width + pad * 2);
    bgRect.setAttribute('height', bbox.height + pad * 2);
    bgRect.setAttribute('fill', bg);
    svgEl.insertBefore(bgRect, svgEl.firstChild);

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(svgEl);
  }

  function exportRaster(format) {
    const svgContent = generateSVG();
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = function () {
      const canvas = document.createElement('canvas');
      const scale = 2;
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      const mimeType = format === 'jpg' ? 'image/jpeg' : `image/${format}`;
      canvas.toBlob(blob => {
        const dlUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = dlUrl;
        a.download = `topology_${_selectedProfile || 'export'}.${format}`;
        a.click();
        URL.revokeObjectURL(dlUrl);
      }, mimeType, 0.95);
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }

  function exportDrawIO() {
    if (!_graph) return;
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile>\n<diagram name="Topology">\n<mxGraphModel>\n<root>\n<mxCell id="0"/>\n<mxCell id="1" parent="0"/>\n';
    let cellId = 2;

    _graph.getElements().forEach(el => {
      const pos = el.position();
      const size = el.size();
      const label = (el.attr('label/text') || '').replace(/\n/g, '&#10;');
      const d = el.prop('resourceData') || {};
      const color = TYPE_COLORS[d.nodeType || d.type] || '#888888';
      xml += `<mxCell id="${cellId}" value="${escXml(label)}" style="rounded=1;fillColor=${color}33;strokeColor=${color};fontColor=#e2e8f0;" vertex="1" parent="1">\n`;
      xml += `<mxGeometry x="${Math.round(pos.x)}" y="${Math.round(pos.y)}" width="${Math.round(size.width)}" height="${Math.round(size.height)}" as="geometry"/>\n</mxCell>\n`;
      cellId++;
    });

    _graph.getLinks().forEach(link => {
      const src = link.source();
      const tgt = link.target();
      if (src.id && tgt.id) {
        const labels = link.labels() || [];
        const label = labels.length > 0 ? (labels[0].attrs?.text?.text || '') : '';
        xml += `<mxCell id="${cellId}" value="${escXml(label)}" edge="1" source="${src.id}" target="${tgt.id}" parent="1" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#00acc1;">\n`;
        xml += `<mxGeometry relative="1" as="geometry"/>\n</mxCell>\n`;
        cellId++;
      }
    });

    xml += '</root>\n</mxGraphModel>\n</diagram>\n</mxfile>';
    downloadBlob(xml, `topology_${_selectedProfile || 'export'}.drawio`, 'application/xml');
  }

  function exportExcalidraw() {
    if (!_graph) return;
    const elements = [];
    let seed = 1;

    _graph.getElements().forEach(el => {
      const pos = el.position();
      const size = el.size();
      const d = el.prop('resourceData') || {};
      const color = TYPE_COLORS[d.nodeType || d.type] || '#888888';
      elements.push({
        id: el.id, type: 'rectangle',
        x: Math.round(pos.x), y: Math.round(pos.y),
        width: Math.round(size.width), height: Math.round(size.height),
        strokeColor: color, backgroundColor: color + '33',
        fillStyle: 'solid', strokeWidth: 2, roughness: 0, opacity: 100,
        seed: seed++, roundness: { type: 3 },
      });
      const label = el.attr('label/text') || '';
      if (label) {
        elements.push({
          id: el.id + '_label', type: 'text',
          x: Math.round(pos.x + 8), y: Math.round(pos.y + size.height / 2 - 8),
          text: label, fontSize: 12, fontFamily: 1, textAlign: 'center',
          strokeColor: '#e2e8f0', seed: seed++,
        });
      }
    });

    _graph.getLinks().forEach(link => {
      const srcEl = _graph.getCell(link.source().id);
      const tgtEl = _graph.getCell(link.target().id);
      if (srcEl && tgtEl) {
        const sp = srcEl.position();
        const ss = srcEl.size();
        const tp = tgtEl.position();
        const ts = tgtEl.size();
        const sx = sp.x + ss.width / 2, sy = sp.y + ss.height / 2;
        const tx = tp.x + ts.width / 2, ty = tp.y + ts.height / 2;
        elements.push({
          id: link.id, type: 'arrow',
          x: sx, y: sy, points: [[0, 0], [tx - sx, ty - sy]],
          strokeColor: '#00acc1', strokeWidth: 2, roughness: 0, seed: seed++,
        });
      }
    });

    const excalidrawData = {
      type: 'excalidraw', version: 2, source: 'AWS FinSecOps Topology',
      elements, appState: { viewBackgroundColor: '#0d1b2a' },
    };
    downloadBlob(JSON.stringify(excalidrawData, null, 2),
      `topology_${_selectedProfile || 'export'}.excalidraw`, 'application/json');
  }

  function downloadBlob(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── PNG HD (4x scale) ──
  function exportRasterHD() {
    const svgContent = generateSVG();
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = function () {
      const canvas = document.createElement('canvas');
      const scale = 4;
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      canvas.toBlob(b => {
        const dlUrl = URL.createObjectURL(b);
        const a = document.createElement('a');
        a.href = dlUrl;
        a.download = `topology_${_selectedProfile || 'export'}_hd.png`;
        a.click();
        URL.revokeObjectURL(dlUrl);
      }, 'image/png');
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }

  // ── PDF Diagram (PNG embedded in PDF via backend) ──
  function exportPdfDiagram() {
    // Use SVG export + rasterize to PNG, then download
    // For now, use backend PDF which is table-based
    // TODO: implement canvas-to-PDF in backend
    generateReport('pdf');
  }

  // ── Terraform Export ──
  function exportTerraform() {
    if (!_scanData) return;
    const resources = _scanData.resources || [];
    const profile = _selectedProfile || 'export';
    let tf = `# Terraform topology export — ${profile}\n`;
    tf += `# Generated by AWS FinSecOps Topology Module\n`;
    tf += `# Date: ${_scanData.metadata?.timestamp || new Date().toISOString()}\n\n`;
    tf += `provider "aws" {\n  region = "${_scanData.metadata?.regions_scanned_list?.[0] || 'us-east-1'}"\n}\n\n`;

    // VPCs
    resources.filter(r => r.type === 'vpc').forEach(v => {
      const name = (v.name || v.id).replace(/[^a-zA-Z0-9_-]/g, '_');
      tf += `resource "aws_vpc" "${name}" {\n`;
      tf += `  cidr_block = "${v.cidr || '10.0.0.0/16'}"\n`;
      if (v.ipv6_cidrs?.length) tf += `  assign_generated_ipv6_cidr_block = true\n`;
      tf += `  tags = {\n    Name = "${v.name || v.id}"\n  }\n}\n\n`;
    });

    // Subnets
    resources.filter(r => r.type === 'subnet').forEach(s => {
      const name = (s.name || s.id).replace(/[^a-zA-Z0-9_-]/g, '_');
      const vpcRef = (resources.find(v => v.type === 'vpc' && v.id === s.vpc_id)?.name || s.vpc_id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
      tf += `resource "aws_subnet" "${name}" {\n`;
      tf += `  vpc_id            = aws_vpc.${vpcRef}.id\n`;
      tf += `  cidr_block        = "${s.cidr || '10.0.0.0/24'}"\n`;
      tf += `  availability_zone = "${s.az || 'us-east-1a'}"\n`;
      if (s.map_public_ip) tf += `  map_public_ip_on_launch = true\n`;
      tf += `  tags = {\n    Name = "${s.name || s.id}"\n  }\n}\n\n`;
    });

    // Internet Gateways
    resources.filter(r => r.type === 'igw').forEach(igw => {
      const name = (igw.name || igw.id).replace(/[^a-zA-Z0-9_-]/g, '_');
      const vpcRef = (resources.find(v => v.type === 'vpc' && v.id === igw.vpc_id)?.name || igw.vpc_id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
      tf += `resource "aws_internet_gateway" "${name}" {\n`;
      tf += `  vpc_id = aws_vpc.${vpcRef}.id\n`;
      tf += `  tags = {\n    Name = "${igw.name || igw.id}"\n  }\n}\n\n`;
    });

    // NAT Gateways
    resources.filter(r => r.type === 'nat').forEach(nat => {
      const name = (nat.name || nat.id).replace(/[^a-zA-Z0-9_-]/g, '_');
      const subRef = (resources.find(s => s.type === 'subnet' && s.id === nat.subnet_id)?.name || nat.subnet_id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
      tf += `resource "aws_nat_gateway" "${name}" {\n`;
      tf += `  subnet_id     = aws_subnet.${subRef}.id\n`;
      tf += `  connectivity_type = "${nat.connectivity || 'public'}"\n`;
      tf += `  tags = {\n    Name = "${nat.name || nat.id}"\n  }\n}\n\n`;
    });

    // Security Groups
    resources.filter(r => r.type === 'security_group').forEach(sg => {
      const name = (sg.name || sg.id).replace(/[^a-zA-Z0-9_-]/g, '_');
      const vpcRef = (resources.find(v => v.type === 'vpc' && v.id === sg.vpc_id)?.name || sg.vpc_id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
      tf += `resource "aws_security_group" "${name}" {\n`;
      tf += `  name        = "${sg.name || sg.id}"\n`;
      if (sg.description) tf += `  description = "${sg.description.replace(/"/g, '\\"')}"\n`;
      tf += `  vpc_id      = aws_vpc.${vpcRef}.id\n`;
      tf += `  tags = {\n    Name = "${sg.name || sg.id}"\n  }\n}\n\n`;
    });

    downloadBlob(tf, `topology_${profile}.tf`, 'text/plain');
  }

  // ── JSON Export (raw scan data) ──
  function exportJSON() {
    if (!_scanData) return;
    const data = {
      profile: _scanData.profile,
      account_id: _scanData.account_id,
      metadata: _scanData.metadata,
      resources: _scanData.resources,
      scan_errors: _scanData.scan_errors,
      exported_at: new Date().toISOString(),
    };
    downloadBlob(JSON.stringify(data, null, 2), `topology_${_selectedProfile || 'export'}.json`, 'application/json');
  }

  // ── Reports ───────────────────────────────────────────────
  async function generateReport(fmt) {
    if (!_selectedProfile) return;
    try {
      const res = await fetch('/topology/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: _selectedProfile, format: fmt }),
      });
      const data = await res.json();
      if (data.status === 'ok') loadReports();
      else alert(data.error || 'Report generation failed');
    } catch (e) { console.error(e); }
  }

  async function generateAllReports() {
    if (!_selectedProfile) return;
    try {
      const res = await fetch('/topology/api/reports/generate_all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: _selectedProfile }),
      });
      const data = await res.json();
      if (data.status === 'ok') loadReports();
    } catch (e) { console.error(e); }
  }

  async function loadReports() {
    try {
      const res = await fetch('/topology/api/reports/list');
      const data = await res.json();
      if (data.status !== 'ok') return;

      const reports = data.reports || [];
      const table = document.getElementById('reportListTable');
      const body = document.getElementById('reportListBody');
      const empty = document.getElementById('reportListEmpty');
      const selectAll = document.getElementById('reportSelectAll');

      if (reports.length === 0) {
        if (table) table.style.display = 'none';
        if (empty) empty.style.display = '';
        if (body) body.innerHTML = '';
        return;
      }

      if (table) table.style.display = '';
      if (empty) empty.style.display = 'none';
      if (selectAll) selectAll.checked = false;
      updateDeleteBtnVisibility();

      // Group by base key
      const groups = {};
      const groupRegex = /^(topology_.+_\d{8}_\d{6})\.(html|csv|pdf)$/;
      reports.forEach(r => {
        const m = r.filename.match(groupRegex);
        const key = m ? m[1] : r.filename;
        if (!groups[key]) groups[key] = { files: [], mtime: r.mtime };
        groups[key].files.push(r);
      });

      // Extract profile from key: topology_{profile}_{ts}
      function extractProfile(key) {
        const m = key.match(/^topology_(.+)_\d{8}_\d{6}$/);
        return m ? m[1] : '';
      }

      body.innerHTML = Object.entries(groups).map(([key, group]) => {
        const date = new Date(group.mtime * 1000).toLocaleString();
        const profile = extractProfile(key);
        const formatBadges = group.files.map(f => {
          const ext = f.filename.split('.').pop().toUpperCase();
          const size = f.size > 1048576 ? `${(f.size / 1048576).toFixed(1)}MB` : `${(f.size / 1024).toFixed(0)}KB`;
          const colors = { HTML: '#3b82f6', CSV: '#22c55e', PDF: '#ef4444' };
          const bg = colors[ext] || 'var(--accent)';
          return `<a href="/topology/reports/download/${f.filename}" target="_blank"
            style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;
            text-decoration:none;background:${bg}18;color:${bg};border:1px solid ${bg}30;transition:all .15s"
            onmouseover="this.style.background='${bg}30'" onmouseout="this.style.background='${bg}18'"
          >${ext} <span style="font-weight:400;font-size:10px;opacity:.7">${size}</span></a>`;
        }).join(' ');

        return `<tr>
          <td style="text-align:center">
            <input type="checkbox" class="report-check" data-base="${escHtml(key)}" onchange="window._topoOnReportCheckChange()" style="accent-color:var(--accent)">
          </td>
          <td style="font-size:12px;color:var(--text-secondary);white-space:nowrap">${date}</td>
          <td style="font-weight:600;color:var(--accent);font-size:12px">${escHtml(profile)}</td>
          <td>${formatBadges}</td>
          <td>
            <button class="btn btn-outline btn-sm" onclick="window._topoDeleteReportGroup('${escHtml(key)}')" title="Delete"
              style="font-size:10px;padding:2px 6px;color:#dc2626;border-color:#dc262630">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </td>
        </tr>`;
      }).join('');
    } catch (e) { console.error('Failed to load reports', e); }
  }

  // ── Report selection helpers ──
  function updateDeleteBtnVisibility() {
    const checked = document.querySelectorAll('.report-check:checked').length;
    const btn = document.getElementById('deleteSelectedReportsBtn');
    if (btn) btn.style.display = checked >= 1 ? '' : 'none';
  }

  window._topoOnReportCheckChange = function() {
    updateDeleteBtnVisibility();
    const all = document.querySelectorAll('.report-check');
    const checked = document.querySelectorAll('.report-check:checked');
    const selectAll = document.getElementById('reportSelectAll');
    if (selectAll) selectAll.checked = all.length > 0 && all.length === checked.length;
  };

  window._topoDeleteReportGroup = async function(base) {
    try {
      await fetch('/topology/api/reports/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bases: [base] }),
      });
      loadReports();
    } catch (e) { console.error(e); }
  };

  async function deleteSelectedReports() {
    const checked = document.querySelectorAll('.report-check:checked');
    if (checked.length === 0) return;
    const bases = [...checked].map(cb => cb.dataset.base);
    try {
      await fetch('/topology/api/reports/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bases }),
      });
      loadReports();
    } catch (e) { console.error(e); }
  }

  // ── Section navigation setup ──
  function setupSectionNav() {
    // Wire sidebar links
    document.querySelectorAll('.nav-item[data-section]').forEach(link => {
      link.addEventListener('click', (e) => {
        const section = link.dataset.section;
        if (section === 'guide') return; // guide is a separate page
        e.preventDefault();
        showSection(section);
      });
    });

    // Handle initial hash
    const hash = location.hash.replace('#', '') || 'dashboard';
    if (hash === 'reports') {
      showSection('reports');
    } else {
      showSection('dashboard');
    }
  }

  // ── Event Listeners ───────────────────────────────────────
  function setupEventListeners() {
    // Profile section buttons
    document.getElementById('selectAllProfilesBtn')?.addEventListener('click', selectAllProfiles);
    document.getElementById('clearProfilesBtn')?.addEventListener('click', clearProfiles);

    // Profile search
    const profileSearchInput = document.getElementById('topoProfileSearchInput');
    if (profileSearchInput) {
      profileSearchInput.addEventListener('input', (e) => onProfileSearch(e.target.value));
    }
    document.getElementById('topoProfileSearchClear')?.addEventListener('click', clearProfileSearch);
    document.getElementById('clearCacheBtn')?.addEventListener('click', clearProfileCache);

    // View level toggle
    document.querySelectorAll('.topo-view-btn[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.topo-view-btn[data-view]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        _currentView = btn.dataset.view;
        _visibleTypes = new Set(VIEW_LEVELS[_currentView]);
        renderFilterPanel();
        renderDiagram();
      });
    });

    // VPC selector
    document.getElementById('vpcSelector')?.addEventListener('change', () => renderDiagram());

    // Filter toggle
    document.getElementById('filterToggleBtn')?.addEventListener('click', () => {
      const panel = document.getElementById('filterPanel');
      panel.style.display = panel.style.display === 'none' ? '' : 'none';
    });

    // Filter checkboxes
    document.getElementById('filterChecks')?.addEventListener('change', (e) => {
      if (e.target.type === 'checkbox') {
        const val = e.target.value;
        if (e.target.checked) _visibleTypes.add(val);
        else _visibleTypes.delete(val);
        renderDiagram();
      }
    });

    document.getElementById('filterSelectAll')?.addEventListener('click', () => {
      _visibleTypes = new Set(VIEW_LEVELS.detailed);
      renderFilterPanel();
      renderDiagram();
    });
    document.getElementById('filterDeselectAll')?.addEventListener('click', () => {
      _visibleTypes.clear();
      renderFilterPanel();
      renderDiagram();
    });

    // ── Map Controls (zoom, fullscreen, fit) ──
    setupMapControls();

    // ── Diagram export buttons (in Reports section) ──
    document.getElementById('expPngBtn')?.addEventListener('click', () => { exportWithFeedback('png'); });
    document.getElementById('expSvgBtn')?.addEventListener('click', () => { exportWithFeedback('svg'); });
    document.getElementById('expPdfDiagramBtn')?.addEventListener('click', () => { exportWithFeedback('pdf-diagram'); });
    document.getElementById('expDrawioBtn')?.addEventListener('click', () => { exportWithFeedback('drawio'); });
    document.getElementById('expTerraformBtn')?.addEventListener('click', () => { exportWithFeedback('terraform'); });
    document.getElementById('expJsonBtn')?.addEventListener('click', () => { exportWithFeedback('json'); });

    // Report buttons
    document.getElementById('generateHtmlBtn')?.addEventListener('click', () => { generateReport('html'); });
    document.getElementById('generateCsvBtn')?.addEventListener('click', () => { generateReport('csv'); });
    document.getElementById('generatePdfBtn')?.addEventListener('click', () => { generateReport('pdf'); });
    document.getElementById('generateAllBtn')?.addEventListener('click', () => { generateAllReports(); });
    document.getElementById('refreshReportsBtn')?.addEventListener('click', () => { loadReports(); });
    document.getElementById('deleteSelectedReportsBtn')?.addEventListener('click', () => { deleteSelectedReports(); });
    document.getElementById('reportSelectAll')?.addEventListener('change', (e) => {
      document.querySelectorAll('.report-check').forEach(cb => { cb.checked = e.target.checked; });
      updateDeleteBtnVisibility();
    });

    // Scan history row click (ignore delete button clicks)
    document.getElementById('scanHistoryList')?.addEventListener('click', (e) => {
      if (e.target.closest('.report-delete-btn')) return;
      const row = e.target.closest('.topo-history-row');
      if (!row) return;
      const profile = row.dataset.profile;
      if (profile) selectProfile(profile);
    });

    // Theme change re-render
    document.addEventListener('themechange', () => {
      if (_scanData) renderDiagram();
    });

    // Region filter
    document.getElementById('regionFilter')?.addEventListener('change', (e) => {
      _selectedRegionFilter = e.target.value;
      renderDiagram();
    });

    // Search
    const searchInput = document.getElementById('topoSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => searchResources(e.target.value));
      searchInput.addEventListener('focus', (e) => { if (e.target.value) searchResources(e.target.value); });
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { e.target.value = ''; closeSearchResults(); }
      });
    }
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.topo-search-wrap')) closeSearchResults();
    });

    // Context menu
    document.addEventListener('click', () => hideContextMenu());
    document.getElementById('contextMenu')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn || !_contextMenuData) return;
      handleContextAction(btn.dataset.action, _contextMenuData);
      hideContextMenu();
    });

    // Minimap toggle
    document.getElementById('minimapToggle')?.addEventListener('click', () => {
      _minimapVisible = !_minimapVisible;
      const mc = document.getElementById('minimapContainer');
      if (mc) mc.style.display = _minimapVisible ? '' : 'none';
    });

    // Reset view button
    document.getElementById('mapResetBtn')?.addEventListener('click', () => {
      if (!_paper) return;
      _paper.translate(0, 0);
      _paper.scale(1, 1);
      _currentScale = 1;
      updateZoomSlider();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'f' && !e.ctrlKey && !e.metaKey) {
        const searchEl = document.getElementById('topoSearchInput');
        if (searchEl) { e.preventDefault(); searchEl.focus(); }
      }
      if (e.key === '1') setViewLevel('basic');
      if (e.key === '2') setViewLevel('medium');
      if (e.key === '3') setViewLevel('detailed');
      if (e.key === '0') fitContent();
    });
  }

  function setViewLevel(level) {
    document.querySelectorAll('.topo-view-btn[data-view]').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.topo-view-btn[data-view="${level}"]`);
    if (btn) btn.classList.add('active');
    _currentView = level;
    _visibleTypes = new Set(VIEW_LEVELS[_currentView]);
    renderFilterPanel();
    renderDiagram();
  }

  // ══════════════════════════════════════════════════════════
  //  Search & Highlight
  // ══════════════════════════════════════════════════════════

  function searchResources(query) {
    const container = document.getElementById('topoSearchResults');
    if (!container || !_scanData) return;
    const q = query.toLowerCase().trim();
    if (!q || q.length < 2) { closeSearchResults(); return; }

    const resources = _scanData.resources || [];
    const matches = resources.filter(r => {
      const searchStr = `${r.name || ''} ${r.id || ''} ${r.type || ''} ${r.region || ''} ${r.cidr || ''} ${r.public_ip || ''} ${r.private_ip || ''}`.toLowerCase();
      return searchStr.includes(q);
    }).slice(0, 20);

    if (!matches.length) {
      container.innerHTML = `<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:12px">${t('topo_no_results') || 'No results found'}</div>`;
      container.classList.add('active');
      return;
    }

    container.innerHTML = matches.map(r => {
      const color = TYPE_COLORS[r.type] || '#888';
      const typeLabel = TYPE_LABELS[r.type] || r.type;
      return `<div class="topo-search-result-item" data-resource-id="${escHtml(r.id)}">
        <span class="result-type" style="background:${color};color:#000">${typeLabel}</span>
        <span class="result-name">${escHtml(r.name || r.id)}</span>
        <span class="result-region">${escHtml(r.region || '')}</span>
      </div>`;
    }).join('');
    container.classList.add('active');

    container.onclick = (e) => {
      const item = e.target.closest('.topo-search-result-item');
      if (!item) return;
      const rid = item.dataset.resourceId;
      highlightAndZoomToNode(rid);
      closeSearchResults();
      document.getElementById('topoSearchInput').value = '';
    };
  }

  function closeSearchResults() {
    const c = document.getElementById('topoSearchResults');
    if (c) c.classList.remove('active');
  }

  function highlightAndZoomToNode(nodeId) {
    if (!_graph || !_paper) return;
    const cell = _graph.getCell(nodeId);
    if (!cell || !cell.isElement()) return;

    // Clear previous highlight
    clearHighlight();

    // Highlight the target node
    _highlightedNodeId = nodeId;
    const pos = cell.position();
    const size = cell.size();

    // Zoom to the node
    const paperW = _paper.el.clientWidth || 1200;
    const paperH = _paper.el.clientHeight || 780;
    const targetScale = 1.2;
    const tx = paperW / 2 - (pos.x + size.width / 2) * targetScale;
    const ty = paperH / 2 - (pos.y + size.height / 2) * targetScale;
    _paper.scale(targetScale, targetScale);
    _paper.translate(tx, ty);
    _currentScale = targetScale;
    updateZoomSlider();

    // Dim non-connected elements
    highlightConnections(nodeId);

    // Show detail panel
    const d = cell.prop('resourceData');
    if (d) showNodeDetail(d);
  }

  function highlightConnections(nodeId) {
    if (!_graph) return;
    const connectedIds = new Set([nodeId]);

    // Find all connected nodes via links
    _graph.getLinks().forEach(link => {
      const srcId = link.source().id;
      const tgtId = link.target().id;
      if (srcId === nodeId) connectedIds.add(tgtId);
      if (tgtId === nodeId) connectedIds.add(srcId);
    });

    // Also include parent/children
    const cell = _graph.getCell(nodeId);
    if (cell) {
      const parent = cell.getParentCell();
      if (parent) connectedIds.add(parent.id);
      (cell.getEmbeddedCells() || []).forEach(c => connectedIds.add(c.id));
    }

    // Apply dimming via SVG attributes
    _graph.getElements().forEach(el => {
      const view = _paper.findViewByModel(el);
      if (!view) return;
      if (connectedIds.has(el.id)) {
        view.el.classList.remove('topo-node-dimmed');
        view.el.classList.add('topo-node-highlighted');
      } else {
        view.el.classList.add('topo-node-dimmed');
        view.el.classList.remove('topo-node-highlighted');
      }
    });
    _graph.getLinks().forEach(link => {
      const view = _paper.findViewByModel(link);
      if (!view) return;
      const srcId = link.source().id;
      const tgtId = link.target().id;
      if (connectedIds.has(srcId) && connectedIds.has(tgtId)) {
        view.el.classList.remove('topo-link-dimmed');
      } else {
        view.el.classList.add('topo-link-dimmed');
      }
    });
  }

  function clearHighlight() {
    _highlightedNodeId = null;
    if (!_graph || !_paper) return;
    _graph.getElements().forEach(el => {
      const view = _paper.findViewByModel(el);
      if (view) {
        view.el.classList.remove('topo-node-dimmed', 'topo-node-highlighted');
      }
    });
    _graph.getLinks().forEach(link => {
      const view = _paper.findViewByModel(link);
      if (view) view.el.classList.remove('topo-link-dimmed');
    });
  }

  // ══════════════════════════════════════════════════════════
  //  Context Menu
  // ══════════════════════════════════════════════════════════

  function showContextMenu(x, y, resourceData) {
    _contextMenuData = resourceData;
    const menu = document.getElementById('contextMenu');
    if (!menu) return;
    menu.style.display = '';
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;

    // Show/hide ARN option
    const arnBtn = menu.querySelector('[data-action="copy-arn"]');
    if (arnBtn) arnBtn.style.display = resourceData.arn ? '' : 'none';

    // Show/hide VPC filter option
    const vpcBtn = menu.querySelector('[data-action="filter-vpc"]');
    if (vpcBtn) vpcBtn.style.display = resourceData.vpc_id ? '' : 'none';

    // Ensure menu doesn't go off-screen
    const rect = menu.getBoundingClientRect();
    if (rect.right > window.innerWidth) menu.style.left = `${x - rect.width}px`;
    if (rect.bottom > window.innerHeight) menu.style.top = `${y - rect.height}px`;
  }

  function hideContextMenu() {
    const menu = document.getElementById('contextMenu');
    if (menu) menu.style.display = 'none';
    _contextMenuData = null;
  }

  function handleContextAction(action, data) {
    switch (action) {
      case 'copy-id':
        navigator.clipboard.writeText(data.id || '');
        break;
      case 'copy-arn':
        navigator.clipboard.writeText(data.arn || '');
        break;
      case 'filter-vpc':
        if (data.vpc_id) {
          const sel = document.getElementById('vpcSelector');
          if (sel) { sel.value = data.vpc_id; renderDiagram(); }
        }
        break;
      case 'highlight-connections':
        highlightAndZoomToNode(data.id);
        break;
      case 'detail':
        showNodeDetail(data);
        break;
    }
  }

  // ══════════════════════════════════════════════════════════
  //  Minimap
  // ══════════════════════════════════════════════════════════

  function updateMinimap() {
    if (!_paper || !_graph || !_minimapVisible) return;
    const canvas = document.getElementById('minimapCanvas');
    const viewport = document.getElementById('minimapViewport');
    if (!canvas || !viewport) return;

    const ctx = canvas.getContext('2d');
    const cw = canvas.width;
    const ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    const elements = _graph.getElements();
    if (!elements.length) return;

    // Compute bounding box of all elements
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    elements.forEach(el => {
      const p = el.position();
      const s = el.size();
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x + s.width);
      maxY = Math.max(maxY, p.y + s.height);
    });

    const pad = 40;
    const contentW = maxX - minX + pad * 2;
    const contentH = maxY - minY + pad * 2;
    const scaleX = cw / contentW;
    const scaleY = ch / contentH;
    const minimapScale = Math.min(scaleX, scaleY);

    const offsetX = (cw - contentW * minimapScale) / 2;
    const offsetY = (ch - contentH * minimapScale) / 2;

    // Draw elements as colored rectangles
    elements.forEach(el => {
      const p = el.position();
      const s = el.size();
      const d = el.prop('resourceData');
      const type = d?.nodeType || d?.type || '';
      const color = TYPE_COLORS[type] || '#334155';

      const x = (p.x - minX + pad) * minimapScale + offsetX;
      const y = (p.y - minY + pad) * minimapScale + offsetY;
      const w = Math.max(2, s.width * minimapScale);
      const h = Math.max(2, s.height * minimapScale);

      ctx.fillStyle = color + '60';
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.5;
      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x, y, w, h);
    });

    // Draw viewport indicator
    const paperW = _paper.el.clientWidth || 1200;
    const paperH = _paper.el.clientHeight || 780;
    const translate = _paper.translate();
    const scale = _paper.scale().sx;

    const vpX = (-translate.tx / scale - minX + pad) * minimapScale + offsetX;
    const vpY = (-translate.ty / scale - minY + pad) * minimapScale + offsetY;
    const vpW = (paperW / scale) * minimapScale;
    const vpH = (paperH / scale) * minimapScale;

    viewport.style.left = `${Math.max(0, vpX)}px`;
    viewport.style.top = `${Math.max(0, vpY)}px`;
    viewport.style.width = `${Math.min(cw, vpW)}px`;
    viewport.style.height = `${Math.min(ch, vpH)}px`;
  }

  // ══════════════════════════════════════════════════════════
  //  Watermark
  // ══════════════════════════════════════════════════════════

  function updateWatermark() {
    const wm = document.getElementById('canvasWatermark');
    if (!wm || !_scanData) return;
    const meta = _scanData.metadata || {};
    const profile = _scanData.profile || '';
    const ts = meta.timestamp || '';
    wm.textContent = `${profile} | ${ts} | ${meta.resource_count || 0} resources`;
  }

  // ── Helpers ───────────────────────────────────────────────
  function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function escXml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function t(key) {
    if (typeof TRANSLATIONS !== 'undefined') {
      const lang = localStorage.getItem('finops_lang') || 'en';
      return TRANSLATIONS[lang]?.[key] || TRANSLATIONS.en?.[key] || '';
    }
    return '';
  }

})();
