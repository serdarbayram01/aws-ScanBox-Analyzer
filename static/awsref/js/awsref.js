/* AWS Reference module — vanilla JS controller.
   Depends on global helpers from /static/js/i18n.js:
     - t(key) / setLang / getLang
     - escapeHtml
   Reads from /awsref/api/* endpoints. No AWS auth, no boto3. */

(function () {
  'use strict';

  // -------------------- State --------------------
  const state = {
    regions:         [],
    services:        [],
    currentRegion:   'eu-central-1',
    currentTab:      'services',
    // Services table — sort + filter
    svcSort:         { col: 'category', dir: 'asc' },
    matrix:          null,         // raw response from /api/cloudping-matrix
    matrixPct:       'p_50',
    matrixTf:        '1D',
    matrixShow:      'all',
    matrixFromQ:     '',
    matrixToQ:       '',
  };

  // -------------------- DOM lookup --------------------
  const $ = (sel) => document.querySelector(sel);

  // -------------------- Latency helpers --------------------
  function latencyClass(ms) {
    if (ms == null) return 'awsref-latency-na';
    if (ms < 50)    return 'awsref-latency-good';
    if (ms < 150)   return 'awsref-latency-mid';
    return 'awsref-latency-bad';
  }
  function fmtMs(ms) {
    if (ms == null) return '—';
    return Number(ms).toFixed(0);
  }

  // -------------------- Tabs --------------------
  function switchAwsRefTab(tab) {
    state.currentTab = tab;
    document.querySelectorAll('#awsrefTabs .fw-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    $('#paneServices').style.display = (tab === 'services') ? '' : 'none';
    $('#paneMatrix').style.display   = (tab === 'matrix')   ? '' : 'none';
    if (tab === 'matrix' && !state.matrix) {
      loadAwsRefMatrix();
    }
  }
  window.switchAwsRefTab = switchAwsRefTab;

  // -------------------- Regions (populate select) --------------------
  async function loadRegions() {
    try {
      const resp = await fetch('/awsref/api/regions');
      const data = await resp.json();
      state.regions = data.regions || [];
      const select = $('#awsrefRegionSelect');
      const groups = {};
      // Group by geo bucket for a tidy <optgroup> layout
      for (const r of state.regions) {
        const geo = r.geo || 'OTHER';
        (groups[geo] = groups[geo] || []).push(r);
      }
      const geoOrder = ['EU', 'NA', 'APAC', 'SA', 'ME', 'AF', 'OTHER'];
      const optHtml = [];
      for (const g of geoOrder) {
        if (!groups[g]) continue;
        optHtml.push('<optgroup label="' + escapeHtml(g) + '">');
        for (const r of groups[g]) {
          // Region itself
          const sel = r.code === state.currentRegion ? ' selected' : '';
          optHtml.push(
            '<option value="' + escapeHtml(r.code) + '"' + sel + '>' +
              escapeHtml(r.code + '  ·  ' + r.name) +
            '</option>'
          );
          // Local Zones (indented)
          for (const lz of (r.lzs || [])) {
            const cityCode = lz.split('-').slice(-2)[0]; // e.g. "ist" from "eu-central-1-ist-1a"
            const city = (data.lz_city_names || {})[cityCode] || cityCode.toUpperCase();
            const sel2 = lz === state.currentRegion ? ' selected' : '';
            optHtml.push(
              '<option value="' + escapeHtml(lz) + '"' + sel2 + '>' +
                '    ↳ ' + escapeHtml(lz + '  ·  ' + city + ' LZ') +
              '</option>'
            );
          }
        }
        optHtml.push('</optgroup>');
      }
      select.innerHTML = optHtml.join('');
      loadAwsRefServices(state.currentRegion);
    } catch (e) {
      $('#awsrefServiceTBody').innerHTML =
        '<tr><td colspan="6" class="awsref-empty">' + escapeHtml(t('awsref_load_failed') || 'Failed to load regions') +
        ': ' + escapeHtml(e.message) + '</td></tr>';
    }
  }

  // -------------------- Services table --------------------
  async function loadAwsRefServices(region) {
    state.currentRegion = region;
    const tbody = $('#awsrefServiceTBody');
    tbody.innerHTML =
      '<tr><td colspan="6" class="awsref-empty"><span class="spinner"></span> ' +
      escapeHtml(t('state_loading') || 'Loading...') + '</td></tr>';
    try {
      const resp = await fetch('/awsref/api/services?region=' + encodeURIComponent(region));
      const data = await resp.json();
      state.services = data.services || [];
      $('#awsrefPrettyName').textContent = data.pretty_name || '';
      _populateAwsRefSvcFilters();
      renderAwsRefServices();
      // If this is an LZ, also load the LZ-specific catalogs.
      const isLz = !!data.is_local_zone;
      $('#awsrefLzDetail').style.display = isLz ? '' : 'none';
      if (isLz) loadAwsRefLzDetail(region);
    } catch (e) {
      tbody.innerHTML = '<tr><td colspan="6" class="awsref-empty">' +
        escapeHtml(e.message) + '</td></tr>';
    }
  }
  window.loadAwsRefServices = loadAwsRefServices;

  // -------------------- LZ Detail (catalog + instance types) --------------------
  const state_lz = {
    catalog:    [],
    catSort:    { col: 'category', dir: 'asc' },
  };

  async function loadAwsRefLzDetail(lzCode) {
    try {
      const [svcResp, instResp] = await Promise.all([
        fetch('/awsref/api/lz-services?region='        + encodeURIComponent(lzCode)),
        fetch('/awsref/api/lz-instance-types?region=' + encodeURIComponent(lzCode)),
      ]);
      const svc  = await svcResp.json();
      const inst = await instResp.json();
      state_lz.catalog = svc.entries || [];
      _renderAwsRefInstanceChips(inst);
      _populateAwsRefLzCatFilter();
      _renderAwsRefLzCatStats(svc.totals || {}, svc.source_counts || {}, svc.aws_rt);
      renderAwsRefLzCat();
    } catch (e) {
      $('#awsrefLzCatTBody').innerHTML =
        '<tr><td colspan="4" class="awsref-empty">' + escapeHtml(e.message) + '</td></tr>';
    }
  }
  window.loadAwsRefLzDetail = loadAwsRefLzDetail;

  function _renderAwsRefInstanceChips(inst) {
    const wrap = $('#awsrefLzInstChips');
    const src  = $('#awsrefLzInstSource');
    if (!wrap) return;
    const types = inst.instance_types || [];
    wrap.innerHTML = types.length
      ? types.map(it => '<span class="awsref-inst-chip">' + escapeHtml(it) + '</span>').join('')
      : '<span class="awsref-empty">' + escapeHtml(t('awsref_no_data') || 'No data') + '</span>';
    if (src) src.textContent = inst.source ? '· ' + inst.source : '';
  }

  function _populateAwsRefLzCatFilter() {
    const sel = $('#awsrefLzCatFilterCat');
    if (!sel) return;
    const prev = sel.value;
    const cats = [...new Set(state_lz.catalog.map(e => e.category))].sort();
    sel.innerHTML = '<option value="all">all categories</option>' +
      cats.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
  }

  function _renderAwsRefLzCatStats(totals, srcCounts, awsRtStatus) {
    const el = $('#awsrefLzCatStats');
    if (!el) return;
    const sup = totals.supported || 0;
    const par = totals.partial   || 0;
    const uns = totals.unsupported || 0;
    const tot = totals.entries  || (sup + par + uns);
    const cur = (srcCounts || {}).curated || 0;
    const der = (srcCounts || {}).derived || 0;
    const ext = (srcCounts || {})['aws-rt'] || 0;
    el.innerHTML =
      '<span class="awsref-lz-stat awsref-lz-stat-total" id="awsrefLzCatTotalBadge">' + tot + ' total</span>' +
      '<span class="awsref-lz-stat awsref-lz-stat-sup">' + sup + ' supported</span>' +
      '<span class="awsref-lz-stat awsref-lz-stat-par">' + par + ' partial</span>' +
      '<span class="awsref-lz-stat awsref-lz-stat-uns">' + uns + ' unsupported</span>' +
      '<span class="awsref-lz-stat awsref-lz-stat-src" title="' +
        escapeHtml('curated: ' + cur + ' · derived: ' + der + ' · from AWS regional-services JSON: ' + ext +
                   (awsRtStatus ? ' · aws-rt: ' + awsRtStatus : '')) +
      '">⓵ ' + cur + ' curated · ⓶ ' + der + ' derived · ⓷ ' + ext + ' AWS-published</span>';
  }

  function sortAwsRefLzCat(col) {
    if (state_lz.catSort.col === col) {
      state_lz.catSort.dir = (state_lz.catSort.dir === 'asc' ? 'desc' : 'asc');
    } else {
      state_lz.catSort.col = col;
      state_lz.catSort.dir = 'asc';
    }
    renderAwsRefLzCat();
  }
  window.sortAwsRefLzCat = sortAwsRefLzCat;

  const _STATUS_ORDER = { 'supported': 0, 'partial': 1, 'unsupported': 2 };

  function renderAwsRefLzCat() {
    const tbody = $('#awsrefLzCatTBody');
    if (!tbody) return;
    if (!state_lz.catalog.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="awsref-empty">' +
        escapeHtml(t('awsref_no_data') || 'No data') + '</td></tr>';
      return;
    }
    const fCat   =  $('#awsrefLzCatFilterCat')?.value    || 'all';
    const fSvc   = ($('#awsrefLzCatFilterSvc')?.value    || '').toLowerCase().trim();
    const fStat  =  $('#awsrefLzCatFilterStatus')?.value || 'all';
    const fNotes = ($('#awsrefLzCatFilterNotes')?.value  || '').toLowerCase().trim();

    let rows = state_lz.catalog.filter(e => {
      if (fCat !== 'all' && e.category !== fCat) return false;
      if (fStat !== 'all' && e.status !== fStat) return false;
      if (fSvc && !(e.service || '').toLowerCase().includes(fSvc)) return false;
      if (fNotes && !(e.notes || '').toLowerCase().includes(fNotes)) return false;
      return true;
    });

    const { col, dir } = state_lz.catSort;
    const mul = (dir === 'desc' ? -1 : 1);
    rows.sort((a, b) => {
      let va = a[col], vb = b[col];
      if (col === 'status') {
        const oa = _STATUS_ORDER[va] ?? 99;
        const ob = _STATUS_ORDER[vb] ?? 99;
        return (oa - ob) * mul;
      }
      return ((va || '').toString()).localeCompare((vb || '').toString()) * mul;
    });

    // Sort indicators
    document.querySelectorAll('#awsrefLzCatTable th.awsref-sortable').forEach(th => {
      const ind = th.querySelector('.awsref-sort-ind');
      if (!ind) return;
      if (th.dataset.sortCol === col) {
        ind.textContent = (dir === 'asc' ? ' ↑' : ' ↓');
        th.classList.add('awsref-sorted');
      } else {
        ind.textContent = '';
        th.classList.remove('awsref-sorted');
      }
    });

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="awsref-empty">' +
        escapeHtml(t('awsref_no_results') || 'No rows match the filters') + '</td></tr>';
      return;
    }

    // Every row shows its own category — no group-blank rendering, since that
    // looked like missing data on a long table. The visual scan stays clean
    // because the badge class keeps each category label compact.
    const out = rows.map(e => {
      return '<tr>' +
        '<td><span class="awsref-lz-cat-cell">' + escapeHtml(e.category) + '</span></td>' +
        '<td style="font-family:var(--font-mono); font-size:11.5px">' + escapeHtml(e.service) + '</td>' +
        '<td><span class="awsref-lz-status awsref-lz-status-' + e.status + '">' +
          escapeHtml(e.status) + '</span></td>' +
        '<td style="color:var(--text-muted); font-size:11.5px">' + escapeHtml(e.notes || '') + '</td>' +
      '</tr>';
    }).join('');
    tbody.innerHTML = out;

    // Update filter-aware count badge so user sees "X of Y" when filters apply.
    const totalEl = $('#awsrefLzCatTotalBadge');
    if (totalEl) {
      const all = state_lz.catalog.length;
      const shown = rows.length;
      totalEl.textContent = (shown === all)
        ? (all + ' total')
        : (shown + ' / ' + all + ' ' + (t('awsref_of') || 'of') + ' total');
      totalEl.classList.toggle('awsref-lz-stat-filtering', shown !== all);
    }
  }
  window.renderAwsRefLzCat = renderAwsRefLzCat;

  function sortAwsRefServices(col) {
    if (state.svcSort.col === col) {
      state.svcSort.dir = (state.svcSort.dir === 'asc' ? 'desc' : 'asc');
    } else {
      state.svcSort.col = col;
      state.svcSort.dir = 'asc';
    }
    renderAwsRefServices();
  }
  window.sortAwsRefServices = sortAwsRefServices;

  const _SCOPE_LABEL = {
    'lz-data-plane':  'LZ data-plane',
    'regional':       'Regional',
    'global':         'Global',
    'lz-link-local':  'Link-local',
  };

  function _populateAwsRefSvcFilters() {
    // Category dropdown — unique values from current services
    const catSel = $('#awsrefSvcFilterCategory');
    const scpSel = $('#awsrefSvcFilterScope');
    if (!catSel || !scpSel) return;
    const cats = [...new Set(state.services.map(s => s.category))].sort();
    const scps = [...new Set(state.services.map(s => s.lz_scope))].sort();
    const prevCat = catSel.value;
    const prevScp = scpSel.value;
    catSel.innerHTML = '<option value="all">all</option>' +
      cats.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    scpSel.innerHTML = '<option value="all">all</option>' +
      scps.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(_SCOPE_LABEL[s] || s)}</option>`).join('');
    if ([...catSel.options].some(o => o.value === prevCat)) catSel.value = prevCat;
    if ([...scpSel.options].some(o => o.value === prevScp)) scpSel.value = prevScp;
  }

  function _reachState(ms, probed) {
    // returns 'reachable' | 'unreachable' | 'not-probed'
    if (!probed) return 'not-probed';
    return (ms != null) ? 'reachable' : 'unreachable';
  }

  function renderAwsRefServices() {
    const tbody = $('#awsrefServiceTBody');
    const countEl = $('#awsrefSvcCount');
    const total = state.services.length;
    if (!total) {
      tbody.innerHTML = '<tr><td colspan="6" class="awsref-empty">' +
        escapeHtml(t('awsref_no_services') || 'No services') + '</td></tr>';
      if (countEl) countEl.textContent = '';
      return;
    }

    // Read filters
    const fName = ($('#awsrefSvcFilterName')?.value     || '').toLowerCase().trim();
    const fEp   = ($('#awsrefSvcFilterEndpoint')?.value || '').toLowerCase().trim();
    const fCat  =  $('#awsrefSvcFilterCategory')?.value || 'all';
    const fScp  =  $('#awsrefSvcFilterScope')?.value    || 'all';
    const fP50  =  $('#awsrefSvcFilterP50')?.value      || 'all';
    const fP95  =  $('#awsrefSvcFilterP95')?.value      || 'all';
    const probed = state.services.some(s => s.p50_ms != null || s.reachable != null);

    let rows = state.services.filter(s => {
      if (fName && !((s.name || '').toLowerCase().includes(fName))) return false;
      if (fEp   && !((s.endpoint || '').toLowerCase().includes(fEp))) return false;
      if (fCat !== 'all' && s.category !== fCat) return false;
      if (fScp !== 'all' && s.lz_scope !== fScp) return false;
      if (fP50 !== 'all' && _reachState(s.p50_ms, probed) !== fP50) return false;
      if (fP95 !== 'all' && _reachState(s.p95_ms, probed) !== fP95) return false;
      return true;
    });

    // Sort
    const { col, dir } = state.svcSort;
    const mul = (dir === 'desc' ? -1 : 1);
    rows.sort((a, b) => {
      let va = a[col], vb = b[col];
      // numeric for ms fields, with nulls sorted last on ascending
      if (col === 'p50_ms' || col === 'p95_ms') {
        if (va == null && vb == null) return 0;
        if (va == null) return 1;   // nulls always at the bottom
        if (vb == null) return -1;
        return (va - vb) * mul;
      }
      va = (va || '').toString();
      vb = (vb || '').toString();
      return va.localeCompare(vb) * mul;
    });

    // Sort indicators on header
    document.querySelectorAll('#awsrefServiceTable th.awsref-sortable').forEach(th => {
      const ind = th.querySelector('.awsref-sort-ind');
      if (!ind) return;
      if (th.dataset.sortCol === col) {
        ind.textContent = (dir === 'asc' ? ' ↑' : ' ↓');
        th.classList.add('awsref-sorted');
      } else {
        ind.textContent = '';
        th.classList.remove('awsref-sorted');
      }
    });

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="awsref-empty">' +
        escapeHtml(t('awsref_no_results') || 'No rows match the filters') + '</td></tr>';
      if (countEl) countEl.textContent = `0 ${t('awsref_of') || 'of'} ${total}`;
      return;
    }

    const out = rows.map(s => {
      const scopeClass = 'awsref-scope-' + s.lz_scope;
      const scopeLabel = _SCOPE_LABEL[s.lz_scope] || s.lz_scope;
      return '<tr>' +
        '<td><strong>' + escapeHtml(s.name) + '</strong>' +
          (s.description_en
            ? '<div style="font-size:10px;color:var(--text-muted)">' + escapeHtml(s.description_en) + '</div>'
            : '') +
        '</td>' +
        '<td>' + escapeHtml(s.category) + '</td>' +
        '<td><span class="awsref-scope-badge ' + scopeClass + '">' + escapeHtml(scopeLabel) + '</span></td>' +
        '<td style="font-family:var(--font-mono);font-size:11px">' + escapeHtml(s.endpoint || '—') + '</td>' +
        '<td class="' + latencyClass(s.p50_ms) + '">' + fmtMs(s.p50_ms) + '</td>' +
        '<td class="' + latencyClass(s.p95_ms) + '">' + fmtMs(s.p95_ms) + '</td>' +
      '</tr>';
    }).join('');
    tbody.innerHTML = out;
    if (countEl) countEl.textContent = `${rows.length} ${t('awsref_of') || 'of'} ${total}`;
  }
  window.renderAwsRefServices = renderAwsRefServices;

  async function probeAwsRefServices() {
    const btn = $('#awsrefProbeBtn');
    btn.disabled = true;
    btn.textContent = t('awsref_probing') || 'Probing...';
    try {
      const resp = await fetch('/awsref/api/services?region=' +
                               encodeURIComponent(state.currentRegion) + '&probe=1');
      const data = await resp.json();
      state.services = data.services || [];
      renderAwsRefServices();
    } finally {
      btn.disabled = false;
      btn.textContent = t('awsref_probe_now') || 'Probe latency';
    }
  }
  window.probeAwsRefServices = probeAwsRefServices;

  // -------------------- CloudPing pairwise matrix --------------------
  async function loadAwsRefMatrix(refresh) {
    state.matrixPct = $('#awsrefPercentile')?.value || 'p_50';
    state.matrixTf  = $('#awsrefTimeframe')?.value  || '1D';

    const tbody = $('#awsrefMatrixTBody');
    const status = $('#awsrefMatrixStatus');
    tbody.innerHTML =
      '<tr><td class="awsref-empty"><span class="spinner"></span> ' +
      escapeHtml(t('awsref_probing') || 'Fetching CloudPing matrix...') + '</td></tr>';
    if (status) status.textContent = '';
    try {
      const qs = new URLSearchParams({
        percentile: state.matrixPct,
        timeframe:  state.matrixTf,
      });
      if (refresh) qs.set('refresh', '1');
      const resp = await fetch('/awsref/api/cloudping-matrix?' + qs);
      const data = await resp.json();
      if (data.status !== 'ok') {
        tbody.innerHTML = '<tr><td class="awsref-empty">' +
          escapeHtml(data.error || 'Failed to load CloudPing matrix') + '</td></tr>';
        return;
      }
      state.matrix = data;
      renderAwsRefMatrix();
    } catch (e) {
      tbody.innerHTML = '<tr><td class="awsref-empty">' +
        escapeHtml(e.message) + '</td></tr>';
    }
  }
  window.loadAwsRefMatrix = loadAwsRefMatrix;

  function toggleAwsRefAbout() {
    const panel = $('#awsrefAboutPanel');
    if (!panel) return;
    panel.style.display = (panel.style.display === 'none' ? '' : 'none');
  }
  window.toggleAwsRefAbout = toggleAwsRefAbout;

  function switchAwsRefInfoTab(tabKey) {
    document.querySelectorAll('.awsref-info-tab').forEach(b => {
      b.classList.toggle('active', b.dataset.infoTab === tabKey);
    });
    document.querySelectorAll('.awsref-info-pane').forEach(p => {
      p.style.display = (p.dataset.infoPane === tabKey ? '' : 'none');
    });
  }
  window.switchAwsRefInfoTab = switchAwsRefInfoTab;

  // Metrics tab — chip selector that swaps the visible definition block.
  function selectAwsRefMetric(metricKey) {
    document.querySelectorAll('.awsref-metric-chip').forEach(b => {
      b.classList.toggle('active', b.dataset.metric === metricKey);
    });
    document.querySelectorAll('.awsref-metric-def').forEach(d => {
      d.style.display = (d.dataset.metricDef === metricKey ? '' : 'none');
    });
  }
  window.selectAwsRefMetric = selectAwsRefMetric;

  // Delegate clicks on the chip group (the chips are static in HTML)
  document.addEventListener('click', (ev) => {
    const chip = ev.target.closest('.awsref-metric-chip');
    if (!chip) return;
    selectAwsRefMetric(chip.dataset.metric);
  });

  // PERCENTILE / TIMEFRAME dropdown change → re-fetch (server may have cached
  // result OR may return data_substituted=true if CLOUDPING_PROXY_URL not set).
  function onAwsRefFilterChange() {
    loadAwsRefMatrix(false);
  }
  window.onAwsRefFilterChange = onAwsRefFilterChange;

  function _cellClass(ms) {
    if (ms == null) return 'cell-na';
    if (ms < 100)   return 'cell-good';
    if (ms < 180)   return 'cell-mid';
    return 'cell-bad';
  }

  // Custom horizontal tooltip for the matrix — rotated column headers are
  // hard to read at a glance; this pops a clean horizontal readout on
  // hover for any column header, row header, or cell.
  let _matrixTooltipEl = null;
  function _ensureMatrixTooltip() {
    if (_matrixTooltipEl) return _matrixTooltipEl;
    const el = document.createElement('div');
    el.className = 'awsref-matrix-tooltip';
    el.id = 'awsrefMatrixTooltip';
    document.body.appendChild(el);
    _matrixTooltipEl = el;
    return el;
  }

  function _hideMatrixTooltip() {
    if (_matrixTooltipEl) _matrixTooltipEl.style.display = 'none';
  }

  function _showMatrixTooltip(target) {
    const text = target.getAttribute('data-tt');
    if (!text) return;
    const el = _ensureMatrixTooltip();
    // Allow a "primary | secondary" split so cell tooltips can show
    // "from → to: 12 ms" with a second line for friendly region names.
    const parts = text.split('||');
    el.innerHTML = parts
      .map(p => '<div class="awsref-tt-line">' + escapeHtml(p.trim()) + '</div>')
      .join('');
    el.style.display = 'block';
    const r = target.getBoundingClientRect();
    // Centre horizontally above the target. For rotated column headers the
    // bounding rect is the rotated bounding box, so its centre is still the
    // right anchor point.
    let left = r.left + r.width / 2;
    let top  = r.top;
    // Clamp horizontally so we don't run off-screen for first/last columns.
    const ttRect = el.getBoundingClientRect();
    const margin = 8;
    if (left - ttRect.width / 2 < margin) left = ttRect.width / 2 + margin;
    if (left + ttRect.width / 2 > window.innerWidth - margin) {
      left = window.innerWidth - ttRect.width / 2 - margin;
    }
    el.style.left = left + 'px';
    el.style.top  = top  + 'px';
  }

  function _attachMatrixTooltip() {
    const wrap = $('.awsref-matrix-wrap');
    if (!wrap || wrap.dataset.ttBound) return;
    wrap.dataset.ttBound = '1';
    wrap.addEventListener('mouseover', (e) => {
      const tgt = e.target.closest('[data-tt]');
      if (tgt) _showMatrixTooltip(tgt);
    });
    wrap.addEventListener('mouseout', (e) => {
      // Hide when leaving an element that has a tooltip and we're not
      // entering another tooltipped element.
      const from = e.target.closest('[data-tt]');
      const to   = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('[data-tt]');
      if (from && from !== to) _hideMatrixTooltip();
    });
    // Hide on scroll inside the matrix or page scroll — sticky positioning
    // would otherwise leave the tooltip floating in a misleading position.
    wrap.addEventListener('scroll', _hideMatrixTooltip);
    window.addEventListener('scroll', _hideMatrixTooltip, true);
  }

  function _subFilterCodes(codes, q) {
    if (!q) return codes;
    const ql = q.toLowerCase();
    return codes.filter(code => code.toLowerCase().includes(ql));
  }

  function renderAwsRefMatrix() {
    state.matrixShow  = $('#awsrefMatrixShow')?.value  || 'all';
    state.matrixFromQ = ($('#awsrefMatrixFrom')?.value || '').trim();
    state.matrixToQ   = ($('#awsrefMatrixTo')?.value   || '').trim();

    const status = $('#awsrefMatrixStatus');
    const thead  = $('#awsrefMatrixThead');
    const tbody  = $('#awsrefMatrixTBody');

    const m = state.matrix;
    if (!m || !m.data || !m.codes) {
      tbody.innerHTML = '<tr><td class="awsref-empty">' +
        escapeHtml(t('awsref_no_data') || 'No data') + '</td></tr>';
      thead.innerHTML = '';
      if (status) status.textContent = '';
      return;
    }

    const md = m.metadata || {};
    const codes  = m.codes || [];
    const types  = m.types || {};
    const names  = m.names || {};
    const regionCount = codes.filter(c => types[c] === 'region').length;
    const lzCount     = codes.filter(c => types[c] === 'local-zone').length;

    // Status line — show 67 codes (35 regions + 32 LZs) like the reference
    const substituted = md.data_substituted === true;
    if (status) {
      const cached = m.cached ? ' (cached)' : ' (fresh from cloudping.co)';
      status.textContent =
        `done · ${codes.length} codes (${regionCount} regions + ${lzCount} LZs)` +
        ` · ${md.percentile || 'p_50'} / ${md.timeframe || '1D'}` +
        `${cached} · fetched ${md.fetched_at || ''}`;
      status.classList.toggle('awsref-status-warn', substituted);
    }

    // Big honest banner when we're showing P50/1D data under a non-default
    // selection. The user is asking why values don't change — this is the
    // explicit answer that's hard to miss.
    const banner = $('#awsrefSubstitutionBanner');
    if (banner) {
      if (substituted) {
        const title = t('awsref_sub_banner_title') ||
          'Identical values across all selections — here is why';
        const upper = (s) => (s || '').replace(/p_/, 'P').toUpperCase();
        const selected = `${upper(md.percentile)} / ${md.timeframe}`;
        const actual   = `${upper(md.actual_percentile || 'p_50')} / ${md.actual_timeframe || '1D'}`;
        const body = (t('awsref_sub_banner_body') ||
          'cloudping.co\'s public homepage only exposes P50 / 1D. ' +
          'For other percentile or timeframe combinations, an API key is required. ' +
          'The numbers below are the substituted P50 / 1D dataset. ' +
          'To unlock real values, set the {env} environment variable to a benchsuite-compatible proxy URL and restart the server.')
          .replace('{env}', '<code>CLOUDPING_PROXY_URL</code>');
        $('#awsrefSubBannerTitle').textContent =
          `${title}  ·  ${(t('awsref_sub_banner_selected') || 'selected')}: ${selected}  ` +
          `·  ${(t('awsref_sub_banner_actual') || 'actual data')}: ${actual}`;
        $('#awsrefSubBannerBody').innerHTML = body;
        banner.style.display = '';
      } else {
        banner.style.display = 'none';
      }
    }

    // SHOW filter — restrict the code set to regions only / LZs only.
    let codeUniverse = codes;
    if (state.matrixShow === 'region') {
      codeUniverse = codes.filter(c => types[c] === 'region');
    } else if (state.matrixShow === 'local-zone') {
      codeUniverse = codes.filter(c => types[c] === 'local-zone');
    }

    const fromCodes = _subFilterCodes(codeUniverse, state.matrixFromQ);
    const toCodes   = _subFilterCodes(codeUniverse, state.matrixToQ);

    if (!fromCodes.length || !toCodes.length) {
      thead.innerHTML = '';
      tbody.innerHTML = '<tr><td class="awsref-empty">' +
        escapeHtml(t('awsref_no_results') || 'No rows match the filters') + '</td></tr>';
      return;
    }

    // Header — one column per TO code, marked with type for tinted background
    let head = '<tr><th class="awsref-corner">FROM \\ TO</th>';
    for (const c of toCodes) {
      const friendly = names[c] || '';
      const isLz = (types[c] === 'local-zone');
      const ttText = c + (friendly ? ' || ' + friendly : '') + (isLz ? ' || (Local Zone)' : '');
      const cls = isLz ? 'awsref-col-rot awsref-col-lz' : 'awsref-col-rot';
      head += '<th class="' + cls + '" data-tt="' + escapeHtml(ttText) + '">' +
              escapeHtml(c) + '</th>';
    }
    head += '</tr>';
    thead.innerHTML = head;

    // Body
    const dataMap = m.data;
    const body = fromCodes.map(from => {
      const rowMap = dataMap[from] || {};
      const friendly = names[from] || '';
      const isLz = (types[from] === 'local-zone');
      const rowClass = isLz ? 'awsref-row-head awsref-row-lz' : 'awsref-row-head';
      const rowTt = from + (friendly ? ' || ' + friendly : '') + (isLz ? ' || (Local Zone)' : '');
      const rowTitle =
        '<th class="' + rowClass + '" data-tt="' + escapeHtml(rowTt) + '">' +
          escapeHtml(from) +
          (friendly ? '<div class="awsref-row-sub">' + escapeHtml(friendly) + '</div>' : '') +
        '</th>';
      const cells = toCodes.map(to => {
        if (to === from) return '<td class="cell-self">—</td>';
        const ms = rowMap[to];
        const friendlyFrom = names[from] || '';
        const friendlyTo   = names[to]   || '';
        const pairLabel = (friendlyFrom && friendlyTo)
          ? friendlyFrom + ' → ' + friendlyTo : '';
        if (ms == null) {
          const tt = from + ' → ' + to + ': no data' + (pairLabel ? ' || ' + pairLabel : '');
          return '<td class="cell-na" data-tt="' + escapeHtml(tt) + '">·</td>';
        }
        const tt = from + ' → ' + to + ': ' + Math.round(ms) + ' ms' +
                   (pairLabel ? ' || ' + pairLabel : '');
        return '<td class="' + _cellClass(ms) + '" data-tt="' + escapeHtml(tt) + '">' +
               Math.round(ms) + '</td>';
      }).join('');
      return '<tr>' + rowTitle + cells + '</tr>';
    }).join('');
    tbody.innerHTML = body;

    // Wire up the custom horizontal tooltip (idempotent — only binds once).
    _attachMatrixTooltip();
  }
  window.renderAwsRefMatrix = renderAwsRefMatrix;

  // -------------------- Init --------------------
  document.addEventListener('DOMContentLoaded', () => {
    loadRegions();
  });
  // Re-translate dynamic content when language toggle fires
  document.addEventListener('langchange', () => {
    if (state.currentTab === 'services') renderAwsRefServices();
    if (state.currentTab === 'matrix')   renderAwsRefMatrix();
  });
})();
