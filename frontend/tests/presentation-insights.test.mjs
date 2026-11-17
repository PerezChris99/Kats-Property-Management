import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = file => readFileSync(new URL('../' + file, import.meta.url), 'utf8');

test('financial KPIs and finance charts use one authenticated report window', () => {
  const dash = read('src/charts/WorkspaceAnalytics.jsx');
  const shared = read('src/charts/PresentationControls.jsx');
  assert.ok(dash.includes('<PeriodDashboard>'), 'both dashboards use reporting control');
  assert.ok(dash.includes('periodView={view}'), 'actual financial series come from same response');
  assert.ok(dash.includes('financialChartData(endpoint, periodView.data)'));
  assert.ok(shared.includes("api('analytics/period-summary?'"), 'server-aggregated shared fetch');
  assert.ok(shared.includes('previous'), 'prior-period comparison is visible');
  assert.ok(shared.includes("months, end_month: endMonth"), 'a single dates selection for KPIs and plots');
  assert.ok(shared.includes('kats:data-updated'), 'dashboard refreshes on successful mutations');
  assert.ok(shared.includes('visibilitychange'), 'stale tab data refreshed');
  assert.ok(shared.includes('generated_at'), 'server generation time, not simulated live data');
  assert.ok(shared.includes('period-summary.pdf?') && shared.includes('period-summary.xlsx?'));
  assert.ok(shared.includes('financialChartData'), 'financial charts mapped from one source');
  assert.equal(shared.includes('Math.random('), false, 'no random reporting numbers');
});

test('chart source records are authenticated, accessible and real vector exports exist', () => {
  const dash = read('src/charts/WorkspaceAnalytics.jsx');
  const charts = read('src/charts/ChartKit.jsx');
  assert.ok(dash.includes("api('analytics/drilldown?'"), 'record clickthrough requests from API');
  assert.ok(dash.includes('RECORD_ROUTES'), 'only whitelisted internal record routes');
  assert.ok(dash.includes('Explore source records'), 'keyboard/touch alternative to chart clicks');
  assert.ok(dash.includes('Download SVG'), 'individual chart export');
  assert.ok(charts.includes('onSelect?.('), 'clickable real plot shapes');
  assert.ok(charts.includes('<Tooltip'), 'native tooltip remains');
});

test('presentation guide cannot leak synthetic credentials into live deployment', () => {
  const guide = read('src/PresentationTour.jsx');
  const app = read('src/App.jsx');
  assert.ok(guide.includes('import.meta.env.DEV'), 'guide is dev-only');
  assert.ok(guide.includes('window.location.hostname'), 'guide restricted to local loopback');
  assert.ok(guide.includes('OWNER:') && guide.includes('ACCOUNTANT:') &&
    guide.includes('TENANT:') && guide.includes('CARETAKER:'), 'guided account roles');
  assert.ok(app.includes('<PresentationTour role={user.role}/>'));
  assert.ok(app.includes('<PresentationTour role="TENANT"/>'));
  assert.ok(app.includes('<PresentationTour role="CARETAKER"/>'));
  assert.equal(guide.includes('localStorage'), false, 'no persistent account state');
});

test('private completed data is not cached and staging load is gated', () => {
  const api = read('src/lib/api.js');
  const load = read('../ops/load-workspace.js');
  assert.ok(api.includes("cache: 'no-store'"));
  assert.ok(api.includes("kats:data-updated"));
  assert.ok(api.includes("inflight.delete(key)"), 'pending coalescing always cleared');
  assert.ok(load.includes('KATS_LOAD_TEST_APPROVED'));
  assert.ok(load.includes('KATS_STAGING_PROFILE'));
  assert.ok(load.includes('KATS_STAGING_VUS'));
  assert.ok(load.includes('[25,50,100]'));
});
