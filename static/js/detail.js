/* ============================================================
   AWS FinOps Dashboard — Profile Detail Page
   ============================================================ */

/* global Chart, t, formatUSD, formatNum, getTheme, escapeHtml, applyChartDefaults, getChartColors, PALETTE, ICONS */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let _profile = '';
let _detailData = null;
let _serviceChart = null;
let _regionChart = null;
let _dailyChart = null;
let _serviceDonutChart = null;

// ---------------------------------------------------------------------------
// Load everything (always Month-to-Date)
// ---------------------------------------------------------------------------

function _mtdRange() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
  const end = fmtDateISO(now);
  return { start, end };
}

async function loadDetail() {
  const params = new URLSearchParams(location.search);
  _profile = params.get('profile') || '';
  if (!_profile) { window.location.href = '/'; return; }

  document.getElementById('profileName').textContent = _profile;
  document.title = `${_profile} — AWS FinOps`;

  showLoading(true);

  try {
    const { start, end } = _mtdRange();
    const url = `/finops/api/detail?profile=${encodeURIComponent(_profile)}&start=${start}&end=${end}`;
    const resp = await fetch(url);
    _detailData = await resp.json();
    renderAll(_detailData);
    loadCostReport();
  } catch (err) {
    showError(err.message || 'Failed to load profile data');
  } finally {
    showLoading(false);
  }
}

function renderAll(data) {
  const costs   = data.costs   || {};
  const regions = data.regions || {};
  const budgets = data.budgets || {};
  const ec2     = data.ec2     || {};
  const credits = data.credits || {};

  renderMetricCards(costs);
  renderCredits(credits);
  renderServiceCharts(costs);
  renderRegionChart(regions);
  renderBudgets(budgets);
  renderAuditSummary(ec2);
  renderEC2(ec2);
  renderAnomalies(costs);
}

// ---------------------------------------------------------------------------
// Metric Cards
// ---------------------------------------------------------------------------

function renderMetricCards(costs) {
  const el = document.getElementById('metricCards');
  if (!el || costs.status !== 'success') return;

  el.innerHTML = `
    <div class="metric-card orange">
      <div class="metric-icon">${ICONS.calendar}</div>
      <div class="metric-label">${t('metric_month')}</div>
      <div class="metric-value">${formatUSD(costs.current_spend)}</div>
      <div class="metric-sub">${costs.current_month}</div>
    </div>
    <div class="metric-card yellow">
      <div class="metric-icon">${ICONS.trendingUp}</div>
      <div class="metric-label">${t('metric_projected')}</div>
      <div class="metric-value">${formatUSD(costs.projection)}</div>
      <div class="metric-sub">End-of-month estimate</div>
    </div>
    <div class="metric-card blue">
      <div class="metric-icon">${ICONS.dollar}</div>
      <div class="metric-label">${t('metric_total')}</div>
      <div class="metric-value">${formatUSD(costs.total_usage)}</div>
      <div class="metric-sub">13-month historical</div>
    </div>
    <div class="metric-card green">
      <div class="metric-icon">${ICONS.tag}</div>
      <div class="metric-label">${t('metric_credits')}</div>
      <div class="metric-value" style="color:var(--green)">${formatUSD(Math.abs(costs.total_credits || 0))}</div>
      <div class="metric-sub">Credits applied</div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Service Charts
// ---------------------------------------------------------------------------

function renderServiceCharts(costs) {
  if (costs.status !== 'success') return;
  applyChartDefaults();
  const cc = getChartColors();

  // Sort by cost descending (Flask jsonify alphabetizes keys)
  const allServices = Object.entries(costs.service_totals || {})
    .sort((a, b) => b[1] - a[1]);

  // Top 20 for bar chart
  const top20 = allServices.slice(0, 20);
  const barLabels = top20.map(([s]) => s.replace('Amazon ', '').replace('AWS ', ''));
  const barValues = top20.map(([, v]) => v);
  const barColors = top20.map((_, i) => PALETTE[i % PALETTE.length]);
  // Keep original full names for click handler
  const barFullNames = top20.map(([s]) => s);

  // Bar chart
  const barCanvas = document.getElementById('serviceBarChart');
  if (barCanvas) {
    if (_serviceChart) _serviceChart.destroy();
    _serviceChart = new Chart(barCanvas, {
      type: 'bar',
      data: {
        labels: barLabels,
        datasets: [{
          data: barValues,
          backgroundColor: barColors.map(c => c + 'cc'),
          borderColor: barColors,
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: cc.tooltip,
            borderColor: cc.border,
            borderWidth: 1,
            titleColor: cc.title,
            bodyColor: cc.text,
            callbacks: {
              title: items => barFullNames[items[0].dataIndex] || items[0].label,
              label: ctx => ` ${formatUSD(ctx.raw)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: cc.grid },
            ticks: { color: cc.text, callback: v => '$' + v.toLocaleString() },
          },
          y: {
            grid: { display: false },
            ticks: {
              color: cc.text,
              font: { size: 10 },
              autoSkip: false,
            },
          },
        },
        onClick: (_, elements) => {
          if (elements.length > 0) {
            const idx = elements[0].index;
            loadServiceDaily(barFullNames[idx]);
          }
        },
      },
    });
  }

  // Doughnut chart — top 8 by cost
  const donutCanvas = document.getElementById('serviceDonutChart');
  if (donutCanvas) {
    if (_serviceDonutChart) _serviceDonutChart.destroy();
    const top8 = allServices.slice(0, 8);
    _serviceDonutChart = new Chart(donutCanvas, {
      type: 'doughnut',
      data: {
        labels: top8.map(([s]) => s.replace('Amazon ', '').replace('AWS ', '')),
        datasets: [{
          data: top8.map(([, v]) => v),
          backgroundColor: top8.map((_, i) => PALETTE[i % PALETTE.length] + 'cc'),
          borderColor: top8.map((_, i) => PALETTE[i % PALETTE.length]),
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: {
            position: 'right',
            labels: { color: cc.text, font: { size: 11 }, usePointStyle: true, pointStyleWidth: 8 },
          },
          tooltip: {
            backgroundColor: cc.tooltip,
            borderColor: cc.border,
            borderWidth: 1,
            titleColor: cc.title,
            bodyColor: cc.text,
            callbacks: { label: ctx => ` ${ctx.label}: ${formatUSD(ctx.raw)}` },
          },
        },
      },
    });
  }

  // Service Table
  renderServiceTable(costs);
}

