/* ═══════════════════════════════════════════════════════════
   Health Module — Dashboard JS
   Self-contained, no shared state with other modules.
   ═══════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ── State ──
  let _pollInterval = null;
  let _historyInterval = null;
  let _latencyBarChart = null;
  let _latencyTrendChart = null;
  let _cfTrendChart = null;
  let _googleTrendChart = null;
  let _cfGaugeChart = null;
  let _googleGaugeChart = null;
  let _currentLatencyView = 'table';
  let _currentOutageView = 'map';
  // Sliding window for DNS availability (last 100 measurements, not cumulative)
  const _DNS_WINDOW = 100;
  let _cfWindow = [];       // [{ok: bool}]
  let _googleWindow = [];

  // ── Init ──
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    setupViewToggles();
    fetchStatus();
    // Poll every 30s (matches backend update frequency)
    _pollInterval = setInterval(fetchStatus, 30000);
    _historyInterval = setInterval(fetchHistory, 30000);
    setTimeout(fetchHistory, 5000);

    // React to theme/language changes
    document.addEventListener('themechange', () => {
      destroyAllCharts();
      fetchStatus();
      fetchHistory();
    });
    document.addEventListener('langchange', () => {
      fetchStatus();
    });

    // Stop polling when tab is hidden to save resources
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        clearInterval(_pollInterval);
        clearInterval(_historyInterval);
        _pollInterval = null;
        _historyInterval = null;
      } else {
        if (!_pollInterval) {
          fetchStatus();
          _pollInterval = setInterval(fetchStatus, 30000);
          _historyInterval = setInterval(fetchHistory, 30000);
        }
      }
    });
  }

  // ── View Toggle Setup ──
  function setupViewToggles() {
    // Latency view toggle
    const latToggle = document.getElementById('latencyViewToggle');
    if (latToggle) {
      latToggle.addEventListener('click', (e) => {
        const btn = e.target.closest('.view-btn');
        if (!btn) return;
        const view = btn.dataset.view;
        _currentLatencyView = view;
        latToggle.querySelectorAll('.view-btn').forEach(b => b.classList.toggle('active', b === btn));
        document.getElementById('latencyTableView').classList.toggle('active', view === 'table');
        document.getElementById('latencyChartView').classList.toggle('active', view === 'chart');
        if (view === 'chart' && !_latencyBarChart) fetchStatus();
      });
    }

    // Outage view toggle
    const outToggle = document.getElementById('outageViewToggle');
    if (outToggle) {
      outToggle.addEventListener('click', (e) => {
        const btn = e.target.closest('.view-btn');
        if (!btn) return;
        const view = btn.dataset.view;
        _currentOutageView = view;
        outToggle.querySelectorAll('.view-btn').forEach(b => b.classList.toggle('active', b === btn));
        document.getElementById('outageFeedView').classList.toggle('active', view === 'feed');
        document.getElementById('outageMapView').classList.toggle('active', view === 'map');
      });
    }
  }

  // ── Fetch All Status ──
  async function fetchStatus() {
    try {
      const resp = await fetch('/health/api/status');
      const data = await resp.json();
      renderStatusBar(data);
      renderLatencyTable(data.regions || []);
      if (_currentLatencyView === 'chart') renderLatencyBarChart(data.regions || []);
      renderOutages(data.aws_outages || [], data.regions || []);
      renderDNS(data.dns || {});
      renderCloudflareStatus(data.cloudflare || {});
    } catch (e) {
      console.error('Health fetch error:', e);
    }
  }

  // ── Fetch History ──
  async function fetchHistory() {
    try {
      const resp = await fetch('/health/api/latency-history');
      const data = await resp.json();
      renderLatencyTrend(data.regions || {});
      renderDNSTrend(data.dns || {});
    } catch (e) {
      console.error('Health history fetch error:', e);
    }
  }

  // ── Chart Colors Helper ──
  function getChartColors() {
    const theme = localStorage.getItem('finops_theme') || 'dark';
    return theme === 'light'
      ? { text: '#334155', grid: '#d0d9e8', bg: '#ffffff' }
      : { text: '#7e96b4', grid: '#1d2636', bg: '#141a24' };
  }

  // ── Destroy All Charts ──
  function destroyAllCharts() {
    [_latencyBarChart, _latencyTrendChart, _cfTrendChart, _googleTrendChart, _cfGaugeChart, _googleGaugeChart].forEach(c => { if (c) c.destroy(); });
    _latencyBarChart = _latencyTrendChart = _cfTrendChart = _googleTrendChart = _cfGaugeChart = _googleGaugeChart = null;
  }

  // ═══════════════════════════════════════════════════════════
  // STATUS BAR
  // ═══════════════════════════════════════════════════════════
  function renderStatusBar(data) {
    const dot = document.getElementById('monitorDot');
    const label = document.getElementById('monitorLabel');
    const updateEl = document.getElementById('lastUpdate');
    const badge = document.getElementById('bestRegionBadge');
    const bestName = document.getElementById('bestRegionName');
    const bestLat = document.getElementById('bestRegionLatency');

    if (data.monitoring) {
      dot.className = 'status-dot ok';
      label.textContent = t('health_monitoring_active');
    } else {
      dot.className = 'status-dot';
      label.textContent = t('health_initializing');
    }

    if (data.timestamp) {
      const d = new Date(data.timestamp * 1000);
      updateEl.textContent = d.toLocaleTimeString();
    }

    if (data.best_region) {
      badge.style.display = 'flex';
      bestName.textContent = `${data.best_region.region} (${data.best_region.name})`;
      bestLat.textContent = `${data.best_region.latency_ms} ms`;
    }
  }

  // ═══════════════════════════════════════════════════════════
  // LATENCY TABLE
  // ═══════════════════════════════════════════════════════════
  function renderLatencyTable(regions) {
    const tbody = document.getElementById('latencyTableBody');
    const countEl = document.getElementById('regionCount');
    if (!tbody) return;
    if (!regions.length) return;

    countEl.textContent = regions.length;

    // Find max latency for bar scaling
    const maxLat = Math.max(...regions.filter(r => r.latency_ms !== null).map(r => r.latency_ms), 1);

    tbody.innerHTML = regions.map((r, i) => {
      const lat = r.latency_ms;
      const latStr = lat !== null ? `${lat} ms` : '—';
      const latClass = lat === null ? '' : lat < 50 ? 'latency-excellent' : lat < 100 ? 'latency-good' : lat < 200 ? 'latency-fair' : 'latency-poor';
      const barColor = lat === null ? 'var(--text-muted)' : lat < 50 ? 'var(--green)' : lat < 100 ? 'var(--teal)' : lat < 200 ? 'var(--yellow)' : 'var(--red)';
      const barWidth = lat !== null ? Math.max((lat / maxLat) * 100, 2) : 0;
      const statusClass = r.status === 'ok' ? 'ok' : 'timeout';
      const rankClass = i < 3 ? 'top3' : '';

      return `<tr>
        <td class="rank-cell ${rankClass}">${i + 1}</td>
        <td class="region-code">${escHtml(r.region)}</td>
        <td class="region-name">${escHtml(r.name)}</td>
        <td class="latency-val ${latClass}">${latStr}</td>
        <td><span class="status-badge ${statusClass}">${r.status === 'ok' ? t('health_status_ok') : t('health_status_timeout')}</span></td>
        <td class="latency-bar-cell"><div class="latency-bar-bg"><div class="latency-bar-fill" style="width:${barWidth}%;background:${barColor}"></div></div></td>
      </tr>`;
    }).join('');
  }

  // ═══════════════════════════════════════════════════════════
  // LATENCY BAR CHART
  // ═══════════════════════════════════════════════════════════
  function renderLatencyBarChart(regions) {
    const ctx = document.getElementById('latencyBarChart');
    if (!ctx) return;
    const colors = getChartColors();

    const labels = regions.map(r => r.region);
    const values = regions.map(r => r.latency_ms || 0);
    const barColors = regions.map(r => {
      const lat = r.latency_ms;
      if (lat === null) return 'rgba(128,128,128,0.3)';
      if (lat < 50) return 'rgba(0,208,132,0.7)';
      if (lat < 100) return 'rgba(45,212,191,0.7)';
      if (lat < 200) return 'rgba(255,209,102,0.7)';
      return 'rgba(255,77,106,0.7)';
    });

    if (_latencyBarChart) _latencyBarChart.destroy();
    _latencyBarChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Latency (ms)',
          data: values,
          backgroundColor: barColors,
          borderRadius: 4,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.parsed.x} ms`
            }
          }
        },
        scales: {
          x: {
            grid: { color: colors.grid },
            ticks: { color: colors.text, font: { size: 11 } },
            title: { display: true, text: 'ms', color: colors.text }
          },
          y: {
            grid: { display: false },
            ticks: { color: colors.text, font: { family: "'JetBrains Mono'", size: 10 } }
          }
        }
      }
    });
  }

  // ═══════════════════════════════════════════════════════════
  // LATENCY TREND CHART
  // ═══════════════════════════════════════════════════════════
  function renderLatencyTrend(historyData) {
    const ctx = document.getElementById('latencyTrendChart');
    if (!ctx) return;
    const colors = getChartColors();

    // Get top 5 regions by latest latency
    const regionCodes = Object.keys(historyData);
    if (!regionCodes.length) return;

    // Get latest value for each region
    const latest = regionCodes.map(code => {
      const pts = historyData[code];
      const last = pts.length ? pts[pts.length - 1] : [0, null];
      return { code, latency: last[1] };
    }).filter(r => r.latency !== null).sort((a, b) => a.latency - b.latency).slice(0, 5);

    const lineColors = ['#ff9900', '#00d084', '#4da6ff', '#a78bfa', '#ff4d6a'];

    const datasets = latest.map((r, i) => {
      const pts = historyData[r.code] || [];
      return {
        label: r.code,
        data: pts.map(p => ({ x: p[0] * 1000, y: p[1] })),
        borderColor: lineColors[i],
        backgroundColor: lineColors[i] + '20',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.3,
        fill: false,
      };
    });

    if (_latencyTrendChart) _latencyTrendChart.destroy();
    _latencyTrendChart = new Chart(ctx, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: colors.text, font: { size: 10 }, boxWidth: 12, padding: 8 }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} ms`
            }
          }
        },
        scales: {
          x: {
            type: 'time',
            time: { unit: 'minute', displayFormats: { minute: 'HH:mm' } },
            grid: { color: colors.grid },
            ticks: { color: colors.text, font: { size: 10 }, maxTicksLimit: 10 },
          },
          y: {
            grid: { color: colors.grid },
            ticks: { color: colors.text, font: { size: 10 } },
            title: { display: true, text: 'ms', color: colors.text, font: { size: 10 } }
          }
        }
      }
    });
  }

  // ═══════════════════════════════════════════════════════════
  // OUTAGE FEED / MAP
  // ═══════════════════════════════════════════════════════════
  function renderOutages(outages, regions) {
    renderOutageFeed(outages);
    renderOutageMap(outages, regions);
  }

  function renderOutageFeed(outages) {
    const container = document.getElementById('outageList');
    const countEl = document.getElementById('outageCount');
    if (!container) return;

    const ongoingCount = outages.filter(o => o.status === 'ongoing').length;
    countEl.textContent = ongoingCount;

    if (!outages.length) {
      container.innerHTML = `<div class="outage-all-clear">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <div style="margin-top:8px">${t('health_all_clear')}</div>
      </div>`;
      return;
    }

    container.innerHTML = outages.map(o => {
      const regionTag = o.region ? `<span class="outage-region-tag">${escHtml(o.region)}</span>` : '';
      return `<div class="outage-item">
        <div class="outage-dot ${o.status}"></div>
        <div class="outage-body">
          <div class="outage-service">${escHtml(o.service)}</div>
          <div class="outage-summary">${escHtml(o.summary)}</div>
          <div class="outage-meta">
            ${regionTag}
            <span>${escHtml(o.date)}</span>
            <span style="text-transform:capitalize">${escHtml(o.status)}</span>
          </div>
        </div>
      </div>`;
    }).join('');
  }

  function renderOutageMap(outages, regions) {
    const grid = document.getElementById('regionMapGrid');
    if (!grid) return;

    // Build a set of regions with ongoing issues
    const issueRegions = new Set(outages.filter(o => o.status === 'ongoing').map(o => o.region).filter(Boolean));

    // Build region data map from latency data
    const regionMap = {};
    regions.forEach(r => { regionMap[r.region] = r; });

    // All AWS regions
    const allRegions = [
      'us-east-1','us-east-2','us-west-1','us-west-2',
      'eu-west-1','eu-west-2','eu-west-3','eu-central-1','eu-central-2','eu-north-1','eu-south-1','eu-south-2',
      'ap-northeast-1','ap-northeast-2','ap-northeast-3','ap-southeast-1','ap-southeast-2','ap-southeast-3',
      'ap-south-1','ap-south-2','ap-east-1',
      'sa-east-1','ca-central-1',
      'me-south-1','me-central-1','af-south-1','il-central-1'
    ];

    grid.innerHTML = allRegions.map(code => {
      const r = regionMap[code];
      const hasIssue = issueRegions.has(code);
      const lat = r ? r.latency_ms : null;
      const latStr = lat !== null ? `${lat} ms` : '—';
      const latClass = lat === null ? '' : lat < 50 ? 'latency-excellent' : lat < 100 ? 'latency-good' : lat < 200 ? 'latency-fair' : 'latency-poor';
      const name = r ? r.name : code;
      const statusIcon = hasIssue
        ? `<div class="rm-status" style="color:var(--red)">${t('health_issue_detected')}</div>`
        : `<div class="rm-status" style="color:var(--green)">${t('health_status_ok')}</div>`;

      return `<div class="region-map-card${hasIssue ? ' has-issue' : ''}">
        <div class="rm-code">${escHtml(code)}</div>
        <div class="rm-name">${escHtml(name)}</div>
        <div class="rm-latency ${latClass}">${latStr}</div>
        ${statusIcon}
      </div>`;
    }).join('');
  }

  // ═══════════════════════════════════════════════════════════
  // DNS STATUS
  // ═══════════════════════════════════════════════════════════
  function renderDNS(dns) {
    // Cloudflare resolvers
    renderResolver('cfResolver1', dns.cloudflare_primary, 'cloudflare');
    renderResolver('cfResolver2', dns.cloudflare_secondary, 'cloudflare');
    // Google resolvers
    renderResolver('googleResolver1', dns.google_primary, 'google');
    renderResolver('googleResolver2', dns.google_secondary, 'google');

    // Update availability sliding window (last N measurements, not cumulative)
    if (dns.cloudflare_primary) {
      _cfWindow.push({ ok: dns.cloudflare_primary.status === 'ok' });
      if (_cfWindow.length > _DNS_WINDOW) _cfWindow.shift();
    }
    if (dns.cloudflare_secondary) {
      _cfWindow.push({ ok: dns.cloudflare_secondary.status === 'ok' });
      if (_cfWindow.length > _DNS_WINDOW) _cfWindow.shift();
    }
    if (dns.google_primary) {
      _googleWindow.push({ ok: dns.google_primary.status === 'ok' });
      if (_googleWindow.length > _DNS_WINDOW) _googleWindow.shift();
    }
    if (dns.google_secondary) {
      _googleWindow.push({ ok: dns.google_secondary.status === 'ok' });
      if (_googleWindow.length > _DNS_WINDOW) _googleWindow.shift();
    }

    // Provider dots
    updateProviderDot('googleDot', 'googleStatusText', dns.google_primary, dns.google_secondary, 'Google DNS');
    renderGauges();
  }

  function renderResolver(elementId, data, provider) {
    const el = document.getElementById(elementId);
    if (!el || !data) return;
    const latencyEl = el.querySelector('.resolver-latency');
    const dotEl = el.querySelector('.resolver-dot');
    if (latencyEl) {
      const lat = data.latency_ms;
      latencyEl.textContent = lat !== null ? `${lat} ms` : '—';
      latencyEl.className = 'resolver-latency ' + (lat === null ? '' : lat < 20 ? 'latency-excellent' : lat < 50 ? 'latency-good' : 'latency-fair');
    }
    if (dotEl) {
      dotEl.className = 'resolver-dot ' + (data.status === 'ok' ? 'ok' : 'down');
    }
  }

  function updateProviderDot(dotId, textId, primary, secondary, name) {
    const dot = document.getElementById(dotId);
    const text = document.getElementById(textId);
    if (!dot || !primary) return;
    const allOk = (primary?.status === 'ok') && (secondary?.status === 'ok');
    const someOk = (primary?.status === 'ok') || (secondary?.status === 'ok');
    dot.className = 'provider-dot ' + (allOk ? 'ok' : someOk ? 'degraded' : 'down');
    if (text) {
      text.textContent = allOk ? t('health_all_operational') : someOk ? t('health_degraded') : t('health_down');
    }
  }

  // ═══════════════════════════════════════════════════════════
  // CLOUDFLARE STATUS
  // ═══════════════════════════════════════════════════════════
  function renderCloudflareStatus(cf) {
    const cfDot = document.getElementById('cfDot');
    const cfText = document.getElementById('cfStatusText');

    if (cf.indicator) {
      const map = { none: 'ok', minor: 'degraded', major: 'down', critical: 'down' };
      cfDot.className = 'provider-dot ' + (map[cf.indicator] || '');
      cfText.textContent = cf.description || cf.indicator;
    }

    // Components
    const compEl = document.getElementById('cfComponents');
    if (compEl && cf.components && cf.components.length) {
      compEl.innerHTML = cf.components.slice(0, 12).map(c => {
        const cls = (c.status || '').replace(/ /g, '_');
        return `<span class="cf-comp-badge ${cls}">${escHtml(c.name)}</span>`;
      }).join('');
    }

    // Incidents
    const incEl = document.getElementById('cfIncidents');
    if (incEl && cf.incidents && cf.incidents.length) {
      incEl.innerHTML = cf.incidents.slice(0, 5).map(inc => {
        const dotClass = (inc.status || 'resolved').toLowerCase();
        return `<div class="cf-incident-item">
          <span class="cf-inc-dot ${dotClass}"></span>
          <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(inc.name)}</span>
          <span style="color:var(--text-muted);text-transform:capitalize">${escHtml(inc.status)}</span>
        </div>`;
      }).join('');
    } else if (incEl) {
      incEl.innerHTML = `<div style="font-size:11px;color:var(--text-muted);padding:6px 0">${t('health_no_incidents')}</div>`;
    }
  }

  // ═══════════════════════════════════════════════════════════
  // DNS TREND CHARTS
  // ═══════════════════════════════════════════════════════════
  function renderDNSTrend(dnsHistory) {
    const colors = getChartColors();

    // Cloudflare trend
    const cfCtx = document.getElementById('cfTrendChart');
    if (cfCtx) {
      const cf1 = (dnsHistory.cloudflare_primary || []).map(p => ({ x: p[0] * 1000, y: p[1] }));
      const cf2 = (dnsHistory.cloudflare_secondary || []).map(p => ({ x: p[0] * 1000, y: p[1] }));

      if (_cfTrendChart) _cfTrendChart.destroy();
      _cfTrendChart = new Chart(cfCtx, {
        type: 'line',
        data: {
          datasets: [
            { label: '1.1.1.1', data: cf1, borderColor: '#f58136', borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: false },
            { label: '1.0.0.1', data: cf2, borderColor: '#f5813680', borderWidth: 1, pointRadius: 0, tension: 0.3, fill: false },
          ]
        },
        options: trendChartOptions(colors)
      });
    }

    // Google trend
    const gCtx = document.getElementById('googleTrendChart');
    if (gCtx) {
      const g1 = (dnsHistory.google_primary || []).map(p => ({ x: p[0] * 1000, y: p[1] }));
      const g2 = (dnsHistory.google_secondary || []).map(p => ({ x: p[0] * 1000, y: p[1] }));

      if (_googleTrendChart) _googleTrendChart.destroy();
      _googleTrendChart = new Chart(gCtx, {
        type: 'line',
        data: {
          datasets: [
            { label: '8.8.8.8', data: g1, borderColor: '#4285f4', borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: false },
            { label: '8.8.4.4', data: g2, borderColor: '#4285f480', borderWidth: 1, pointRadius: 0, tension: 0.3, fill: false },
          ]
        },
        options: trendChartOptions(colors)
      });
    }
  }

  function trendChartOptions(colors) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'top', labels: { color: colors.text, font: { size: 9 }, boxWidth: 8, padding: 6 } },
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} ms` } }
      },
      scales: {
        x: {
          type: 'time',
          time: { unit: 'minute', displayFormats: { minute: 'HH:mm' } },
          grid: { color: colors.grid },
          ticks: { color: colors.text, font: { size: 9 }, maxTicksLimit: 6 }
        },
        y: {
          grid: { color: colors.grid },
          ticks: { color: colors.text, font: { size: 9 } },
          beginAtZero: true
        }
      }
    };
  }

  // ═══════════════════════════════════════════════════════════
  // GAUGE CHARTS
  // ═══════════════════════════════════════════════════════════
  function renderGauges() {
    const colors = getChartColors();

    const cfOk = _cfWindow.filter(m => m.ok).length;
    const cfAvail = _cfWindow.length > 0 ? Math.round((cfOk / _cfWindow.length) * 100) : 100;
    const gOk = _googleWindow.filter(m => m.ok).length;
    const gAvail = _googleWindow.length > 0 ? Math.round((gOk / _googleWindow.length) * 100) : 100;

    renderGauge('cfGaugeChart', cfAvail, '#f58136', colors);
    renderGauge('googleGaugeChart', gAvail, '#4285f4', colors);
  }

  function renderGauge(canvasId, value, color, colors) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const chartRef = canvasId === 'cfGaugeChart' ? '_cfGaugeChart' : '_googleGaugeChart';

    // Destroy existing
    if (canvasId === 'cfGaugeChart' && _cfGaugeChart) _cfGaugeChart.destroy();
    if (canvasId === 'googleGaugeChart' && _googleGaugeChart) _googleGaugeChart.destroy();

    const remaining = 100 - value;
    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [value, remaining],
          backgroundColor: [color, colors.grid],
          borderWidth: 0,
          circumference: 180,
          rotation: 270,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '75%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false },
        }
      },
      plugins: [{
        id: 'gaugeText',
        afterDraw(chart) {
          const { ctx: c, chartArea } = chart;
          const cx = (chartArea.left + chartArea.right) / 2;
          const cy = chartArea.bottom - 10;
          c.save();
          c.font = `bold 28px 'Inter'`;
          c.fillStyle = color;
          c.textAlign = 'center';
          c.textBaseline = 'bottom';
          c.fillText(`${value}%`, cx, cy);
          c.restore();
        }
      }]
    });

    if (canvasId === 'cfGaugeChart') _cfGaugeChart = chart;
    else _googleGaugeChart = chart;
  }

  // ═══════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════
  function escHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

})();
