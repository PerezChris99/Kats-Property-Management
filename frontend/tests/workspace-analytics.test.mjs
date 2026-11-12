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
  for (const kind of ['DonutChart','BarChart','LineChart','VennChart','RadarChart']) {
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
            kit.includes('<RechartsRadarChart'), 'all visual types are Recharts');
});

test('workspace sizing tokens are 14px base with 12-col responsive layout',()=>{
  const css=read('src/workspace.css');
  const main=read('src/main.jsx');
  assert.ok(main.includes("import './workspace.css'"));
  for(const entry of [
    '--font-size-xs: 11px','--font-size-sm: 12px','--font-size-base: 14px',
    '--font-size-lg: 16px','--font-size-xl: 20px','--font-size-2xl: 24px',
    '--control-height: 32px','--control-height-sm: 28px',
    '--chart-height: 240px','--content-max: 1392px'
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