// Service table sort state
let _svcSortCol = 'cost';  // 'service' | 'cost' | 'pct'
let _svcSortAsc = false;   // default: cost descending

function renderServiceTable(costs) {
  const container = document.getElementById('serviceTableContainer');
  if (!container) return;

  const services = Object.entries(costs.service_totals || {});
  const total = services.reduce((a, [, v]) => a + v, 0);

  // Sort based on current state
  const sorted = [...services].sort((a, b) => {
    let cmp = 0;
    if (_svcSortCol === 'service') {
      cmp = a[0].localeCompare(b[0]);
    } else {
      // cost and pct have same sort order (both based on cost value)
      cmp = a[1] - b[1];
    }
    return _svcSortAsc ? cmp : -cmp;
  });

  const arrow = (col) => {
    if (_svcSortCol !== col) return '<span style="opacity:0.3">⇅</span>';
    return _svcSortAsc ? '↑' : '↓';
  };

  container.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th class="sortable-th" onclick="sortServiceTable('service')" style="cursor:pointer;user-select:none">
          ${t('col_service')} ${arrow('service')}
        </th>
        <th class="num sortable-th" onclick="sortServiceTable('cost')" style="cursor:pointer;user-select:none">
          ${t('col_cost')} ${arrow('cost')}
        </th>
        <th class="num sortable-th" onclick="sortServiceTable('pct')" style="cursor:pointer;user-select:none">
          ${t('col_pct')} ${arrow('pct')}
        </th>
        <th></th>
      </tr></thead>
      <tbody>
        ${sorted.map(([svc, cost]) => `
          <tr class="clickable-row" onclick="loadServiceDaily('${escapeHtml(svc)}')">
            <td>${escapeHtml(svc)}</td>
            <td class="num">${formatUSD(cost)}</td>
            <td class="num">${formatNum(total > 0 ? (cost / total) * 100 : 0)}%</td>
            <td><span style="color:var(--accent);font-size:11px">→</span></td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function sortServiceTable(col) {
  if (_svcSortCol === col) {
    _svcSortAsc = !_svcSortAsc;
  } else {
    _svcSortCol = col;
    _svcSortAsc = col === 'service'; // A-Z default for service, desc for cost/pct
  }
  if (_detailData && _detailData.costs) renderServiceTable(_detailData.costs);
}

// --- Daily service drilldown ---

async function loadServiceDaily(serviceName) {
  const container = document.getElementById('dailyContainer');
  const title = document.getElementById('dailyTitle');
  if (!container) return;

  if (title) title.textContent = `${serviceName} \u2014 Daily (This Month)`;
  container.innerHTML = `<div class="loading-overlay"><span class="spinner"></span></div>`;

  try {
    const resp = await fetch(`/finops/api/service-detail?profile=${encodeURIComponent(_profile)}&service=${encodeURIComponent(serviceName)}&months=6`);
    const data = await resp.json();

    if (data.status !== 'success') {
      container.innerHTML = `<div style="color:var(--red);padding:20px">${escapeHtml(data.error || 'Unknown error')}</div>`;
      return;
    }

    const cc = getChartColors();
    applyChartDefaults();

    const dailyEntries = Object.entries(data.daily).sort(([a], [b]) => a.localeCompare(b));
    const labels = dailyEntries.map(([d]) => d.slice(5)); // MM-DD
    const values = dailyEntries.map(([, v]) => v);

    container.innerHTML = '<canvas id="dailyChart" style="height:200px"></canvas>';
    const canvas = document.getElementById('dailyChart');

    if (_dailyChart) _dailyChart.destroy();
    _dailyChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: '#ff9900aa',
          borderColor: '#ff9900',
          borderWidth: 1,
          borderRadius: 3,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: cc.tooltip,
            borderColor: cc.border,
            borderWidth: 1,
            bodyColor: cc.text,
            callbacks: { label: ctx => ` ${formatUSD(ctx.raw)}` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: cc.text, font: { size: 10 } } },
          y: { grid: { color: cc.grid }, ticks: { color: cc.text, callback: v => '$' + v } },
        },
      },
    });

    // Show and scroll to daily section
    const dailySection = document.getElementById('dailySection');
    if (dailySection) {
      dailySection.style.display = 'block';
      dailySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

  } catch (err) {
    container.innerHTML = `<div style="color:var(--red);padding:20px">${escapeHtml(err.message)}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Credits
// ---------------------------------------------------------------------------

// Credit tab state
let _creditTabItems = [];
let _creditTabCharts = {};

function switchCreditTab(idx) {
  document.querySelectorAll('.credit-tab-btn').forEach((b, i) =>
    b.classList.toggle('active', i === idx));
  document.querySelectorAll('.credit-tab-panel').forEach((p, i) =>
    p.style.display = i === idx ? 'block' : 'none');
  _renderCreditTabChart(idx);
}

function _renderCreditTabChart(idx) {
  if (_creditTabCharts[idx]) return;
  const item = _creditTabItems[idx];
  if (!item) return;
  const canvas = document.getElementById(`creditTabChart_${idx}`);
  if (!canvas) return;
  applyChartDefaults();
  const cc = getChartColors();
  const months = Object.keys(item.monthly || {}).sort();
  const color = item.active ? '#00c87a' : '#7a90a8';
  _creditTabCharts[idx] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: months,
      datasets: [{
        data: months.map(m => item.monthly[m]),
        backgroundColor: color + '55',
        borderColor: color,
        borderWidth: 1,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: cc.tooltip, borderColor: cc.border, borderWidth: 1,
          bodyColor: cc.text, callbacks: { label: ctx => ` ${formatUSD(ctx.raw)}` },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: cc.text, maxRotation: 0 } },
        y: { grid: { color: cc.grid }, ticks: { color: cc.text, callback: v => '$' + v } },
      },
    },
  });
}

