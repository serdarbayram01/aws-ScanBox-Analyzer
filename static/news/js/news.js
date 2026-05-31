/* ============================================================
   News Module — vanilla JS controller.
   Depends on:
     - Fuse.js (loaded via CDN in templates/news/index.html)
     - escapeHtml, t, getLang, getTheme  (global, from /static/js/i18n.js)
   ============================================================ */

(function () {
  'use strict';

  // -------------------- State --------------------
  const state = {
    feed:           null,           // raw feed dict { lastUpdated, itemCount, items }
    items:          [],             // items array
    query:          '',
    filters:        new Set(),      // active category/service filter names
    dateFilter:     'all',          // 'all' | '7d' | '14d' | '30d'
    catSearchText:  '',             // internal search inside Categories dropdown
    fuse:           null,
    refreshing:     false,
    openDropdown:   null,           // 'cat' | 'date' | null
  };

  // Date filter presets — days back from now. 0 / null means no date constraint.
  const DATE_DAYS = { all: 0, '7d': 7, '14d': 14, '30d': 30 };

  // Feed-source labels (mirrors fetcher.RSS_FEEDS[].source). These are
  // promoted to the TOP of the Categories dropdown with a distinct icon and
  // a separator line before the regular service/category rows.
  const FEED_SOURCES = new Set(["What's New", 'Official Blog', 'Security Bulletins']);
  const FEED_ICON_SVG =
    '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/>' +
    '<circle cx="5" cy="19" r="1.4" fill="currentColor"/></svg>';

  // -------------------- DOM refs --------------------
  const $ = (sel) => document.querySelector(sel);
  const els = {
    search:         $('#newsSearch'),
    searchClear:    $('#newsSearchClear'),
    grid:           $('#newsGrid'),
    resultCount:    $('#newsResultCount'),
    clearFilters:   $('#newsClearFilters'),
    activeCount:    $('#newsActiveCount'),
    itemsCount:     $('#newsItemsCount'),
    empty:          $('#newsEmpty'),
    error:          $('#newsError'),
    totalCount:     $('#newsTotalCount'),
    newCount:       $('#newsNewCount'),
    newBadge:       $('#newsNewBadge'),
    lastUpdated:    $('#newsLastUpdated'),
    refreshBtn:     $('#newsRefreshSidebar'),
    updatedStat:    $('#newsUpdatedStat'),     // clickable "Last updated" pill
    kbdHint:        $('#newsKbdHint'),
    // Categories dropdown
    catDropdown:    $('#newsCatDropdown'),
    catBtn:         $('#newsCatBtn'),
    catBtnCount:    $('#newsCatBtnCount'),
    catPanel:       $('#newsCatPanel'),
    catSearch:      $('#newsCatSearch'),
    catList:        $('#newsCatList'),
    catClear:       $('#newsCatClear'),
    catInfo:        $('#newsCatInfo'),
    // Date dropdown
    dateDropdown:   $('#newsDateDropdown'),
    dateBtn:        $('#newsDateBtn'),
    dateValue:      $('#newsDateValue'),
    datePanel:      $('#newsDatePanel'),
    // Active filter pills
    activeFilters:  $('#newsActiveFilters'),
  };

  // -------------------- Deterministic tag palette --------------------
  // Hash-based stable color per tag — same tag always gets same color.
  const NEWS_PALETTE = [
    { bg: 'rgba(99,102,241,0.12)',  bd: 'rgba(99,102,241,0.55)',  fg: '#8b94f7' }, // indigo
    { bg: 'rgba(34,211,238,0.12)',  bd: 'rgba(34,211,238,0.55)',  fg: '#3fd7e9' }, // cyan
    { bg: 'rgba(16,185,129,0.12)',  bd: 'rgba(16,185,129,0.55)',  fg: '#22c599' }, // emerald
    { bg: 'rgba(249,115,22,0.12)',  bd: 'rgba(249,115,22,0.55)',  fg: '#f59353' }, // orange
    { bg: 'rgba(236,72,153,0.12)',  bd: 'rgba(236,72,153,0.55)',  fg: '#f06fa9' }, // pink
    { bg: 'rgba(139,92,246,0.12)',  bd: 'rgba(139,92,246,0.55)',  fg: '#a98cf2' }, // violet
    { bg: 'rgba(245,158,11,0.12)',  bd: 'rgba(245,158,11,0.55)',  fg: '#f0a83b' }, // amber
    { bg: 'rgba(34,197,94,0.12)',   bd: 'rgba(34,197,94,0.55)',   fg: '#3acf76' }, // green
    { bg: 'rgba(239,68,68,0.12)',   bd: 'rgba(239,68,68,0.55)',   fg: '#ef6868' }, // red
    { bg: 'rgba(56,189,248,0.12)',  bd: 'rgba(56,189,248,0.55)',  fg: '#52bcef' }, // sky
    { bg: 'rgba(132,204,22,0.12)',  bd: 'rgba(132,204,22,0.55)',  fg: '#a3d34d' }, // lime
    { bg: 'rgba(217,70,239,0.12)',  bd: 'rgba(217,70,239,0.55)',  fg: '#d77ce8' }, // fuchsia
  ];
  function djb2(str) {
    let h = 5381;
    for (let i = 0; i < str.length; i++) {
      h = ((h << 5) + h) ^ str.charCodeAt(i);
    }
    return Math.abs(h | 0);
  }
  function tagColor(tag) {
    return NEWS_PALETTE[djb2(String(tag).toLowerCase()) % NEWS_PALETTE.length];
  }

  // -------------------- Translation helper --------------------
  // Reads TRANSLATIONS from i18n.js directly. We don't call the global t()
  // because Fuse.js (loaded right before this file) ships a top-level helper
  // also named `t` that shadows the i18n one and would return non-string
  // values, rendering function source as text. TRANSLATIONS itself is a
  // namespaced const and stays intact.
  function currentLang() {
    // Read localStorage directly so we're immune to any global function shadowing.
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

  // -------------------- Date formatting --------------------
  function relativeTime(iso) {
    if (!iso) return '—';
    const date = new Date(iso);
    if (Number.isNaN(+date)) return '—';
    const diff = (Date.now() - date.getTime()) / 1000;
    const lang = currentLang();
    const isTr = lang === 'tr';
    const units = [
      { sec: 60,           one: isTr ? 'sn'  : 's',  many: isTr ? 'sn'  : 's'  },
      { sec: 3600,         one: isTr ? 'dk'  : 'm',  many: isTr ? 'dk'  : 'm'  },
      { sec: 86400,        one: isTr ? 'sa'  : 'h',  many: isTr ? 'sa'  : 'h'  },
      { sec: 86400 * 30,   one: isTr ? 'gun' : 'd',  many: isTr ? 'gun' : 'd'  },
      { sec: 86400 * 365,  one: isTr ? 'ay'  : 'mo', many: isTr ? 'ay'  : 'mo' },
    ];
    let prev = 1;
    for (const u of units) {
      if (diff < u.sec) {
        const n = Math.max(1, Math.floor(diff / prev));
        const suffix = isTr ? ' once' : ' ago';
        return n + u.one + suffix;
      }
      prev = u.sec;
    }
    const years = Math.floor(diff / (86400 * 365));
    return isTr ? (years + 'y once') : (years + 'y ago');
  }
  function shortDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(+d)) return '—';
    const lang = currentLang();
    return d.toLocaleDateString(lang === 'tr' ? 'tr-TR' : 'en-US', { year: 'numeric', month: 'short', day: '2-digit' });
  }

  // -------------------- Fuse setup --------------------
  function buildFuse(items) {
    if (typeof Fuse === 'undefined') {
      state.fuse = null;
      return;
    }
    state.fuse = new Fuse(items, {
      threshold: 0.35,
      includeScore: true,
      ignoreLocation: true,
      keys: [
        { name: 'title',       weight: 2   },
        { name: 'description', weight: 1   },
        { name: 'tags',        weight: 1.5 },
        { name: 'services',    weight: 1.5 },
        { name: 'categories',  weight: 1   },
      ],
    });
  }

  // -------------------- Date threshold helper --------------------
  function dateThresholdMs() {
    const days = DATE_DAYS[state.dateFilter] || 0;
    if (!days) return null;
    return Date.now() - days * 86400000;
  }

  // -------------------- Search + filter computation --------------------
  function compute() {
    let result = state.items;
    const q = state.query.trim();
    if (q) {
      if (state.fuse) {
        result = state.fuse.search(q).map((x) => x.item);
      } else {
        // Fuse failed to load — naive substring fallback so search still works.
        const ql = q.toLowerCase();
        result = state.items.filter((it) =>
          (it.title || '').toLowerCase().includes(ql) ||
          (it.description || '').toLowerCase().includes(ql) ||
          (it.tags || []).some((tg) => tg.includes(ql)));
      }
    }
    if (state.filters.size) {
      // OR semantics: an item passes if it matches ANY selected filter.
      // (Previously AND — kept the "this AND that" intersection.)
      result = result.filter((it) => {
        const haystack = new Set([
          ...(it.categories || []),
          ...(it.services || []),
          ...(it.tags || []),
        ].map((s) => s.toLowerCase()));
        for (const f of state.filters) {
          if (haystack.has(f.toLowerCase())) return true;
        }
        return false;
      });
    }
    const since = dateThresholdMs();
    if (since !== null) {
      result = result.filter((it) => {
        const t = Date.parse(it.publishedAt);
        return Number.isFinite(t) && t >= since;
      });
    }
    return result;
  }

  // -------------------- All categories with counts (dropdown content) --------------------
  function allCategoriesWithCounts() {
    const counts = new Map();
    for (const it of state.items) {
      const seen = new Set();
      for (const c of [...(it.categories || []), ...(it.services || [])]) {
        if (!c || seen.has(c)) continue;
        seen.add(c);
        counts.set(c, (counts.get(c) || 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([name, count]) => ({ name, count }));
  }

  // -------------------- Renderers --------------------
  function renderSkeleton() {
    if (!els.grid) return;
    const cells = [];
    for (let i = 0; i < 9; i++) {
      cells.push(
        '<div class="news-skel">' +
          '<div class="news-skel-line s-meta"></div>' +
          '<div class="news-skel-line s-title"></div>' +
          '<div class="news-skel-line"></div>' +
          '<div class="news-skel-line"></div>' +
          '<div class="news-skel-line" style="width:70%"></div>' +
          '<div class="news-skel-tags"><span class="news-skel-line s-tag"></span><span class="news-skel-line s-tag"></span></div>' +
        '</div>'
      );
    }
    els.grid.innerHTML = cells.join('');
    if (els.empty) els.empty.hidden = true;
    if (els.error) els.error.hidden = true;
  }

  function renderHeader() {
    if (!state.feed) return;
    if (els.totalCount) els.totalCount.textContent = String(state.items.length);
    const newCount = state.items.filter((it) => it.isNew).length;
    if (els.newCount) els.newCount.textContent = String(newCount);
    if (els.newBadge) els.newBadge.hidden = newCount === 0;
    if (els.lastUpdated) {
      els.lastUpdated.textContent = state.feed.lastUpdated ? relativeTime(state.feed.lastUpdated) : '—';
      els.lastUpdated.title = state.feed.lastUpdated || '';
    }
  }

  // Render the multi-select checkbox list inside the Categories dropdown.
  function renderCatList() {
    if (!els.catList) return;
    const all = allCategoriesWithCounts();
    const ftext = state.catSearchText.trim().toLowerCase();
    const visible = ftext ? all.filter((c) => c.name.toLowerCase().includes(ftext)) : all;

    if (!visible.length) {
      els.catList.innerHTML = '<div class="news-dropdown-empty">' +
        escapeHtml(tr('news_no_categories', 'No categories found')) +
        '</div>';
    } else {
      // Partition: feed sources at the top, regular categories below.
      const feeds = visible.filter((c) => FEED_SOURCES.has(c.name));
      const rest  = visible.filter((c) => !FEED_SOURCES.has(c.name));
      // Feeds keep their own sort: by predefined order in FEED_SOURCES.
      const feedOrder = Array.from(FEED_SOURCES);
      feeds.sort((a, b) => feedOrder.indexOf(a.name) - feedOrder.indexOf(b.name));

      const renderRow = (c, isFeed) => {
        const checked = state.filters.has(c.name);
        const checkbox =
          '<input type="checkbox" data-cat="' + escapeHtml(c.name) + '"' + (checked ? ' checked' : '') + '>';
        const mark =
          '<span class="news-check-mark" aria-hidden="true">' +
            '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' +
          '</span>';
        const name =
          '<span class="news-check-name" title="' + escapeHtml(c.name) + '">' + escapeHtml(c.name) + '</span>';
        const count =
          '<span class="news-check-count">' + c.count + '</span>';
        const cls = 'news-check-row' + (checked ? ' is-checked' : '') + (isFeed ? ' is-feed' : '');
        if (isFeed) {
          // Feed rows: count sits immediately right of the feed icon so the
          // dropdown reads as "icon · count · name" on a single line.
          const icon = '<span class="news-check-feed-icon" aria-hidden="true">' + FEED_ICON_SVG + '</span>';
          return '<label class="' + cls + '">' + checkbox + mark + icon + count + name + '</label>';
        }
        return '<label class="' + cls + '">' + checkbox + mark + name + count + '</label>';
      };

      const buf = [];
      if (feeds.length) {
        buf.push('<div class="news-dropdown-section-label">' +
          escapeHtml(tr('news_feeds_label', 'Feeds')) + '</div>');
        for (const c of feeds) buf.push(renderRow(c, true));
        if (rest.length) {
          buf.push('<div class="news-dropdown-divider" role="separator"></div>');
          buf.push('<div class="news-dropdown-section-label">' +
            escapeHtml(tr('news_categories_section', 'Categories & Services')) + '</div>');
        }
      }
      for (const c of rest) buf.push(renderRow(c, false));
      els.catList.innerHTML = buf.join('');
    }

    // Footer info: selected/total
    if (els.catInfo) {
      const total = all.length;
      els.catInfo.textContent = state.filters.size
        ? state.filters.size + ' / ' + total
        : total + ' ' + tr('news_categories_total', 'categories');
    }

    // Button count badge
    if (els.catBtnCount) {
      if (state.filters.size > 0) {
        els.catBtnCount.hidden = false;
        els.catBtnCount.textContent = String(state.filters.size);
      } else {
        els.catBtnCount.hidden = true;
        els.catBtnCount.textContent = '';
      }
    }
    if (els.catBtn) els.catBtn.classList.toggle('is-active', state.filters.size > 0);

    // Clear all button (right-most)
    const total = state.filters.size + (state.dateFilter !== 'all' ? 1 : 0);
    if (els.activeCount) els.activeCount.textContent = total ? ' (' + total + ')' : '';
    if (els.clearFilters) els.clearFilters.hidden = total === 0;
  }

  // Sync the Date dropdown UI (button label + radio checked state).
  function syncDateUI() {
    const labels = {
      all:  tr('news_date_all',  'All dates'),
      '7d': tr('news_date_7d',   'Last 7 days'),
      '14d': tr('news_date_14d', 'Last 14 days'),
      '30d': tr('news_date_30d', 'Last 30 days'),
    };
    if (els.dateValue) els.dateValue.textContent = labels[state.dateFilter] || labels.all;
    if (els.dateBtn)   els.dateBtn.classList.toggle('is-active', state.dateFilter !== 'all');
    if (els.datePanel) {
      els.datePanel.querySelectorAll('input[type="radio"]').forEach((r) => {
        r.checked = (r.value === state.dateFilter);
      });
    }
  }

  // Render the active-filter pill row below the filter bar header.
  function renderActiveFilters() {
    if (!els.activeFilters) return;
    const buf = [];
    for (const f of state.filters) {
      const c = tagColor(f);
      const style =
        '--news-tag-bg:'     + c.bg + ';' +
        '--news-tag-fg:'     + c.fg + ';' +
        '--news-tag-border:' + c.bd + ';';
      buf.push(
        '<span class="news-active-pill" data-cat="' + escapeHtml(f) + '" style="' + style + '" title="' +
          escapeHtml(tr('news_remove_filter', 'Remove filter')) + '">' +
          escapeHtml(f) +
          '<span class="pill-x" aria-hidden="true">' +
            '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
          '</span>' +
        '</span>'
      );
    }
    if (state.dateFilter !== 'all') {
      const labels = {
        '7d': tr('news_date_7d', 'Last 7 days'),
        '14d': tr('news_date_14d', 'Last 14 days'),
        '30d': tr('news_date_30d', 'Last 30 days'),
      };
      buf.push(
        '<span class="news-active-pill is-date" data-date="' + state.dateFilter + '" title="' +
          escapeHtml(tr('news_remove_filter', 'Remove filter')) + '">' +
          '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
            '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>' +
          '</svg>' +
          escapeHtml(labels[state.dateFilter] || '') +
          '<span class="pill-x" aria-hidden="true">' +
            '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
          '</span>' +
        '</span>'
      );
    }
    els.activeFilters.innerHTML = buf.join('');
    els.activeFilters.hidden = buf.length === 0;
  }

  function renderGrid(visibleItems) {
    if (!els.grid) return;
    if (!visibleItems.length) {
      els.grid.innerHTML = '';
      renderEmpty();
      return;
    }
    if (els.empty) els.empty.hidden = true;

    const buf = [];
    const maxStagger = 14;
    for (let i = 0; i < visibleItems.length; i++) {
      const it = visibleItems[i];
      const delayMs = Math.min(i, maxStagger) * 28;
      // Service tags (max 4) at the bottom, deterministic-coloured.
      const serviceTags = (it.services && it.services.length ? it.services : (it.categories || []))
        .slice(0, 4);
      const tagsHtml = serviceTags
        .map((tg) => {
          const c = tagColor(tg);
          const style =
            '--news-tag-bg:'     + c.bg + ';' +
            '--news-tag-fg:'     + c.fg + ';' +
            '--news-tag-border:' + c.bd + ';';
          return '<span class="news-tag" style="' + style + '" data-filter="' + escapeHtml(tg) + '">' + escapeHtml(tg) + '</span>';
        })
        .join('');

      // Primary category pill — first category if present, else the first service.
      const headCategory = (it.categories && it.categories[0]) || (it.services && it.services[0]) || '';
      let headPillHtml = '';
      if (headCategory) {
        const c = tagColor(headCategory);
        const style =
          '--news-tag-bg:'     + c.bg + ';' +
          '--news-tag-fg:'     + c.fg + ';' +
          '--news-tag-border:' + c.bd + ';';
        headPillHtml =
          '<span class="news-card-cat" style="' + style + '" data-filter="' + escapeHtml(headCategory) + '">' +
            escapeHtml(headCategory) +
          '</span>';
      }

      buf.push(
        '<a class="news-card' + (it.isNew ? ' is-new' : '') + '" href="' + escapeHtml(it.url || '#') +
          '" target="_blank" rel="noopener noreferrer" style="animation-delay:' + delayMs + 'ms">' +
          '<div class="news-card-head">' +
            '<div class="news-card-head-left">' +
              (it.isNew
                ? '<span class="news-new-badge">' +
                    '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>' +
                    '<span>' + escapeHtml(tr('news_new_badge', 'NEW')) + '</span>' +
                  '</span>'
                : '') +
              headPillHtml +
            '</div>' +
            '<span class="news-card-date" title="' + escapeHtml(it.publishedAt || '') + '">' +
              '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
                '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>' +
              '</svg>' +
              escapeHtml(relativeTime(it.publishedAt)) +
            '</span>' +
          '</div>' +
          '<div class="news-card-title">' + escapeHtml(it.title || '') + '</div>' +
          (it.description ? '<div class="news-card-desc">' + escapeHtml(it.description) + '</div>' : '') +
          (tagsHtml ? '<div class="news-card-tags">' + tagsHtml + '</div>' : '') +
          '<div class="news-card-foot">' +
            '<span class="news-card-foot-date">' + escapeHtml(shortDate(it.publishedAt)) + '</span>' +
            '<span class="news-read-more">' +
              escapeHtml(tr('news_read_more', 'Read more')) +
              '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>' +
            '</span>' +
          '</div>' +
        '</a>'
      );
    }
    els.grid.innerHTML = buf.join('');
  }

  function renderEmpty() {
    if (!els.empty) return;
    const filtered = state.filters.size > 0 || state.query.trim().length > 0;
    const sub = filtered
      ? (state.query.trim() ? tr('news_empty_searched', 'Try a different search term.') : tr('news_empty_filtered', 'Try removing some filters to see more results.'))
      : tr('news_load_error_sub', 'Press Refresh to fetch the feed.');
    els.empty.innerHTML =
      '<div class="news-empty-icon">' +
        '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">' +
          '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/>' +
        '</svg>' +
      '</div>' +
      '<div class="news-empty-title">' + escapeHtml(tr('news_empty_title', 'No announcements found')) + '</div>' +
      '<div class="news-empty-sub">' + escapeHtml(sub) + '</div>' +
      (filtered
        ? '<button type="button" class="news-empty-action" id="newsEmptyClear">' +
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
            escapeHtml(tr('news_empty_clear_all', 'Clear all filters')) +
          '</button>'
        : '');
    els.empty.hidden = false;
    const btn = document.getElementById('newsEmptyClear');
    if (btn) btn.addEventListener('click', resetAll);
  }

  function renderError(msg) {
    if (!els.error) return;
    els.error.innerHTML =
      '<div class="news-error-icon">' +
        '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>' +
      '</div>' +
      '<div class="news-error-title">' + escapeHtml(tr('news_load_error_title', 'Failed to load data')) + '</div>' +
      '<div class="news-error-sub">' + escapeHtml(msg || tr('news_load_error_sub', 'Press Refresh to fetch the feed.')) + '</div>' +
      '<button type="button" class="news-error-action" id="newsErrorRefresh">' +
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>' +
        escapeHtml(tr('news_refresh', 'Refresh Feed')) +
      '</button>';
    els.error.hidden = false;
    if (els.grid) els.grid.innerHTML = '';
    if (els.empty) els.empty.hidden = true;
    const btn = document.getElementById('newsErrorRefresh');
    if (btn) btn.addEventListener('click', triggerRefresh);
  }

  function renderResultCount(n) {
    if (els.resultCount) {
      if (state.query.trim() || state.filters.size) {
        els.resultCount.hidden = false;
        const word = tr('news_results', 'results');
        const ofw  = tr('news_items_of', 'of');
        els.resultCount.textContent = n + ' ' + word + ' ' + ofw + ' ' + state.items.length;
      } else {
        els.resultCount.hidden = true;
        els.resultCount.textContent = '';
      }
    }
    if (els.itemsCount) {
      const items = tr('news_items_total', 'announcements');
      els.itemsCount.textContent = state.items.length + ' ' + items;
    }
  }

  function renderAll() {
    renderHeader();
    renderCatList();
    syncDateUI();
    renderActiveFilters();
    const visible = compute();
    renderGrid(visible);
    renderResultCount(visible.length);
    if (els.searchClear) els.searchClear.hidden = !state.query;
  }

  // -------------------- Actions --------------------
  function setQuery(v) {
    state.query = v || '';
    renderAll();
  }
  function toggleFilter(name) {
    if (state.filters.has(name)) state.filters.delete(name);
    else state.filters.add(name);
    renderAll();
  }
  function clearFilters() {
    state.filters.clear();
    state.dateFilter = 'all';
    renderAll();
  }
  function resetAll() {
    state.filters.clear();
    state.dateFilter = 'all';
    state.query = '';
    state.catSearchText = '';
    if (els.search)    els.search.value = '';
    if (els.catSearch) els.catSearch.value = '';
    renderAll();
  }
  function setDateFilter(value) {
    if (DATE_DAYS[value] === undefined) return;
    state.dateFilter = value;
    renderAll();
  }
  function removeFilter(name) {
    state.filters.delete(name);
    renderAll();
  }

  // -------------------- Dropdown helpers --------------------
  function openDropdown(kind) {
    closeDropdowns(kind);
    const dd = kind === 'cat' ? els.catDropdown : els.dateDropdown;
    if (!dd) return;
    dd.classList.add('is-open');
    const btn = dd.querySelector('.news-dropdown-btn');
    if (btn) btn.setAttribute('aria-expanded', 'true');
    state.openDropdown = kind;
    if (kind === 'cat' && els.catSearch) {
      // Defer focus until after the panel is visible.
      setTimeout(() => els.catSearch.focus(), 0);
    }
  }
  function closeDropdowns(except) {
    document.querySelectorAll('.news-dropdown.is-open').forEach((dd) => {
      if (except && dd.dataset.kind === except) return;
      dd.classList.remove('is-open');
      const btn = dd.querySelector('.news-dropdown-btn');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
    if (!except) state.openDropdown = null;
    else state.openDropdown = except;
  }
  function toggleDropdown(kind) {
    const dd = kind === 'cat' ? els.catDropdown : els.dateDropdown;
    if (!dd) return;
    if (dd.classList.contains('is-open')) closeDropdowns();
    else openDropdown(kind);
  }

  // -------------------- Wire up events --------------------
  let debounceTimer = null;
  function wireEvents() {
    if (els.search) {
      els.search.addEventListener('input', (e) => {
        if (debounceTimer) clearTimeout(debounceTimer);
        const v = e.target.value;
        debounceTimer = setTimeout(() => setQuery(v), 180);
      });
    }
    if (els.searchClear) {
      els.searchClear.addEventListener('click', () => {
        if (els.search) { els.search.value = ''; els.search.focus(); }
        setQuery('');
      });
    }
    if (els.grid) {
      els.grid.addEventListener('click', (e) => {
        const tag = e.target.closest('.news-tag, .news-card-cat');
        if (!tag || !tag.dataset.filter) return;
        e.preventDefault();
        e.stopPropagation();
        toggleFilter(tag.dataset.filter);
      });
    }
    if (els.clearFilters) {
      els.clearFilters.addEventListener('click', clearFilters);
    }

    // ---- Categories dropdown wiring ----
    if (els.catBtn) {
      els.catBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleDropdown('cat');
      });
    }
    if (els.catPanel) {
      // Clicks inside the panel must not bubble to the document-level outside handler.
      els.catPanel.addEventListener('click', (e) => e.stopPropagation());
    }
    if (els.catSearch) {
      els.catSearch.addEventListener('input', (e) => {
        state.catSearchText = e.target.value;
        renderCatList();
      });
      // Suppress Esc here so we close the dropdown without clearing the main search.
      els.catSearch.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          e.stopPropagation();
          closeDropdowns();
          if (els.catBtn) els.catBtn.focus();
        }
      });
    }
    if (els.catList) {
      els.catList.addEventListener('change', (e) => {
        const cb = e.target.closest('input[type="checkbox"]');
        if (!cb) return;
        const name = cb.dataset.cat;
        if (!name) return;
        if (cb.checked) state.filters.add(name);
        else state.filters.delete(name);
        renderAll();
      });
    }
    if (els.catClear) {
      els.catClear.addEventListener('click', (e) => {
        e.stopPropagation();
        state.filters.clear();
        renderAll();
      });
    }

    // ---- Date dropdown wiring ----
    if (els.dateBtn) {
      els.dateBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleDropdown('date');
      });
    }
    if (els.datePanel) {
      els.datePanel.addEventListener('click', (e) => e.stopPropagation());
      els.datePanel.addEventListener('change', (e) => {
        const r = e.target.closest('input[type="radio"]');
        if (!r) return;
        setDateFilter(r.value);
        // Auto-close shortly after for snappy feedback.
        setTimeout(() => closeDropdowns(), 120);
      });
    }

    // ---- Active filter pill row: click X to remove that filter ----
    if (els.activeFilters) {
      els.activeFilters.addEventListener('click', (e) => {
        const pill = e.target.closest('.news-active-pill');
        if (!pill) return;
        if (pill.dataset.cat)        removeFilter(pill.dataset.cat);
        else if (pill.dataset.date)  setDateFilter('all');
      });
    }

    // ---- Click outside any dropdown closes them ----
    document.addEventListener('click', () => {
      if (state.openDropdown) closeDropdowns();
    });
    if (els.refreshBtn) {
      els.refreshBtn.addEventListener('click', (e) => {
        e.preventDefault();
        triggerRefresh(e.shiftKey);
      });
    }
    // The "Last updated" pill is a click-to-refresh trigger.
    // - Plain click  → normal refresh (server may serve cached if mtime < 5min)
    // - Shift+click  → force-refresh (?force=1 bypasses the freshness TTL)
    if (els.updatedStat) {
      els.updatedStat.addEventListener('click', (e) => {
        e.preventDefault();
        triggerRefresh(e.shiftKey);
      });
    }

    // Keyboard shortcuts: Cmd/Ctrl+K → focus search; Esc → close dropdowns or clear search.
    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        if (els.search) { els.search.focus(); els.search.select(); }
      } else if (e.key === 'Escape') {
        if (state.openDropdown) {
          closeDropdowns();
          return;
        }
        if (document.activeElement === els.search) {
          if (els.search) {
            els.search.value = '';
            els.search.blur();
          }
          setQuery('');
        }
      }
    });

    // Re-render when theme or language changes (refreshes all i18n strings + dates).
    document.addEventListener('themechange',  renderAll);
    document.addEventListener('langchange',   renderAll);
  }

  // -------------------- API calls --------------------
  async function loadFeed() {
    try {
      const res = await fetch('/news/api/feed', { headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      if (!data || data.status === 'error') throw new Error((data && data.error) || 'Unknown error');
      state.feed  = data;
      state.items = Array.isArray(data.items) ? data.items : [];
      buildFuse(state.items);
      if (els.error) els.error.hidden = true;
      renderAll();
    } catch (err) {
      renderError(err && err.message ? err.message : String(err));
    }
  }

  async function triggerRefresh(force) {
    if (state.refreshing) return;
    state.refreshing = true;

    // Sidebar button: text label + spinner via .is-loading
    if (els.refreshBtn) {
      els.refreshBtn.classList.add('is-loading');
      const lbl = els.refreshBtn.querySelector('.nav-label');
      if (lbl) lbl.textContent = tr('news_refreshing', 'Refreshing...');
    }
    // "Last updated" pill: spin icon
    if (els.updatedStat) {
      els.updatedStat.classList.add('is-refreshing');
      els.updatedStat.classList.remove('is-fresh-flash');
    }

    try {
      const url = '/news/api/refresh' + (force ? '?force=1' : '');
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
      });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data || data.status === 'error') {
        const msg = (data && data.error) || ('HTTP ' + res.status);
        renderError(msg);
        return;
      }
      // refreshed === false → cache hit (mtime < FRESH_TTL); still refresh UI.
      const wasRefreshed = !!data.refreshed;
      await loadFeed();

      // Brief green flash + tooltip update so the user gets feedback.
      if (els.updatedStat) {
        els.updatedStat.classList.add('is-fresh-flash');
        els.updatedStat.title = wasRefreshed
          ? tr('news_just_refreshed', 'Fresh data fetched')
          : tr('news_already_fresh',  'Feed already fresh');
        setTimeout(() => {
          els.updatedStat.classList.remove('is-fresh-flash');
          // Restore the click-to-refresh hint after the flash
          els.updatedStat.title = tr('news_last_updated_hint',
            'Click to refresh • Shift-click to force a fresh fetch');
        }, 1400);
      }
    } catch (err) {
      renderError(err && err.message ? err.message : String(err));
    } finally {
      state.refreshing = false;
      if (els.refreshBtn) {
        els.refreshBtn.classList.remove('is-loading');
        const lbl = els.refreshBtn.querySelector('.nav-label');
        if (lbl) lbl.textContent = tr('news_refresh', 'Refresh Feed');
      }
      if (els.updatedStat) {
        els.updatedStat.classList.remove('is-refreshing');
      }
    }
  }

  // -------------------- Init --------------------
  function init() {
    if (!els.grid) return;
    // Show platform-correct shortcut hint.
    if (els.kbdHint) {
      const isMac = /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent || '');
      els.kbdHint.textContent = isMac ? '⌘K' : 'Ctrl+K';
    }
    renderSkeleton();
    wireEvents();
    loadFeed();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
