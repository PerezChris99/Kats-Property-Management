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

test('role dashboards have operational hierarchy and no presentation walkthrough', () => {
  const app = read('src/App.jsx');
  const analytics = read('src/charts/WorkspaceAnalytics.jsx');
  const style = read('src/dashboard-polish.css');
  const nav = read('src/WorkspaceNavigation.jsx');
  assert.equal(app.includes('PresentationTour'), false, 'no walkthrough shown at top');
  assert.ok(app.includes('kats-flow-label') && app.includes('kats-action-grid'));
  assert.ok(app.includes('kats-tenant-money-panel'), 'tenant rent gets emphasis');
  assert.ok(analytics.includes('<ChartDisclosure'), 'secondary charts fold on demand');
  assert.ok(analytics.includes('setVisited(true)'), 'secondary queries load when opened');
  assert.ok(style.includes('--dash-glass:'), 'subtle translucent layering');
  assert.ok(style.includes('prefers-reduced-motion'), 'motion accessibility');
  assert.ok(nav.includes('kats-nav-group-toggle'), 'labeled collapsible navigation');
  assert.ok(nav.includes('PAGE_META[page]?.icon'), 'icons for every supported route');
});

test('command palette respects route permissions and the workspace shares its install control', () => {
  const app = read('src/App.jsx');
  const command = read('src/QuickActionsPalette.jsx');
  const install = read('src/PwaInstallButton.jsx');
  const manifest = JSON.parse(read('public/manifest.webmanifest'));
  assert.ok(app.includes('<QuickActionsPalette pages={nav}/>'));
  assert.ok(command.includes('event.metaKey') && command.includes('event.ctrlKey'));
  assert.ok(command.includes("api('workspace/search?q='"), 'server authorizes record results');
  assert.ok(command.includes('allowed.includes(item.path.slice(1))'), 'local role-based route list');
  assert.ok(command.includes('createPortal('), 'modal escapes header blur');
  assert.ok(command.includes('aria-modal="true"') && command.includes('Escape'));
  assert.ok(app.includes('<PwaInstallButton/>'), 'all signed-in workspaces share the install control');
  assert.ok(install.includes('beforeinstallprompt'));
  assert.equal(manifest.start_url, '/dashboard');
  assert.equal(manifest.display, 'standalone');
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
