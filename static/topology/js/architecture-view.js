/* ============================================================
   Topology — Architecture View controller.
   Self-contained IIFE. Doesn't touch the existing JointJS controller.

   Responsibilities:
     - Tab switching (Interactive ↔ Architecture View)
     - VPC dropdown population from /topology/api/architecture/list
     - Inline SVG fetch + display
     - .drawio download
     - "Open in diagrams.net" handoff (?title=...#R<base64>)
     - SVG download
     - PNG download (frontend canvas, no backend dep)
   ============================================================ */

(function () {
  'use strict';

  // Defensive lookup for i18n strings — bypass global t() since other libs
  // may shadow it (see /static/news/js/news.js for the same pattern).
  function currentLang() {
    try {
      const v = localStorage.getItem('finops_lang');
      if (v === 'tr' || v === 'en') return v;
    } catch (e) { /* fall through */ }
    return 'en';
  }
  function tr(key, fallback) {
    try {
      if (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS) {
        const lang = currentLang();
        const v = (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) ||
                  (TRANSLATIONS.en && TRANSLATIONS.en[key]);
        if (typeof v === 'string') return v;
      }
    } catch (e) { /* fall through */ }
    return fallback || key;
  }

  // --- DOM refs --------------------------------------------------------
  const $ = (sel) => document.querySelector(sel);
  function refs() {
    return {
      tabBar:        $('#topoTabBar'),
      interactive:   $('#topoInteractiveView'),
      architecture:  $('#topoArchitectureView'),
      vpcSelect:     $('#archVpcSelect'),
      svgCard:       $('#archSvgCard'),
      svgStatus:     $('#archSvgStatus'),
      svgStage:      $('#archSvgStage'),
      svgContainer:  $('#archSvgContainer'),
      btnDrawio:     $('#archDownloadDrawio'),
      btnOpenDrawio: $('#archOpenDrawio'),
      btnSvg:        $('#archDownloadSvg'),
      btnPng:        $('#archDownloadPng'),
      // Zoom panel
      mapControls:   $('#archMapControls'),
      btnFullscreen: $('#archFullscreenBtn'),
      btnZoomIn:     $('#archZoomInBtn'),
      btnZoomOut:    $('#archZoomOutBtn'),
      btnFit:        $('#archFitBtn'),
      btnReset:      $('#archResetBtn'),
      zoomSlider:    $('#archZoomSlider'),
      zoomReadout:   $('#archZoomReadout'),
      // Inventory
      invCard:       $('#archInventoryCard'),
      invHead:       $('#archInventoryHead'),
      invMeta:       $('#archInventoryMeta'),
      invBody:       $('#archInventoryBody'),
      invFilter:     $('#archInventoryFilter'),
      invExpand:     $('#archInventoryExpandAll'),
      invCollapse:   $('#archInventoryCollapseAll'),
    };
  }

  // --- State -----------------------------------------------------------
  const state = {
    profile:    '',           // last-used profile (set when scan loads)
    vpcs:       [],
    currentVpc: '',
    currentSvg: '',           // last fetched SVG string
    // Pan/zoom state (1.0 = 100%)
    pz: { scale: 1, tx: 0, ty: 0, baseW: 0, baseH: 0 },
    // Inventory state
    inventory: null,            // last fetched {groups, total} payload
    inventoryFilter: '',        // search box value
    inventoryOpen: new Set(),   // expanded type names
  };
  const ZOOM_MIN = 0.2;
  const ZOOM_MAX = 3.0;

  // --- Profile discovery ---------------------------------------------
  // The existing topology controller stores the loaded profile somewhere.
  // We can read it from the scan-history dropdown OR from a global the
  // controller may set. Cheapest path: hit /api/last-scanned-profile.
  async function discoverProfile() {
    try {
      const r = await fetch('/topology/api/last-scanned-profile');
      const d = await r.json();
      if (d && d.status === 'ok' && d.profile) return d.profile;
    } catch (e) { /* ignore */ }
    // Fallback — try to read from JointJS's hidden inputs.
    const histSelect = document.querySelector('[data-history-active]');
    if (histSelect && histSelect.dataset.historyActive) return histSelect.dataset.historyActive;
    return '';
  }

  // --- VPC list refresh ----------------------------------------------
  async function refreshVpcList() {
    const r = refs();
    if (!r.vpcSelect) return;
    state.profile = await discoverProfile();
    if (!state.profile) {
      r.vpcSelect.innerHTML = '<option value="">' +
        escapeHtmlSafe(tr('topology_arch_no_vpcs', 'No VPCs in scan')) + '</option>';
      setStatus(tr('topology_arch_no_vpcs', 'No VPCs in scan'));
      return;
    }
    try {
      const resp = await fetch('/topology/api/architecture/list?profile=' +
        encodeURIComponent(state.profile));
      const data = await resp.json();
      if (data.status !== 'ok' || !data.vpcs || !data.vpcs.length) {
        r.vpcSelect.innerHTML = '<option value="">' +
          escapeHtmlSafe(tr('topology_arch_no_vpcs', 'No VPCs in scan')) + '</option>';
        setStatus(tr('topology_arch_no_vpcs', 'No VPCs in scan'));
        state.vpcs = [];
        return;
      }
      state.vpcs = data.vpcs;
      const opts = ['<option value="">' +
        escapeHtmlSafe(tr('topology_arch_select_vpc', 'Select a VPC')) + '</option>'];
      for (const v of data.vpcs) {
        const label = `${v.region} · ${v.vpc_id}` +
          (v.cidr ? ` (${v.cidr})` : '') +
          ` · ${v.subnet_count} subnet, ${v.az_count} AZ`;
        opts.push(`<option value="${escapeHtmlSafe(v.vpc_id)}">${escapeHtmlSafe(label)}</option>`);
      }
      r.vpcSelect.innerHTML = opts.join('');

      // Auto-select first VPC and render.
      if (data.vpcs.length > 0) {
        r.vpcSelect.value = data.vpcs[0].vpc_id;
        await loadVpc(data.vpcs[0].vpc_id);
      }
    } catch (err) {
      setStatus(tr('topology_arch_error', 'Diagram generation failed') + ': ' + err.message,
                'arch-svg-error');
    }
  }

  function escapeHtmlSafe(s) {
    if (typeof escapeHtml === 'function') return escapeHtml(s);
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // --- Status / loading ----------------------------------------------
  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }
  function setStatus(msg, cls) {
    const r = refs();
    if (!r.svgCard || !r.svgStatus) return;
    r.svgCard.classList.add('is-empty');
    r.svgStatus.className = 'arch-svg-status' + (cls ? ' ' + cls : '');
    r.svgStatus.textContent = msg;
    if (r.svgContainer) r.svgContainer.innerHTML = '';
    enableExportButtons(false);
  }
  function setLoading() {
    const r = refs();
    if (!r.svgContainer) return;
    r.svgCard.classList.remove('is-empty');
    r.svgContainer.innerHTML =
      '<div class="arch-svg-loading">' +
      escapeHtmlSafe(tr('topology_arch_loading', 'Generating diagram...')) +
      '</div>';
    enableExportButtons(false);
  }
  function enableExportButtons(yes) {
    const r = refs();
    [r.btnDrawio, r.btnOpenDrawio, r.btnSvg, r.btnPng].forEach((b) => {
      if (b) b.disabled = !yes;
    });
  }

  // --- Pan / Zoom -----------------------------------------------------
  function applyTransform() {
    const r = refs();
    if (!r.svgContainer) return;
    r.svgContainer.style.transform =
      `translate(${state.pz.tx}px, ${state.pz.ty}px) scale(${state.pz.scale})`;
    if (r.zoomSlider)  r.zoomSlider.value   = String(Math.round(state.pz.scale * 100));
    if (r.zoomReadout) r.zoomReadout.textContent = Math.round(state.pz.scale * 100) + '%';
  }
  function clampScale(s) { return Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, s)); }
  function setScale(s, anchor) {
    const r = refs();
    if (!r.svgStage) { state.pz.scale = clampScale(s); applyTransform(); return; }
    const newScale = clampScale(s);
    if (anchor) {
      // Zoom around the (anchor.x, anchor.y) point in stage coords.
      const stageRect = r.svgStage.getBoundingClientRect();
      const ax = anchor.x - stageRect.left;
      const ay = anchor.y - stageRect.top;
      const k = newScale / state.pz.scale;
      state.pz.tx = ax - (ax - state.pz.tx) * k;
      state.pz.ty = ay - (ay - state.pz.ty) * k;
    }
    state.pz.scale = newScale;
    applyTransform();
  }
  function fitToView() {
    const r = refs();
    if (!r.svgStage) return;
    const svgEl = r.svgContainer && r.svgContainer.querySelector('svg');
    if (!svgEl) return;
    // Use the SVG's viewBox if available — otherwise its natural width/height.
    const vb = svgEl.viewBox && svgEl.viewBox.baseVal;
    const w = (vb && vb.width)  || svgEl.clientWidth  || svgEl.getBoundingClientRect().width  || 800;
    const h = (vb && vb.height) || svgEl.clientHeight || svgEl.getBoundingClientRect().height || 600;
    state.pz.baseW = w;
    state.pz.baseH = h;
    const sw = r.svgStage.clientWidth  - 24;
    const sh = r.svgStage.clientHeight - 24;
    const scale = Math.min(sw / w, sh / h, 1);
    state.pz.scale = clampScale(scale);
    state.pz.tx = (r.svgStage.clientWidth  - w * state.pz.scale) / 2;
    state.pz.ty = (r.svgStage.clientHeight - h * state.pz.scale) / 2;
    applyTransform();
  }
  function resetView() {
    state.pz.scale = 1; state.pz.tx = 0; state.pz.ty = 0;
    applyTransform();
  }

  function wirePanZoom() {
    const r = refs();
    if (!r.svgStage) return;

    // Drag-pan
    let dragging = false, startX = 0, startY = 0, startTX = 0, startTY = 0;
    r.svgStage.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      // Don't start a drag when interacting with the floating controls.
      if (e.target.closest('.arch-map-controls')) return;
      dragging = true;
      r.svgStage.classList.add('is-panning');
      startX = e.clientX; startY = e.clientY;
      startTX = state.pz.tx; startTY = state.pz.ty;
      e.preventDefault();
    });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      state.pz.tx = startTX + (e.clientX - startX);
      state.pz.ty = startTY + (e.clientY - startY);
      applyTransform();
    });
    window.addEventListener('mouseup', () => {
      if (!dragging) return;
      dragging = false;
      r.svgStage.classList.remove('is-panning');
    });

    // Wheel zoom (anchored on cursor)
    r.svgStage.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setScale(state.pz.scale * (1 + delta), { x: e.clientX, y: e.clientY });
    }, { passive: false });

    if (r.btnZoomIn)  r.btnZoomIn.addEventListener('click',  () => setScale(state.pz.scale * 1.2));
    if (r.btnZoomOut) r.btnZoomOut.addEventListener('click', () => setScale(state.pz.scale / 1.2));
    if (r.btnFit)     r.btnFit.addEventListener('click',     fitToView);
    if (r.btnReset)   r.btnReset.addEventListener('click',   resetView);
    if (r.zoomSlider) {
      r.zoomSlider.addEventListener('input', (e) => {
        setScale(parseInt(e.target.value, 10) / 100);
      });
    }
    if (r.btnFullscreen) {
      r.btnFullscreen.addEventListener('click', async () => {
        try {
          if (!document.fullscreenElement) {
            await r.svgCard.requestFullscreen();
          } else {
            await document.exitFullscreen();
          }
          // Re-fit after layout settles.
          setTimeout(fitToView, 200);
        } catch (err) { /* ignore */ }
      });
    }
    document.addEventListener('fullscreenchange', () => setTimeout(fitToView, 100));
    window.addEventListener('resize',             () => setTimeout(fitToView, 60));
  }

  // --- VPC load ------------------------------------------------------
  async function loadVpc(vpcId) {
    state.currentVpc = vpcId || '';
    if (!state.currentVpc || !state.profile) {
      setStatus(tr('topology_arch_select_vpc', 'Select a VPC'));
      return;
    }
    const r = refs();
    setLoading();
    try {
      const url = '/topology/api/architecture/svg?profile=' +
        encodeURIComponent(state.profile) +
        '&vpc_id=' + encodeURIComponent(state.currentVpc) +
        '&theme=' + encodeURIComponent(currentTheme());
      const resp = await fetch(url);
      if (!resp.ok) {
        const txt = await resp.text();
        setStatus('HTTP ' + resp.status + ': ' + txt.slice(0, 100),
                  'arch-svg-error');
        return;
      }
      const svg = await resp.text();
      state.currentSvg = svg;
      r.svgCard.classList.remove('is-empty');
      r.svgContainer.innerHTML = svg;
      enableExportButtons(true);
      // Fit to viewport on first paint of every new diagram.
      setTimeout(fitToView, 30);
      // Refresh the inventory table for this VPC.
      loadInventory();
    } catch (err) {
      setStatus(tr('topology_arch_error', 'Diagram generation failed') + ': ' + err.message,
                'arch-svg-error');
    }
  }

  // --- Inventory table ----------------------------------------------
  // ScanBox type → human label + small SVG icon path (vendored aws-icons).
  const ICON_BASE = '/static/topology/icons/aws-icons';
  const INV_ICONS = {
    vpc:              ICON_BASE + '/architecture-service/AmazonVirtualPrivateCloud.svg',
    subnet:           ICON_BASE + '/architecture-group/Privatesubnet.svg',
    ec2:              ICON_BASE + '/architecture-service/AmazonEC2.svg',
    rds:              ICON_BASE + '/architecture-service/AmazonRDS.svg',
    lambda:           ICON_BASE + '/architecture-service/AWSLambda.svg',
    ecs:              ICON_BASE + '/architecture-service/AmazonElasticContainerService.svg',
    eks:              ICON_BASE + '/architecture-service/AmazonElasticKubernetesService.svg',
    s3:               ICON_BASE + '/architecture-service/AmazonSimpleStorageService.svg',
    efs:              ICON_BASE + '/architecture-service/AmazonEFS.svg',
    igw:              ICON_BASE + '/resource/AmazonVPCInternetGateway.svg',
    nat:              ICON_BASE + '/resource/AmazonVPCNATGateway.svg',
    route_table:      ICON_BASE + '/resource/AmazonRoute53RouteTable.svg',
    vpc_endpoint:     ICON_BASE + '/resource/AmazonVPCEndpoints.svg',
    eip:              ICON_BASE + '/resource/AmazonEC2ElasticIPAddress.svg',
    nacl:             ICON_BASE + '/resource/AmazonVPCNetworkAccessControlList.svg',
    eni:              ICON_BASE + '/resource/AmazonVPCRouter.svg',
    security_group:   ICON_BASE + '/architecture-service/AmazonVirtualPrivateCloud.svg',
    transit_gateway:  ICON_BASE + '/architecture-service/AWSTransitGateway.svg',
    direct_connect:   ICON_BASE + '/architecture-service/AWSDirectConnect.svg',
    vpn:              ICON_BASE + '/architecture-service/AWSSitetoSiteVPN.svg',
    cloudfront:       ICON_BASE + '/architecture-service/AmazonCloudFront.svg',
    route53:          ICON_BASE + '/architecture-service/AmazonRoute53.svg',
    elb:              ICON_BASE + '/architecture-service/ElasticLoadBalancing.svg',
    apigateway:       ICON_BASE + '/architecture-service/AmazonAPIGateway.svg',
    network_firewall: ICON_BASE + '/architecture-service/AWSNetworkFirewall.svg',
    acm:              ICON_BASE + '/architecture-service/AWSCertificateManager.svg',
    cognito:          ICON_BASE + '/architecture-service/AmazonCognito.svg',
    dynamodb:         ICON_BASE + '/architecture-service/AmazonDynamoDB.svg',
    organization:     ICON_BASE + '/architecture-group/AWSAccount.svg',
  };
  const INV_TYPE_LABEL = {
    ec2: 'EC2 Instances', rds: 'RDS Databases', s3: 'S3 Buckets',
    eni: 'Network Interfaces', vpc: 'VPCs', subnet: 'Subnets',
    igw: 'Internet Gateways', nat: 'NAT Gateways', route_table: 'Route Tables',
    security_group: 'Security Groups', nacl: 'Network ACLs', eip: 'Elastic IPs',
    elb: 'Load Balancers', cloudfront: 'CloudFront', route53: 'Route 53',
    lambda: 'Lambda', ecs: 'ECS', eks: 'EKS', efs: 'EFS',
    transit_gateway: 'Transit Gateways', direct_connect: 'Direct Connect',
    vpn: 'VPN', vpc_endpoint: 'VPC Endpoints', apigateway: 'API Gateway',
    network_firewall: 'Network Firewalls', acm: 'Certificates',
    cognito: 'Cognito', dynamodb: 'DynamoDB', organization: 'Organization',
  };

  async function loadInventory() {
    const r = refs();
    if (!r.invBody) return;
    if (!state.profile || !state.currentVpc) {
      r.invBody.innerHTML = '<div class="arch-inv-empty">' +
        escapeHtmlSafe(tr('topology_arch_inventory_empty', 'Pick a VPC to populate the inventory.')) +
        '</div>';
      if (r.invMeta) r.invMeta.textContent = '';
      return;
    }
    try {
      const url = '/topology/api/architecture/inventory?profile=' +
        encodeURIComponent(state.profile) +
        '&vpc_id=' + encodeURIComponent(state.currentVpc);
      const resp = await fetch(url);
      const data = await resp.json();
      if (data.status !== 'ok') {
        r.invBody.innerHTML = '<div class="arch-inv-empty">' +
          escapeHtmlSafe(data.error || 'Inventory unavailable') + '</div>';
        return;
      }
      state.inventory = data;
      // All sub-categories closed by default — user expands what they need.
      renderInventory();
    } catch (e) {
      r.invBody.innerHTML = '<div class="arch-inv-empty">' +
        escapeHtmlSafe('Failed: ' + e.message) + '</div>';
    }
  }

  function inventoryColumnsFor(type) {
    // Pick the columns that matter most per resource type — keeps the table
    // narrow and informative instead of dumping every field.
    const common = ['id', 'name'];
    const map = {
      ec2:            [...common, 'instance_type', 'state', 'private_ip', 'public_ip', 'az', 'subnet_id'],
      rds:            [...common, 'engine', 'instance_type', 'state', 'az'],
      lambda:         [...common, 'engine', 'state'],
      eni:            [...common, 'description', 'state', 'az', 'subnet_id', 'private_ip', 'public_ip'],
      nat:            [...common, 'state', 'public_ip', 'az', 'subnet_id'],
      igw:            [...common, 'state'],
      subnet:         [...common, 'cidr', 'az', 'state'],
      vpc:            [...common, 'cidr', 'state'],
      route_table:    [...common, 'state'],
      security_group: [...common, 'description'],
      nacl:           [...common, 'state'],
      eip:            [...common, 'public_ip', 'private_ip', 'state'],
      elb:            [...common, 'instance_type', 'state', 'description'],
      cloudfront:     [...common, 'state', 'description'],
      route53:        [...common, 'state'],
      acm:            [...common, 'state'],
      s3:             [...common, 'region'],
      vpc_endpoint:   [...common, 'description', 'state'],
      transit_gateway:[...common, 'state'],
      direct_connect: [...common, 'state'],
      vpn:            [...common, 'state'],
      organization:   [...common, 'state'],
    };
    return map[type] || [...common, 'state'];
  }

  function renderInventory() {
    const r = refs();
    if (!r.invBody || !state.inventory) return;
    const groups = state.inventory.groups || [];
    const filterText = (state.inventoryFilter || '').toLowerCase().trim();

    // Apply filter and remove empty groups.
    const visibleGroups = groups.map(g => {
      if (!filterText) return g;
      const items = g.items.filter(it => {
        return (it.id || '').toLowerCase().includes(filterText) ||
               (it.name || '').toLowerCase().includes(filterText) ||
               (it.description || '').toLowerCase().includes(filterText) ||
               (it.private_ip || '').includes(filterText) ||
               (it.public_ip || '').includes(filterText);
      });
      return { ...g, items, count: items.length };
    }).filter(g => g.count > 0);

    if (r.invMeta) {
      r.invMeta.textContent =
        `${state.inventory.total} resources • ${visibleGroups.length} types`;
    }

    if (!visibleGroups.length) {
      r.invBody.innerHTML = '<div class="arch-inv-empty">' +
        escapeHtmlSafe(tr('topology_arch_inventory_empty', 'No resources match the filter.')) +
        '</div>';
      return;
    }

    const buf = [];
    for (const g of visibleGroups) {
      const isOpen = state.inventoryOpen.has(g.type);
      const icon = INV_ICONS[g.type] || (ICON_BASE + '/architecture-group/AWSCloud.svg');
      const label = INV_TYPE_LABEL[g.type] || g.type;
      const cols = inventoryColumnsFor(g.type);

      const head =
        `<div class="arch-inv-group-head" data-type="${escapeHtmlSafe(g.type)}">` +
          `<svg class="chev" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>` +
          `<span class="arch-inv-group-icon"><img src="${escapeHtmlSafe(icon)}" alt=""></span>` +
          `<span class="arch-inv-type">${escapeHtmlSafe(label)}</span>` +
          `<span class="arch-inv-count">${g.count}</span>` +
        `</div>`;

      const headers = cols.map(c =>
        `<th>${escapeHtmlSafe(c.replace(/_/g, ' '))}</th>`).join('');
      const rows = g.items.map(it => {
        const tds = cols.map(c => {
          let v = it[c] || '';
          if (Array.isArray(v)) v = v.join(', ');
          if (typeof v === 'object') v = JSON.stringify(v);
          v = String(v);
          let cls = '';
          if (c === 'state' && v) {
            cls = ' class="arch-inv-state-' + escapeHtmlSafe(v.toLowerCase().replace(/\s+/g,'-')) + '"';
          }
          return `<td${cls} title="${escapeHtmlSafe(v)}">${escapeHtmlSafe(v) || '<span style="color:var(--text-muted)">—</span>'}</td>`;
        }).join('');
        return `<tr>${tds}</tr>`;
      }).join('');

      const body =
        `<div class="arch-inv-group-body">` +
          `<table class="arch-inv-table">` +
            `<thead><tr>${headers}</tr></thead>` +
            `<tbody>${rows}</tbody>` +
          `</table>` +
        `</div>`;

      buf.push(`<div class="arch-inv-group${isOpen ? ' is-open' : ''}">${head}${body}</div>`);
    }
    r.invBody.innerHTML = buf.join('');
  }

  function wireInventory() {
    const r = refs();
    // Outer Inventory accordion — closed by default, toggles on head click.
    // Toolbar (search/expand-all/collapse-all) lives inside the head; its
    // wrapping div in the template stops propagation so those controls
    // remain operable without snapping the card shut.
    if (r.invHead && r.invCard) {
      const toggleCard = () => r.invCard.classList.toggle('is-open');
      r.invHead.addEventListener('click', toggleCard);
      r.invHead.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleCard(); }
      });
    }
    if (r.invBody) {
      r.invBody.addEventListener('click', (e) => {
        const head = e.target.closest('.arch-inv-group-head');
        if (!head) return;
        const t = head.dataset.type;
        if (state.inventoryOpen.has(t)) state.inventoryOpen.delete(t);
        else                            state.inventoryOpen.add(t);
        head.parentElement.classList.toggle('is-open');
      });
    }
    if (r.invFilter) {
      let timer;
      r.invFilter.addEventListener('input', (e) => {
        clearTimeout(timer);
        const v = e.target.value;
        timer = setTimeout(() => {
          state.inventoryFilter = v;
          renderInventory();
        }, 150);
      });
    }
    if (r.invExpand) {
      r.invExpand.addEventListener('click', () => {
        if (!state.inventory) return;
        for (const g of state.inventory.groups) state.inventoryOpen.add(g.type);
        // Auto-open the outer accordion so the expansion is actually visible.
        if (r.invCard && !r.invCard.classList.contains('is-open')) {
          r.invCard.classList.add('is-open');
        }
        renderInventory();
      });
    }
    if (r.invCollapse) {
      r.invCollapse.addEventListener('click', () => {
        state.inventoryOpen.clear();
        renderInventory();
      });
    }
  }

  // --- Downloads -----------------------------------------------------
  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  async function fetchDrawio() {
    if (!state.profile || !state.currentVpc) return null;
    const url = '/topology/api/architecture/drawio?profile=' +
      encodeURIComponent(state.profile) +
      '&vpc_id=' + encodeURIComponent(state.currentVpc);
    const resp = await fetch(url);
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error('HTTP ' + resp.status + ': ' + txt.slice(0, 100));
    }
    return await resp.text();
  }

  async function downloadDrawio() {
    try {
      const xml = await fetchDrawio();
      if (!xml) return;
      triggerDownload(
        new Blob([xml], { type: 'application/xml' }),
        `topology-${state.currentVpc}.drawio`,
      );
    } catch (err) {
      alert(err.message || String(err));
    }
  }

  async function openInDrawio() {
    try {
      const xml = await fetchDrawio();
      if (!xml) return;
      // drawio's documented #R fragment loader: percent-encoded then base64.
      // Reference: https://www.drawio.com/blog/embedding-walkthrough
      const encoded = btoa(unescape(encodeURIComponent(xml)));
      const url = 'https://app.diagrams.net/?title=topology-' +
        encodeURIComponent(state.currentVpc) + '.drawio#R' + encoded;
      window.open(url, '_blank', 'noopener');
    } catch (err) {
      alert(err.message || String(err));
    }
  }

  function downloadSvg() {
    if (!state.currentSvg) return;
    triggerDownload(
      new Blob([state.currentSvg], { type: 'image/svg+xml' }),
      `topology-${state.currentVpc}.svg`,
    );
  }

  function downloadPng() {
    if (!state.currentSvg) return;
    // Render SVG → off-screen canvas at 2x resolution → PNG blob.
    const r = refs();
    const svgEl = r.svgContainer.querySelector('svg');
    if (!svgEl) return;

    const vbW = svgEl.viewBox && svgEl.viewBox.baseVal && svgEl.viewBox.baseVal.width
      ? svgEl.viewBox.baseVal.width  : svgEl.clientWidth  || 800;
    const vbH = svgEl.viewBox && svgEl.viewBox.baseVal && svgEl.viewBox.baseVal.height
      ? svgEl.viewBox.baseVal.height : svgEl.clientHeight || 600;
    const scale = 2;

    const blob = new Blob([state.currentSvg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width  = Math.round(vbW * scale);
      canvas.height = Math.round(vbH * scale);
      const ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);
      canvas.toBlob((pngBlob) => {
        if (!pngBlob) return;
        triggerDownload(pngBlob, `topology-${state.currentVpc}.png`);
      }, 'image/png');
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      alert(tr('topology_arch_error', 'Diagram generation failed'));
    };
    img.src = url;
  }

  // --- Tab switching --------------------------------------------------
  function activateTab(name) {
    const r = refs();
    if (!r.tabBar) return;
    r.tabBar.querySelectorAll('.topo-tab').forEach((b) => {
      const on = b.dataset.tab === name;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-selected', String(on));
    });
    if (r.interactive)  r.interactive.style.display  = (name === 'interactive')  ? '' : 'none';
    if (r.architecture) r.architecture.style.display = (name === 'architecture') ? '' : 'none';
    if (name === 'architecture') {
      // Lazy load — only fetch VPC list the first time the tab is shown.
      if (!state._loaded) {
        state._loaded = true;
        refreshVpcList();
      }
    }
  }

  // --- Wire up -------------------------------------------------------
  function wire() {
    const r = refs();
    if (r.tabBar) {
      r.tabBar.addEventListener('click', (e) => {
        const btn = e.target.closest('.topo-tab');
        if (!btn) return;
        activateTab(btn.dataset.tab);
      });
    }
    if (r.vpcSelect) {
      r.vpcSelect.addEventListener('change', (e) => loadVpc(e.target.value));
    }
    if (r.btnDrawio)     r.btnDrawio.addEventListener('click', downloadDrawio);
    if (r.btnOpenDrawio) r.btnOpenDrawio.addEventListener('click', openInDrawio);
    if (r.btnSvg)        r.btnSvg.addEventListener('click', downloadSvg);
    if (r.btnPng)        r.btnPng.addEventListener('click', downloadPng);

    // Pan / Zoom — wire after the SVG container is in the DOM.
    wirePanZoom();
    // Inventory — collapsible per-type groups + filter.
    wireInventory();

    // Re-fetch SVG on theme change so colors adapt.
    document.addEventListener('themechange', () => {
      if (state.currentVpc && state._loaded) loadVpc(state.currentVpc);
    });
    // Re-render labels on lang change (status messages, "select a vpc", etc).
    document.addEventListener('langchange', () => {
      if (!state.currentVpc) {
        const lbl = tr('topology_arch_select_vpc', 'Select a VPC');
        setStatus(lbl);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }
})();
