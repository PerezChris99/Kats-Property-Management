import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = path => readFileSync(new URL('../'+path, import.meta.url), 'utf8');

test('all dashboard charts use one lazily imported visualization toolkit with live endpoints', () => {
  const app=read('src/App.jsx');
  const analytics=read('src/charts/WorkspaceAnalytics.jsx');
  const kit=read('src/charts/ChartKit.jsx');
  const annual=read('src/AnnualTrendsPage.jsx');
  assert.ok(app.includes("lazy(() => import('./charts/WorkspaceAnalytics')"));
  assert.ok(app.includes('<LandlordAnalytics />'));
  assert.ok(app.includes('<TenantAnalytics />'));
  assert.ok(analytics.includes("api(endpoint,{signal:controller.signal})"));
  assert.ok(analytics.includes("new AbortController()"));
  assert.ok(analytics.includes("role=\"status\""));
  assert.ok(analytics.includes("role=\"alert\""));
  assert.ok(analytics.includes("setRevision(v=>v+1)"));
  for (const endpoint of [
    'analytics/landlord/occupancy','analytics/landlord/collections-by-property',
    'analytics/landlord/monthly','analytics/landlord/tenant-overlap',
    'analytics/landlord/property-scores',
    'analytics/tenant/payment-status','analytics/tenant/applied-payments',
    'analytics/tenant/balance-trend'
  ]) assert.ok(analytics.includes(endpoint),endpoint);
  for (const kind of ['DonutChart','PieChart','BarChart','LineChart','AreaChart','ComparisonBarChart','VennChart','PropertyPerformanceChart']) {
    assert.ok(kit.includes('export function '+kind+'('),kind);
  }
  assert.ok(annual.includes("from './charts/ChartKit'"));
  assert.equal(annual.includes('<svg'),false);
  const pkg=JSON.parse(read('package.json'));
  assert.ok(pkg.dependencies.recharts,'Recharts is the one charting library');
  assert.ok(pkg.dependencies['react-is'],'Recharts React 19 peer support');
  assert.equal(/chart.js|react-chartjs-2|upsetjs/i.test(read('package.json')),false);
  assert.ok(kit.includes("from 'recharts'"),'all chart primitives use Recharts');
  assert.ok(kit.includes('<ResponsiveContainer'), 'responsive charts use literal Recharts container');
  assert.ok(kit.includes('<Tooltip'), 'native chart tooltips available');
  assert.ok(kit.includes('<Legend'), 'native chart legends available');
  assert.ok(kit.includes('<RechartsPieChart') &&
            kit.includes('<RechartsBarChart') &&
            kit.includes('<RechartsLineChart') &&
            kit.includes('<RechartsAreaChart'), 'all visual types are Recharts');
  assert.equal(kit.includes('<RechartsRadarChart'), false, 'misleading circular radar removed');
  assert.ok(kit.includes('domain={[0, 100]}'), 'property rates use comparable 0-100% axis');
  assert.ok(kit.includes('secondary'), 'collections and invoicing stay distinct');
  assert.ok(analytics.includes('kind="performance"'), 'staff property scores use true comparison bars');
  assert.ok(analytics.includes('kind="monthly-line"'), 'staff collections are time series');
  assert.ok(analytics.includes('analytics/tenant/payment-history'), 'tenant gets verified settlement history');
  assert.ok(analytics.includes('<PieChart') && analytics.includes('<DonutChart'), 'distribution toggles');
  assert.ok(analytics.includes('<ComparisonBarChart'), 'monthly billing and collections compare correctly');
  assert.ok(analytics.includes('setMode(') && analytics.includes('setRange('),
    'chart type and rolling period controls are interactive');
  assert.ok(annual.includes('setCollectionStyle(') && annual.includes('setMonthsToShow('),
    'annual collection trend is switchable between real graph types');
  assert.ok(annual.includes('<LineChart') && annual.includes('<AreaChart') &&
    annual.includes('<BarChart'), 'annual reports render real Cartesian charts');
});