function renderCredits(credits) {
  const container = document.getElementById('creditsContainer');
  if (!container) return;

  // ── No data / API error ──────────────────────────────────────────────────
  if (credits.status !== 'success') {
    container.innerHTML = `
      <div class="state-empty" style="padding:20px">
        <div class="state-empty-icon">${ICONS.creditCard}</div>
        <div class="state-empty-text">${escapeHtml(credits.error || 'Credit data unavailable')}</div>
      </div>`;
    return;
  }

  const { status_type, total_used, current_month_credits, monthly_credits, credit_items } = credits;
  const now = new Date();
  const curMonth = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
  const allItems = credit_items || [];
  const activeCount = allItems.filter(c => c.active).length;

  // ── No credits ────────────────────────────────────────────────────────────
  if (status_type === 'none') {
    container.innerHTML = `
      <div class="credit-empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-muted)">
          <rect x="2" y="5" width="20" height="14" rx="2"/>
          <line x1="2" y1="10" x2="22" y2="10"/>
        </svg>
        <div class="credit-empty-title">No AWS Credits</div>
        <div class="credit-empty-sub">This account has no active or historical credits. All charges are direct billing.</div>
      </div>`;
    return;
  }

  // Reset tab state
  _creditTabItems = allItems;
  _creditTabCharts = {};

  // ── Summary bar ───────────────────────────────────────────────────────────
  let html = `
    <div class="credit-summary-bar">
      <div class="credit-summary-stat">
        <div class="credit-summary-label">Total Used</div>
        <div class="credit-summary-value" style="color:var(--green)">${formatUSD(total_used)}</div>
      </div>
      <div class="credit-summary-sep"></div>
      <div class="credit-summary-stat">
        <div class="credit-summary-label">This Month</div>
        <div class="credit-summary-value" style="color:${current_month_credits > 0 ? 'var(--green)' : 'var(--text-muted)'}">
          ${current_month_credits > 0 ? formatUSD(current_month_credits) : '—'}
        </div>
      </div>
      <div class="credit-summary-sep"></div>
      <div class="credit-summary-stat">
        <div class="credit-summary-label">Active Credits</div>
        <div class="credit-summary-value">${activeCount || (status_type === 'active' ? '≥1' : '0')}</div>
      </div>
      <div class="credit-summary-sep"></div>
      <div class="credit-summary-stat">
        <div class="credit-summary-label">Amount Remaining</div>
        <div class="credit-summary-value" style="color:var(--text-muted);font-size:13px" title="Only available in Billing Console">—</div>
      </div>
    </div>`;

  // ── Tabs (one per credit item) ────────────────────────────────────────────
  if (allItems.length > 0) {
    // Tab buttons
    html += `<div class="credit-tabs">`;
    allItems.forEach((c, i) => {
      const shortName = c.id.split('_').slice(0, 2).join('_') || c.id;
      const badge = c.active
        ? `<span class="credit-tab-dot" style="background:var(--green)"></span>`
        : `<span class="credit-tab-dot" style="background:var(--text-muted)"></span>`;
      html += `<button class="credit-tab-btn${i === 0 ? ' active' : ''}" onclick="switchCreditTab(${i})">
        ${badge}<span title="${escapeHtml(c.id)}">${escapeHtml(shortName)}</span>
      </button>`;
    });
    html += `</div>`;

    // Tab panels
    allItems.forEach((c, i) => {
      const months = Object.keys(c.monthly || {}).sort();
      const statusBadge = c.active
        ? `<span class="state-badge state-running">● Active</span>`
        : `<span class="state-badge state-stopped">Expired</span>`;

      html += `<div class="credit-tab-panel" style="display:${i === 0 ? 'block' : 'none'}">`;

      // Credit name + key stats row
      html += `
        <div class="credit-tab-header">
          <div class="credit-tab-name">${escapeHtml(c.id)}</div>
          <div class="credit-tab-stats">
            <div class="credit-tab-stat">
              <span class="credit-tab-stat-label">Amount Used</span>
              <span class="credit-tab-stat-val" style="color:var(--green)">${formatUSD(c.total_used)}</span>
            </div>
            <div class="credit-tab-stat">
              <span class="credit-tab-stat-label">Issued Amount</span>
              <span class="credit-tab-stat-val" style="color:var(--text-muted)" title="See Billing Console">—</span>
            </div>
            <div class="credit-tab-stat">
              <span class="credit-tab-stat-label">Remaining</span>
              <span class="credit-tab-stat-val" style="color:var(--text-muted)" title="See Billing Console">—</span>
            </div>
            <div class="credit-tab-stat">
              <span class="credit-tab-stat-label">Expiration</span>
              <span class="credit-tab-stat-val" style="color:var(--text-muted)" title="See Billing Console">—</span>
            </div>
            <div class="credit-tab-stat">
              <span class="credit-tab-stat-label">First Applied</span>
              <span class="credit-tab-stat-val">${c.first_used || '—'}</span>
            </div>
            <div class="credit-tab-stat">
              <span class="credit-tab-stat-label">Last Applied</span>
              <span class="credit-tab-stat-val">${c.active ? '<span style="color:var(--green)">Active</span>' : (c.last_used || '—')}</span>
            </div>
            <div class="credit-tab-stat">
              <span class="credit-tab-stat-label">Status</span>
              <span class="credit-tab-stat-val">${statusBadge}</span>
            </div>
          </div>
        </div>`;

      // Monthly chart + table
      if (months.length > 0) {
        html += `
          <div style="margin:14px 0 10px">
            <div class="credit-section-label">Monthly Usage</div>
            <div style="height:140px;margin-bottom:12px"><canvas id="creditTabChart_${i}"></canvas></div>
            <table class="data-table">
              <thead><tr>
                <th>Month</th>
                <th class="num">Credits Applied</th>
                <th></th>
              </tr></thead>
              <tbody>
                ${months.slice().reverse().map(m => {
                  const amt = c.monthly[m];
                  const isThis = m === curMonth;
                  return `<tr>
                    <td>${m}${isThis ? ' <span class="state-badge state-running" style="font-size:10px;margin-left:6px">current</span>' : ''}</td>
                    <td class="num" style="color:var(--green)">${formatUSD(amt)}</td>
                    <td>${isThis ? '<span style="color:var(--green);font-size:12px">● Active</span>' : '<span style="color:var(--text-muted);font-size:12px">Applied</span>'}</td>
                  </tr>`;
                }).join('')}
              </tbody>
            </table>
          </div>`;
      } else {
        html += `<div style="padding:12px 0;color:var(--text-muted);font-size:13px">No monthly breakdown available for this credit.</div>`;
      }

      html += `</div>`; // end panel
    });

  } else if (status_type === 'active') {
    // No per-subscription breakdown, fallback to total monthly chart
    const months = Object.keys(monthly_credits).sort();
    html += `
      <div class="credit-section-label">Monthly Usage (All Credits)</div>
      <div style="height:140px;margin-bottom:12px"><canvas id="creditTabChart_0"></canvas></div>
      <table class="data-table" style="margin-bottom:16px">
        <thead><tr><th>Month</th><th class="num">Credits Applied</th><th></th></tr></thead>
        <tbody>
          ${months.slice().reverse().map(m => {
            const amt = monthly_credits[m];
            const isThis = m === curMonth;
            return `<tr>
              <td>${m}${isThis ? ' <span class="state-badge state-running" style="font-size:10px;margin-left:6px">current</span>' : ''}</td>
              <td class="num" style="color:var(--green)">${formatUSD(amt)}</td>
              <td>${isThis ? '<span style="color:var(--green);font-size:12px">● Active</span>' : '<span style="color:var(--text-muted);font-size:12px">Applied</span>'}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>`;
    _creditTabItems = [{ id: 'All Credits', active: true, monthly: monthly_credits, total_used, first_used: null, last_used: null }];
  }

  // ── API note ──────────────────────────────────────────────────────────────
  html += `
    <div style="margin-top:14px;padding:9px 13px;background:var(--bg-input);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:11px;color:var(--text-muted)">
      ℹ️ <strong style="color:var(--text-secondary)">Issued amount · Expiration date · Amount remaining</strong>
      are not exposed by the AWS Cost Explorer API. View exact figures at
      <strong style="color:var(--text-secondary)">AWS Billing Console → Credits</strong>.
    </div>`;

  container.innerHTML = html;

  // Render chart for the first (active) tab immediately
  _renderCreditTabChart(0);
}

// ---------------------------------------------------------------------------
// Region Chart
// ---------------------------------------------------------------------------

function renderRegionChart(regions) {
  const canvas = document.getElementById('regionChart');
  if (!canvas || regions.status !== 'success') {
    if (canvas) canvas.closest('.chart-card').innerHTML += `<div style="color:var(--text-muted);padding:20px;text-align:center">Region data unavailable</div>`;
    return;
  }
  applyChartDefaults();
  const cc = getChartColors();

  // Sort by cost descending (Flask jsonify sorts keys alphabetically, breaking order)
  // Filter out Global/Marketplace from the chart — it gets its own detail section below
  const allEntries = Object.entries(regions.region_totals || {})
    .sort((a, b) => b[1] - a[1]);

  const globalLabel = 'Global / Marketplace';
  const regionalEntries = allEntries
    .filter(([r]) => r !== globalLabel)
    .filter(([, v]) => v >= 0.50)   // filter out negligible $0 regions
    .slice(0, 12);

  const globalEntry = allEntries.find(([r]) => r === globalLabel);

  const labels = regionalEntries.map(([r]) => r);
  const values = regionalEntries.map(([, v]) => v);
  const colors = labels.map((_, i) => PALETTE[i % PALETTE.length]);

  if (_regionChart) _regionChart.destroy();
  _regionChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Cost ($)',
        data: values,
        backgroundColor: colors.map(c => c + 'cc'),
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 3,
        maxBarThickness: 14,
        barPercentage: 0.6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      layout: { padding: { top: 0, bottom: 0 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: cc.tooltip,
          borderColor: cc.border,
          borderWidth: 1,
          titleColor: cc.title,
          bodyColor: cc.text,
          callbacks: {
            label: ctx => ` ${formatUSD(ctx.raw)}`,
          },
        },
      },
      scales: {
        x: { grid: { color: cc.grid }, ticks: { color: cc.text, font: { size: 10 }, callback: v => '$' + v.toLocaleString() } },
        y: { grid: { display: false }, ticks: { color: cc.text, font: { size: 10 }, padding: 2 } },
      },
    },
  });

  // Render global services detail table below the chart
  _renderGlobalServicesDetail(regions.global_services, globalEntry ? globalEntry[1] : 0);
}

function _renderGlobalServicesDetail(globalServices, globalTotal) {
  const container = document.getElementById('globalServicesDetail');
  if (!container) return;

  if ((!globalServices || Object.keys(globalServices).length === 0) && !globalTotal) {
    container.innerHTML = '';
    return;
  }

  const entries = Object.entries(globalServices || {}).sort((a, b) => b[1] - a[1]);
  const total = globalTotal || entries.reduce((s, [, v]) => s + v, 0);

  container.innerHTML = `
    <div style="margin-top:12px;padding:12px 16px;background:var(--bg-input);border:1px solid var(--border);border-radius:var(--radius-sm)">
      <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:8px;display:flex;align-items:center;gap:6px">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        Global / Marketplace Services (${formatUSD(total)})
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">
        These services report under us-east-1 but are global, marketplace, or SaaS subscriptions — not actual regional infrastructure.
      </div>
      ${entries.length > 0 ? `
      <table class="data-table" style="font-size:12px">
        <thead><tr><th>Service</th><th class="num">Cost</th></tr></thead>
        <tbody>
          ${entries.map(([svc, cost]) => `
            <tr>
              <td>${escapeHtml(svc)}</td>
              <td class="num">${formatUSD(cost)}</td>
            </tr>`).join('')}
        </tbody>
      </table>` : ''}
    </div>`;
}

// ---------------------------------------------------------------------------
// Budgets
// ---------------------------------------------------------------------------

function renderBudgets(budgets) {
  const container = document.getElementById('budgetContainer');
  if (!container) return;

  if (budgets.status !== 'success') {
    container.innerHTML = `<div class="state-empty"><div class="state-empty-icon">${ICONS.wallet}</div><div class="state-empty-text">${escapeHtml(budgets.error || t('budget_none'))}</div></div>`;
    return;
  }

  const list = budgets.budgets || [];
  if (!list.length) {
    container.innerHTML = `<div class="state-empty"><div class="state-empty-icon">${ICONS.wallet}</div><div class="state-empty-text" data-i18n="budget_none">${t('budget_none')}</div></div>`;
    return;
  }

  container.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>${t('col_budget_name')}</th>
        <th>Type</th>
        <th class="num">${t('col_limit')}</th>
        <th class="num">${t('col_actual')}</th>
        <th class="num">${t('col_forecast')}</th>
        <th>${t('col_usage')}</th>
      </tr></thead>
      <tbody>
        ${list.map(b => {
          const cls = b.pct_used >= 100 ? 'over' : b.pct_used >= 80 ? 'warn' : 'ok';
          const pctCapped = Math.min(b.pct_used, 100);
          return `
            <tr>
              <td>${escapeHtml(b.name)}</td>
              <td><span class="state-badge state-running">${escapeHtml(b.type)}</span></td>
              <td class="num">${formatUSD(b.limit)}</td>
              <td class="num">${formatUSD(b.actual)}</td>
              <td class="num">${formatUSD(b.forecasted)}</td>
              <td style="min-width:140px">
                <div style="display:flex;align-items:center;gap:8px">
                  <div class="budget-bar-wrap" style="flex:1">
                    <div class="budget-bar ${cls}" style="width:${pctCapped}%"></div>
                  </div>
                  <span style="font-size:12px;min-width:38px;text-align:right">${formatNum(b.pct_used)}%</span>
                </div>
              </td>
            </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

// ---------------------------------------------------------------------------
// EC2 Inventory
// ---------------------------------------------------------------------------

// EC2 sort state
let _ec2Instances = [];
let _ec2SortCol = -1;
let _ec2SortAsc = true;

const _EC2_COLS = [
  { key: 'name',        label: () => t('col_name'),        align: 'left',   val: i => i.name || '' },
  { key: 'id',          label: () => t('col_instance'),    align: 'left',   val: i => i.id || '' },
  { key: 'type',        label: () => t('col_type'),        align: 'left',   val: i => i.type || '' },
  { key: 'state',       label: () => t('col_state'),       align: 'left',   val: i => i.state || '' },
  { key: 'region',      label: () => t('col_region'),      align: 'left',   val: i => i.region || '' },
  { key: 'vcpu',        label: () => 'vCPU',               align: 'center', val: i => i.vcpu || 0, numeric: true },
  { key: 'ram_gb',      label: () => 'RAM',                align: 'right',  val: i => i.ram_gb || 0, numeric: true },
  { key: 'disk_count',  label: () => 'Disks',              align: 'center', val: i => i.disk_count || 0, numeric: true },
  { key: 'total_disk_gb', label: () => 'Storage',          align: 'right',  val: i => i.total_disk_gb || 0, numeric: true },
  { key: 'environment', label: () => t('col_environment'), align: 'left',   val: i => i.environment || '' },
  { key: 'untagged',    label: () => t('col_untagged'),    align: 'left',   val: i => i.untagged ? 1 : 0, numeric: true },
];

function _ec2Sort(colIdx) {
  if (_ec2SortCol === colIdx) {
    _ec2SortAsc = !_ec2SortAsc;
  } else {
    _ec2SortCol = colIdx;
    _ec2SortAsc = true;
  }
  const col = _EC2_COLS[colIdx];
  _ec2Instances.sort((a, b) => {
    const va = col.val(a);
    const vb = col.val(b);
    if (col.numeric) return _ec2SortAsc ? va - vb : vb - va;
    return _ec2SortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
  _ec2RenderTable();
}

function _ec2RenderTable() {
  const container = document.getElementById('ec2Container');
  if (!container) return;

  const arrow = (idx) => {
    if (_ec2SortCol !== idx) return ' <span style="opacity:0.3">⇅</span>';
    return _ec2SortAsc ? ' ▲' : ' ▼';
  };

  const thead = _EC2_COLS.map((c, idx) =>
    `<th style="text-align:${c.align};cursor:pointer;user-select:none;white-space:nowrap" onclick="_ec2Sort(${idx})">${c.label()}${arrow(idx)}</th>`
  ).join('');

  const tbody = _ec2Instances.map(i => {
    const diskCount = i.disk_count || 0;
    const totalGb = i.total_disk_gb || 0;
    const disks = i.disks || [];
    const diskTooltip = disks.length
      ? disks.map(d => `${escapeHtml(d.device)}: ${d.size_gb}GB ${escapeHtml(d.type)}${d.encrypted ? ' enc' : ''}`).join('\n')
      : 'No EBS data';
    return `<tr>
      <td>${escapeHtml(i.name)}</td>
      <td style="font-family:monospace;font-size:12px">${escapeHtml(i.id)}</td>
      <td>${escapeHtml(i.type)}</td>
      <td><span class="state-badge state-${escapeHtml(i.state)}">${i.state === 'running' ? t('state_running') : t('state_stopped')}</span></td>
      <td>${escapeHtml(i.region)}</td>
      <td style="text-align:center;font-weight:600">${i.vcpu || '—'}</td>
      <td style="text-align:right;font-weight:600">${i.ram_gb ? i.ram_gb + ' GB' : '—'}</td>
      <td style="text-align:center;cursor:default" title="${escapeHtml(diskTooltip)}"><span style="font-weight:600;color:var(--accent)">${diskCount}</span></td>
      <td style="text-align:right;font-weight:600">${totalGb > 0 ? totalGb + ' GB' : '—'}</td>
      <td>${escapeHtml(i.environment)}</td>
      <td>${i.untagged ? `<span style="color:var(--red);display:inline-flex;align-items:center;gap:3px">${ICONS.alertTriangle} Yes</span>` : `<span style="color:var(--green);display:inline-flex;align-items:center">${ICONS.check}</span>`}</td>
    </tr>`;
  }).join('');

  container.innerHTML = `
    <div style="max-height:420px;overflow-y:auto">
      <table class="data-table">
        <thead style="position:sticky;top:0;z-index:1;background:var(--bg-card)"><tr>${thead}</tr></thead>
        <tbody>${tbody}</tbody>
      </table>
    </div>`;
}

function _ec2ExportCsv() {
  if (!_ec2Instances.length) return;
  const headers = ['Name','Instance','Type','State','Region','vCPU','RAM_GB','Disks','Storage_GB','Environment','Untagged'];
  const rows = _ec2Instances.map(i => [
    i.name || '-',
    i.id || '',
    i.type || '',
    i.state || '',
    i.region || '',
    i.vcpu || 0,
    i.ram_gb || 0,
    i.disk_count || 0,
    i.total_disk_gb || 0,
    i.environment || '-',
    i.untagged ? 'Yes' : 'No',
  ]);
  let csv = headers.join(',') + '\n';
  for (const row of rows) {
    csv += row.map(v => {
      const s = String(v);
      return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(',') + '\n';
  }
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const profile = new URLSearchParams(window.location.search).get('profile') || 'unknown';
  const date = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `ec2_inventory_${profile}_${date}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function renderEC2(ec2) {
  const container = document.getElementById('ec2Container');
  if (!container) return;

  if (ec2.status !== 'success') {
    container.innerHTML = `<div class="state-empty"><div class="state-empty-icon">${ICONS.monitor}</div><div class="state-empty-text">${escapeHtml(ec2.error || 'EC2 data unavailable')}</div></div>`;
    return;
  }

  _ec2Instances = ec2.instances || [];
  if (!_ec2Instances.length) {
    container.innerHTML = `<div class="state-empty"><div class="state-empty-icon">${ICONS.monitor}</div><div class="state-empty-text">No EC2 instances found</div></div>`;
    return;
  }

  // Default sort: running first, then by region
  _ec2SortCol = -1;
  _ec2SortAsc = true;
  _ec2Instances.sort((a, b) => {
    if (a.state !== b.state) return a.state === 'running' ? -1 : 1;
    return a.region.localeCompare(b.region);
  });

  _ec2RenderTable();
}

// ---------------------------------------------------------------------------
// FinOps Audit Summary
// ---------------------------------------------------------------------------

function renderAuditSummary(ec2) {
  const el = document.getElementById('auditSummary');
  if (!el) return;

  if (ec2.status !== 'success') {
    el.innerHTML = '';
    return;
  }

  const s = ec2.summary || {};
  const instances = ec2.instances || [];

  // Calculate running vs stopped resource totals
  const running = instances.filter(i => i.state === 'running');
  const stopped = instances.filter(i => i.state === 'stopped');

  const runVcpu = running.reduce((sum, i) => sum + (i.vcpu || 0), 0);
  const runRam  = running.reduce((sum, i) => sum + (i.ram_gb || 0), 0);
  const runDisk = running.reduce((sum, i) => sum + (i.total_disk_gb || 0), 0);

  const stopVcpu = stopped.reduce((sum, i) => sum + (i.vcpu || 0), 0);
  const stopRam  = stopped.reduce((sum, i) => sum + (i.ram_gb || 0), 0);
  const stopDisk = stopped.reduce((sum, i) => sum + (i.total_disk_gb || 0), 0);

  const runSub = runVcpu || runRam || runDisk
    ? `<div style="font-size:9px;color:var(--text-muted);margin-top:2px">${runVcpu} vCPU · ${runRam} GB RAM · ${runDisk} GB Disk</div>`
    : '';
  const stopSub = stopVcpu || stopRam || stopDisk
    ? `<div style="font-size:9px;color:var(--text-muted);margin-top:2px">${stopVcpu} vCPU · ${stopRam} GB RAM · ${stopDisk} GB Disk</div>`
    : '';

  el.innerHTML = `
    <div class="audit-card ok">
      <div class="audit-number">${s.total || 0}</div>
      <div class="audit-label" data-i18n="audit_total_ec2">${t('audit_total_ec2')}</div>
    </div>
    <div class="audit-card ok">
      <div class="audit-number">${s.running || 0}</div>
      <div class="audit-label" data-i18n="audit_running">${t('audit_running')}</div>
      ${runSub}
    </div>
    <div class="audit-card ${s.stopped > 0 ? 'danger' : 'ok'}">
      <div class="audit-number">${s.stopped || 0}</div>
      <div class="audit-label" data-i18n="audit_stopped">${t('audit_stopped')}</div>
      ${stopSub}
    </div>
    <div class="audit-card ${s.untagged > 0 ? 'danger' : 'ok'}">
      <div class="audit-number">${s.untagged || 0}</div>
      <div class="audit-label" data-i18n="audit_untagged">${t('audit_untagged')}</div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Anomalies
// ---------------------------------------------------------------------------

function renderAnomalies(costs) {
  const container = document.getElementById('anomalyContainer');
  if (!container || costs.status !== 'success') return;

  const anomalies = costs.anomalies || [];
  if (!anomalies.length) {
    container.innerHTML = `
      <div class="state-empty" style="padding:20px">
        <div class="state-empty-icon" style="color:var(--green)">${ICONS.checkCircle}</div>
        <div class="state-empty-text" data-i18n="anomaly_none">${t('anomaly_none')}</div>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="alert-list">
      ${anomalies.map(a => `
        <div class="alert-item alert-${a.severity}">
          <div class="alert-icon">${a.severity === 'critical' ? ICONS.alertCircle : ICONS.alertTriangle}</div>
          <div class="alert-text">
            <div class="alert-title">${a.month}: +${formatNum(a.change_pct)}% ${t('anomaly_vs')}</div>
            <div class="alert-desc">${formatUSD(a.prev_cost)} → ${formatUSD(a.curr_cost)}</div>
          </div>
        </div>`).join('')}
    </div>`;
}

// ---------------------------------------------------------------------------
// Cost Report
// ---------------------------------------------------------------------------

let _costReportGran   = 'DAILY';
let _costReportPeriod = 'mtd';  // default: Month to Date
let _costTrendChart   = null;

const CR_PERIODS = [
  { key: 'mtd', labelTr: 'Bu Ay', labelEn: 'MTD',  mtd: true,  defaultGran: 'DAILY'   },
  { key: '1m',  labelTr: '1 Ay',  labelEn: '1M',   months: 1,  defaultGran: 'DAILY'   },
  { key: '3m',  labelTr: '3 Ay',  labelEn: '3M',   months: 3,  defaultGran: 'MONTHLY' },
  { key: '6m',  labelTr: '6 Ay',  labelEn: '6M',   months: 6,  defaultGran: 'MONTHLY' },
  { key: '12m', labelTr: '12 Ay', labelEn: '12M',  months: 12, defaultGran: 'MONTHLY' },
];

function _crPeriodDates(key) {
  const today = new Date(); today.setHours(0,0,0,0);
  const p = CR_PERIODS.find(x => x.key === key);
  if (p.mtd) {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    return { start: fmtDateISO(start), end: fmtDateISO(today) };
  }
  const start = new Date(today.getFullYear(), today.getMonth() - p.months, today.getDate());
  return { start: fmtDateISO(start), end: fmtDateISO(today) };
}

function setCostReportPeriod(key) {
  _costReportPeriod = key;
  const p = CR_PERIODS.find(x => x.key === key);
  if (p) _costReportGran = p.defaultGran;
  document.querySelectorAll('.cr-period-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.p === key));
  document.querySelectorAll('.cr-gran-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.g === _costReportGran));
  loadCostReport();
}

function setCostReportGran(g) {
  _costReportGran = g;
  document.querySelectorAll('.cr-gran-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.g === g));
  loadCostReport();
}

async function loadCostReport() {
  const container = document.getElementById('costReportContainer');
  if (!container || !_profile) return;

  container.innerHTML = '<div class="loading-overlay" style="min-height:80px"><span class="spinner"></span></div>';

  const { start, end } = _crPeriodDates(_costReportPeriod);
  const url = `/finops/api/cost-report?profile=${encodeURIComponent(_profile)}&granularity=${_costReportGran}&start=${start}&end=${end}`;

  try {
    const resp = await fetch(url);
    const data = await resp.json();
    renderCostReport(data);
  } catch (err) {
    container.innerHTML = `<div class="state-empty" style="padding:20px"><div class="state-empty-text">${escapeHtml(err.message)}</div></div>`;
  }
}

function renderCostReport(data) {
  const container = document.getElementById('costReportContainer');
  if (!container) return;

  if (data.status !== 'success') {
    container.innerHTML = `<div class="state-empty" style="padding:20px"><div class="state-empty-text">${escapeHtml(data.error || 'Unknown error')}</div></div>`;
    return;
  }

  const { periods, services, total_cost, avg_daily_cost, service_count, granularity, period_totals } = data;

  const fmtPeriod = (p) => {
    const d = new Date(p.start + 'T00:00:00');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    if (granularity === 'MONTHLY') return `${months[d.getMonth()]} ${d.getFullYear()}`;
    return `${months[d.getMonth()]} ${d.getDate()}`;
  };

  // Heat color for cells (0 = transparent, max = accent)
  const maxPeriodVal = Math.max(...services.flatMap(s =>
    Object.values(s.by_period || {})), 0.01);

  const heatBg = (v) => {
    if (!v || v <= 0) return '';
    const pct = Math.min(v / maxPeriodVal, 1);
    const alpha = Math.round(pct * 55);
    return `background:rgba(255,153,0,${(alpha/255).toFixed(2)})`;
  };

  const lang = document.documentElement.lang || 'en';

  // Build period labels and values for chart
  const chartLabels = periods.map(p => fmtPeriod(p));
  const chartValues = periods.map(p => period_totals[p.start] || 0);

  let html = `
    <div style="padding:16px 20px 0">
      <div class="cr-controls">
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <!-- Period buttons -->
          <div class="cr-period-row">
            ${CR_PERIODS.map(p => `
              <button class="cr-period-btn${_costReportPeriod === p.key ? ' active' : ''}" data-p="${p.key}" onclick="setCostReportPeriod('${p.key}')">
                ${lang === 'tr' ? p.labelTr : p.labelEn}
              </button>`).join('')}
          </div>
          <div class="cr-divider"></div>
          <!-- Granularity buttons -->
          <div class="cr-gran-row">
            ${['DAILY','MONTHLY'].map(g => `
              <button class="cr-gran-btn${_costReportGran === g ? ' active' : ''}" data-g="${g}" onclick="setCostReportGran('${g}')">
                ${g.charAt(0) + g.slice(1).toLowerCase()}
              </button>`).join('')}
          </div>
        </div>
        <div class="cr-stats-row">
          <div class="cr-stat-pill">
            <span class="cr-stat-pill-label">Total Cost</span>
            <span class="cr-stat-pill-val" style="color:var(--accent)">${formatUSD(total_cost)}</span>
          </div>
          <div class="cr-stat-pill">
            <span class="cr-stat-pill-label">Avg Daily</span>
            <span class="cr-stat-pill-val">${formatUSD(avg_daily_cost)}</span>
          </div>
          <div class="cr-stat-pill">
            <span class="cr-stat-pill-label">Services</span>
            <span class="cr-stat-pill-val">${service_count}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Cost Trend Chart -->
    <div style="position:relative;height:140px;padding:8px 20px 0">
      <canvas id="costTrendChart"></canvas>
    </div>

    <div style="overflow-x:auto;padding:12px 0 4px">
      <table class="data-table cr-table">
        <thead>
          <tr>
            <th class="cr-svc-col">Service</th>
            <th class="num cr-total-col">Total</th>
            ${periods.map(p => `<th class="num cr-period-th">${fmtPeriod(p)}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          <tr class="cr-total-row">
            <td class="cr-svc-col">Total</td>
            <td class="num cr-total-col" style="color:var(--accent)">${formatUSD(total_cost)}</td>
            ${periods.map(p => {
              const v = period_totals[p.start] || 0;
              return `<td class="num cr-cell" style="color:var(--accent)">${v > 0 ? formatUSD(v) : '—'}</td>`;
            }).join('')}
          </tr>
          ${services.map(s => `
            <tr>
              <td class="cr-svc-col">${escapeHtml(s.name)}</td>
              <td class="num cr-total-col" style="font-weight:600">${formatUSD(s.total)}</td>
              ${periods.map(p => {
                const v = s.by_period[p.start] || 0;
                return `<td class="num cr-cell" style="${heatBg(v)}">${v > 0 ? formatUSD(v) : '<span style="color:var(--border-light)">—</span>'}</td>`;
              }).join('')}
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;

  container.innerHTML = html;

  // Render cost trend chart
  _renderCostTrendChart(chartLabels, chartValues);
}

function _renderCostTrendChart(labels, values) {
  const canvas = document.getElementById('costTrendChart');
  if (!canvas || !labels.length) return;
  applyChartDefaults();
  const cc = getChartColors();

  if (_costTrendChart) _costTrendChart.destroy();

  // Calculate average from actual chart values (excludes zeros)
  const nonZero = values.filter(v => v > 0);
  const avg = nonZero.length > 0 ? nonZero.reduce((a, b) => a + b, 0) / nonZero.length : 0;
  const avgLine = labels.map(() => avg);

  _costTrendChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Cost',
          data: values,
          borderColor: '#ff9900',
          backgroundColor: (ctx) => {
            const chart = ctx.chart;
            const { ctx: c, chartArea } = chart;
            if (!chartArea) return '#ff990022';
            const gradient = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
            gradient.addColorStop(0, 'rgba(255,153,0,0.35)');
            gradient.addColorStop(1, 'rgba(255,153,0,0.02)');
            return gradient;
          },
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: values.length > 20 ? 0 : 3,
          pointHoverRadius: 5,
          pointBackgroundColor: '#ff9900',
        },
        {
          label: 'Avg',
          data: avgLine,
          borderColor: cc.text + '55',
          borderWidth: 1,
          borderDash: [4, 4],
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { left: 0, right: 0 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: cc.tooltip,
          borderColor: cc.border,
          borderWidth: 1,
          titleColor: cc.title,
          bodyColor: cc.text,
          callbacks: {
            label: ctx => {
              if (ctx.datasetIndex === 1) return ` Average: ${formatUSD(ctx.raw)}`;
              return ` Cost: ${formatUSD(ctx.raw)}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            color: cc.text,
            font: { size: 9 },
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 15,
          },
        },
        y: {
          grid: { color: cc.grid },
          ticks: {
            color: cc.text,
            font: { size: 9 },
            callback: v => '$' + v.toLocaleString(),
          },
          beginAtZero: true,
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function showLoading(show) {
  const el = document.getElementById('loadingOverlay');
  if (el) el.style.display = show ? 'flex' : 'none';
}

function showError(msg) {
  const body = document.getElementById('pageBody');
  if (body) body.innerHTML = `
    <div class="state-empty">
      <div class="state-empty-icon">${ICONS.warning}</div>
      <div class="state-empty-text">${escapeHtml(msg)}</div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Collapsible Sections
// ---------------------------------------------------------------------------

function toggleSection(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('open');
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtDateISO(d) {
  if (!d) return '';
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

// ---------------------------------------------------------------------------
// Init — prevent any navigation away from this page
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  loadDetail();

  // Prevent hash-based navigation from redirecting away from detail page.
  // The main dashboard uses hash (#dashboard, #reports) but on the detail
  // page we must stay here. Override popstate and hashchange to ignore.
  window.addEventListener('hashchange', (e) => {
    e.preventDefault();
    // Restore the URL without hash interference
    const base = window.location.pathname + window.location.search;
    history.replaceState(null, '', base);
  });

  // Intercept sidebar nav-item clicks that would navigate away via hash
  document.querySelectorAll('.nav-item[data-section]').forEach(link => {
    link.addEventListener('click', (e) => {
      // On detail page, section-based nav should go to dashboard page
      e.preventDefault();
      e.stopPropagation();
      window.location.href = '/#' + (link.dataset.section || 'dashboard');
    });
  });
});

document.addEventListener('themechange', () => {
  if (_detailData) {
    applyChartDefaults();
    renderServiceCharts(_detailData.costs || {});
    renderRegionChart(_detailData.regions || {});
    loadCostReport();
  }
});

document.addEventListener('langchange', () => {
  if (_detailData) renderAll(_detailData);
});
