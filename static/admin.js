/* Aggregate-only owner overview. No analytics SDK, local storage or raw records. */
(() => {
  'use strict';
  const number = value => Number.isFinite(value) ? new Intl.NumberFormat('en-US').format(value) : '—';
  const percent = value => Number.isFinite(value) ? `${new Intl.NumberFormat('en-US', {maximumFractionDigits: 1}).format(value)}%` : '—';
  const duration = ms => Number.isFinite(ms) ? `${new Intl.NumberFormat('en-US', {maximumFractionDigits: 1}).format(ms / 1000)}s` : '—';
  const date = day => new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', timeZone: 'UTC'}).format(new Date(`${day}T12:00:00Z`));
  const timestamp = value => value ? new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/Los_Angeles'}).format(new Date(value)) + ' PT' : 'No events yet';
  const names = {tarot: 'Tarot', runes: 'Runes', iching: 'I Ching', number: 'Numerology', oracle: 'Oracle', unknown: 'Unknown'};
  const modeName = value => names[value] || value;
  const environmentName = value => ({production: 'Production', preview: 'Preview', local: 'Local', test: 'Test', staging: 'Staging', development: 'Development'}[value] || 'Unknown');
  const $ = id => document.getElementById(id);
  const set = (id, value) => { $(id).textContent = value; };
  const element = (tag, text, className) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; };
  const svg = (tag, attributes, text) => { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value))); if (text !== undefined) node.textContent = text; return node; };
  function row(values) { const node = element('tr'); values.forEach(value => node.append(element('td', value))); return node; }
  function emptyRow(body, columns, message) { const cell = element('td', message, 'empty'); cell.colSpan = columns; const r = element('tr'); r.append(cell); body.append(r); }
  function renderDaily(days, firstObserved) {
    const chart = $('daily-chart'), body = $('daily-table'); chart.replaceChildren(); body.replaceChildren();
    const width = Math.max(300, Math.min(650, window.innerWidth - 80)), height = 210, left = 34, right = 8, top = 14, bottom = 30;
    const plotWidth = width - left - right, plotHeight = height - top - bottom;
    const coverageDay = firstObserved ? new Intl.DateTimeFormat('en-CA', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'America/Los_Angeles'}).format(new Date(firstObserved)) : null;
    const max = Math.max(1, ...days.map(day => day.completed_readings));
    const ceiling = max <= 4 ? 4 : Math.ceil(max / 4) * 4;
    const root = svg('svg', {viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-labelledby': 'daily-chart-title daily-chart-desc'});
    root.append(svg('title', {id: 'daily-chart-title'}, 'Completed readings by Pacific calendar day'));
    root.append(svg('desc', {id: 'daily-chart-desc'}, `${days.reduce((sum, day) => sum + day.completed_readings, 0)} completed readings. Today's bar is purple and covers a partial day. Exact values are in View daily counts.`));
    for (let i = 0; i <= 4; i++) { const y = top + plotHeight * i / 4; root.append(svg('line', {x1: left, x2: width - right, y1: y, y2: y, class: 'gridline'})); root.append(svg('text', {x: left - 9, y: y + 4, 'text-anchor': 'end'}, number(ceiling * (4 - i) / 4))); }
    const slot = plotWidth / Math.max(1, days.length), barWidth = Math.min(36, slot * .52);
    days.forEach((day, index) => {
      const x = left + slot * (index + .5), barHeight = day.completed_readings / ceiling * plotHeight;
      const mark = day.completed_readings ? svg('rect', {x: x - barWidth / 2, y: top + plotHeight - barHeight, width: barWidth, height: barHeight, rx: 2, class: index === days.length - 1 ? 'bar today' : 'bar'}) : svg('circle', {cx: x, cy: top + plotHeight, r: 2, class: 'zero-dot'});
      const beforeCoverage = !coverageDay || day.date < coverageDay;
      mark.append(svg('title', {}, beforeCoverage ? `${date(day.date)}: before observed coverage` : `${date(day.date)}: ${number(day.completed_readings)} readings`)); if (!beforeCoverage) root.append(mark);
      if (days.length <= 8 || index === 0 || index === days.length - 1 || (index % 5 === 0 && index < days.length - 3)) root.append(svg('text', {x, y: height - 8, 'text-anchor': 'middle'}, date(day.date)));
      body.append(row([`${date(day.date)}${index === days.length - 1 ? ' · partial day' : ''}`, beforeCoverage ? 'No coverage' : number(day.completed_readings), beforeCoverage ? 'No coverage' : number(day.linked_active_browsers)]));
    });
    chart.append(root);
  }
  function renderModes(modes, spreads) {
    const bars = $('mode-bars'), table = $('spread-table'); bars.replaceChildren(); table.replaceChildren();
    const total = modes.reduce((sum, item) => sum + item.completed_readings, 0);
    if (!total) bars.append(element('p', 'No completed readings in this period.', 'empty'));
    modes.forEach(item => {
      const wrap = element('div', undefined, 'mode-row'), label = element('div');
      label.append(element('span', modeName(item.mode)), element('span', `${number(item.completed_readings)} · ${percent(100 * item.completed_readings / total)}`, 'mode-value'));
      const track = element('div', undefined, 'mode-track'), picture = svg('svg', {viewBox: '0 0 100 5', preserveAspectRatio: 'none', 'aria-hidden': 'true'});
      picture.append(svg('rect', {x: 0, y: 0, width: 100 * item.completed_readings / total, height: 5, rx: 2, fill: '#b5a1d2'})); track.append(picture); wrap.append(label, track); bars.append(wrap);
    });
    spreads.forEach(item => table.append(row([`${modeName(item.mode)} · ${item.spread}`, number(item.completed_readings)])));
    if (!spreads.length) emptyRow(table, 2, 'No spread data yet.');
  }
  let displayedReport = null;
  function render(report) {
    displayedReport = report;
    const {totals, coverage, latency_ms: latency, qrng, tokens} = report;
    set('completed', number(totals.completed_readings)); set('browsers', number(totals.linked_active_browsers)); set('completion-rate', percent(totals.completion_rate_percent)); set('median', duration(latency.median));
    set('completion-note', totals.logical_starts_eligible ? `${number(totals.logical_starts_completed)} of ${number(totals.logical_starts_eligible)} eligible starts · recent 15 min excluded` : 'No eligible starts yet · recent 15 min excluded');
    set('latency-note', latency.completed_attempts ? `95th percentile: ${duration(latency.p95)} · ${number(latency.completed_attempts)} timed attempts` : 'No completed attempts with timing yet');
    set('chart-range', `${date(report.window.start_local_date)} – ${date(report.window.end_local_date)} · Today is a partial day`);
    renderDaily(report.daily, coverage.earliest_retained_event_at); renderModes(report.popularity.modes, report.popularity.spreads);
    set('attempt-total', `${number(totals.attempts.total)} attempts`); $('outcomes').replaceChildren();
    ['completed', 'failed', 'interrupted', 'pending', 'unresolved'].forEach(key => { const wrap = element('div', undefined, 'outcome'), label = element('span', undefined, 'outcome-label'); label.append(element('i', undefined, `status-dot ${key}`), document.createTextNode(key[0].toUpperCase() + key.slice(1))); wrap.append(label, element('strong', number(totals.attempts[key]))); $('outcomes').append(wrap); });
    set('fallback', percent(qrng.fallback_batch_percent)); set('fallback-note', `${number(qrng.batches_with_fallback)} of ${number(qrng.batches)} recorded draw batches used fallback`); set('fallback-values', number(qrng.fallback_values));
    set('usage-coverage', `${number(tokens.calls)} usage records`); $('token-table').replaceChildren();
    tokens.by_model.forEach(item => $('token-table').append(row([item.model, number(item.calls), ...['input_tokens', 'output_tokens', 'thinking_tokens', 'cached_tokens', 'total_tokens'].map(key => item.reported_counts && item.reported_counts[key] > 0 ? `${number(item[key])}${item.reported_counts[key] < item.calls ? '*' : ''}` : '—')])));
    if (!tokens.by_model.length) emptyRow($('token-table'), 7, 'No reported model usage in this period.');
    set('tokens-note', `${number(tokens.calls_with_reported_tokens)} records include token values; ${number(tokens.calls_missing_reported_tokens)} have no token values. These are reported totals, not all generation costs. * marks a partial total where some records lack that field. A dash means no reported values. Token categories may overlap and should not be added together.`);
    const first = coverage.earliest_retained_event_at;
    set('coverage-text', first ? `Retained public data begins ${timestamp(first)}. Latest event: ${timestamp(coverage.latest_event_at)}. ${number(coverage.window_event_count)} events in this window. Days before observed coverage are unknown, not zero activity. Quiet periods and collection failures can both produce gaps.` : 'No public events have been collected yet. Empty charts are expected until people use Oracle.');
    set('anonymous-note', `${number(totals.completed_without_visitor_id)} completed readings have no linked browser ID. ${environmentName(report.environment)} public traffic only; test and internal events excluded.`);
    set('load-status', `Updated ${timestamp(report.generated_at)} · ${environmentName(report.environment)} data`);
    $('report').hidden = false; $('report').setAttribute('aria-busy', 'false');
  }
  let current = ['today', '7d', '30d'].includes(new URLSearchParams(location.search).get('period')) ? new URLSearchParams(location.search).get('period') : '7d';
  let requestSequence = 0, controller;
  async function load(period) {
    displayedReport = null; current = period; const sequence = ++requestSequence; if (controller) controller.abort(); controller = new AbortController(); const activeController = controller;
    const timeout = setTimeout(() => activeController.abort(), 20000);
    document.querySelectorAll('[data-period]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.period === period)));
    $('report').hidden = true; $('report').setAttribute('aria-busy', 'true'); $('error').hidden = true; $('refresh').disabled = true; set('load-status', 'Loading usage…');
    try {
      const response = await fetch(`/admin/api/report?period=${encodeURIComponent(period)}`, {credentials: 'same-origin', cache: 'no-store', signal: activeController.signal});
      if (response.status === 401 || response.status === 403) throw new Error('session');
      if (!response.ok) throw new Error('unavailable');
      const report = await response.json(); if (sequence !== requestSequence) return;
      if (report.status !== 'ok' || report.schema_version !== 1 || report.period !== period) throw new Error('unavailable');
      render(report); history.replaceState(null, '', `/admin?period=${encodeURIComponent(period)}`);
    } catch (error) {
      if (sequence !== requestSequence) return;
      $('report').hidden = true; $('error').replaceChildren();
      if (error.message === 'session') { $('error').append(document.createTextNode('Your owner session has ended. ')); const link = element('a', 'Sign in again'); link.href = '/admin'; $('error').append(link); }
      else $('error').textContent = 'Usage data could not be loaded. Try Refresh in a moment. Readings on Oracle are unaffected.';
      $('error').hidden = false; set('load-status', 'Data unavailable · no totals shown');
    } finally { clearTimeout(timeout); if (sequence === requestSequence) $('refresh').disabled = false; }
  }
  document.querySelectorAll('[data-period]').forEach(button => button.addEventListener('click', () => load(button.dataset.period)));
  $('refresh').addEventListener('click', () => load(current));
  window.addEventListener('resize', () => { if (displayedReport) renderDaily(displayedReport.daily, displayedReport.coverage.earliest_retained_event_at); });
  load(current);
})();