test('workspace sizing tokens are 14px base with 12-col responsive layout',()=>{
  const css=read('src/workspace.css');
  const main=read('src/main.jsx');
  assert.ok(main.includes("import './workspace.css'"));
  for(const entry of [
    '--font-size-xs: 11px','--font-size-sm: 12px','--font-size-base: 14px',
    '--font-size-lg: 16px','--font-size-xl: 20px','--font-size-2xl: 24px',
    '--control-height: 32px','--control-height-sm: 28px',
    '--chart-height: 310px','--content-max: 1392px'
  ]) assert.ok(css.includes(entry),entry);
  for(let i=1;i<=8;i++)assert.ok(css.includes('--space-'+i+': '+(4*i)+'px'));
  assert.ok(css.includes('grid-template-columns:repeat(12,minmax(0,1fr))'));
  for (const n of ['640','768','1024','1280'])
    assert.ok(css.includes('(max-width:'+n+'px)'),n);
});

test('router has functional error recovery and an actual 404 route',()=>{
  const main=read('src/main.jsx');
  const route=read('src/RouteFailure.jsx');
  const app=read('src/App.jsx');
  assert.ok(main.includes('createBrowserRouter('));
  assert.ok(main.includes('errorElement: <RouteFailure />'));
  assert.ok(route.includes('export function RouteFailure()'));
  assert.ok(route.includes('useRouteError()'));
  assert.ok(route.includes('export function NotFoundPage()'));
  assert.ok(app.includes('<Route path="*" element={<NotFoundPage/>}/>'));
  assert.equal(route.includes('class RouteFailure'),false);
});


test('lazy module selectors match actual export kinds (including utilities)',()=>{
  const app=read('src/App.jsx');
  const modules=[
    ['UtilitiesPage','default'],
    ['PrivacyRequestsPage','default'],
    ['DisputesPage','default'],
    ['PreventiveMaintenancePage','default'],
    ['ProrationPage','named'],
    ['AnnualTrendsPage','named'],
    ['PortfolioEditPage','named'],
    ['ExpenseApprovalsPage','named']
  ];
  for (const [component,kind] of modules) {
    const source=read('src/'+component+'.jsx');
    if(kind==='default') {
      assert.ok(source.includes('export default function '+component),component);
      assert.ok(app.includes("lazy(() => import('./"+component+"'))"),component);
    } else {
      assert.ok(source.includes('export function '+component),component);
      assert.ok(app.includes("lazy(() => import('./"+component+"').then(m => ({ default: m."+component+" })))"),component);
    }
  }
});


test('chart CSS reserves real graph height and does not shrink the SVG', () => {
  const css = read('src/workspace.css');
  assert.ok(css.includes('.kats-recharts-frame svg.recharts-surface'));
  assert.ok(css.includes('max-height:none'), 'plot cannot be clipped to a decorative icon');
  assert.equal(/svg\.recharts-surface\s*\{[^}]*width:\s*100%/s.test(css), false,
    'do not override Recharts SVG width with a percentage');
  assert.ok(css.includes('.kats-chart-controls'), 'management and tenant selectors are styled');
  assert.ok(css.includes('@media (max-width:640px)'), 'narrow device layout remains responsive');
});

test('all staff and tenant chart controls use real API data, not display-only placeholders', () => {
  const source = read('src/charts/WorkspaceAnalytics.jsx');
  assert.ok(source.includes("api(endpoint,{signal:controller.signal})"));
  assert.ok(source.includes("const plotted = TIME_SERIES.has(kind)"), 'changing range selects source points');
  assert.ok(source.includes("onChange={event => setMode(event.target.value)}"));
  assert.ok(source.includes("onChange={event => setRange(event.target.value)}"));
  assert.ok(source.includes('PropertyPerformanceChart'));
  assert.ok(source.includes('TenantAnalytics()') && source.includes('LandlordAnalytics()'));
  assert.equal(/const sampleData|Math\.random\(|demoChartData/.test(source), false);
});
