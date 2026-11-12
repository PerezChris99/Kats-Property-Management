import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'src');
const read = path => readFileSync(resolve(sourceRoot, path), 'utf8');

test('all role-specific chart imports resolve without missing lazy chunks', () => {
  const app = read('App.jsx');
  const lazyImports = [...app.matchAll(/lazy\(\(\) => import\('([^']+)'\)/g)];
  assert.ok(lazyImports.length >= 15, 'expected lazy route modules');
  for (const [, ref] of lazyImports) {
    assert.ok(ref.startsWith('./'), 'relative module required');
    assert.ok(existsSync(resolve(sourceRoot, ref + '.jsx')) ||
              existsSync(resolve(sourceRoot, ref + '.js')),
              'missing lazy module: ' + ref);
  }
});

test('all eight existing charts and both new reports are backed by real analytics endpoints', () => {
  const analytics = read('charts/WorkspaceAnalytics.jsx');
  const source = readFileSync(resolve(sourceRoot, '../../backend/app/workspace_analytics.py'), 'utf8');
  const chartEndpoints = [
    'landlord/occupancy','landlord/collections-by-property','landlord/monthly',
    'landlord/tenant-overlap','landlord/property-scores',
    'tenant/payment-status','tenant/applied-payments','tenant/balance-trend',
    'tenant/payment-history','landlord/portfolio'
  ];
  assert.ok(analytics.includes('api(endpoint,{signal:controller.signal})'));
  for (const endpoint of chartEndpoints) {
    assert.ok(analytics.includes('analytics/' + endpoint), 'UI missing: ' + endpoint);
    assert.ok(source.includes('/analytics/' + endpoint + '"'), 'API missing: ' + endpoint);
  }
  assert.ok(source.includes('.group_by('), 'aggregated SQL missing');
  assert.ok(source.includes('func.sum('), 'SQL financial aggregates missing');
  assert.ok(source.includes('func.count('), 'SQL occupancy aggregates missing');
  assert.ok(source.includes('func.date_trunc('), 'PostgreSQL month bucketing missing');
});

test('tokenized portal sizing, shared states and actual no-blank route recovery remain wired', () => {
  const app = read('App.jsx');
  const css = read('workspace.css');
  const charts = read('charts/WorkspaceAnalytics.jsx');
  const ui = read('components/WorkspacePrimitives.jsx');
  const main = read('main.jsx');
  for (const token of [
    '--font-size-xs:', '--font-size-sm:', '--font-size-base: 14px',
    '--font-size-lg:', '--font-size-xl:', '--font-size-2xl:',
    '--control-height: 32px','--control-height-sm: 28px',
    '--content-max: 1392px','--chart-height: 240px'
  ]) assert.ok(css.includes(token), token);
  for (let step=1;step<=8;step++) assert.ok(css.includes('--space-'+step+': '+(step*4)+'px'));
  for (const breakpoint of ['640','768','1024','1280'])
    assert.ok(css.includes('(max-width:'+breakpoint+'px)'));
  assert.ok(css.includes('repeat(12,minmax(0,1fr))'));
  assert.ok(ui.includes('role="status"'));
  assert.ok(ui.includes('role="alert"'));
  assert.ok(charts.includes('PortfolioMetrics'));
  assert.ok(charts.includes('Invalid portfolio response'));
  assert.ok(app.includes('<Route path="*" element={<NotFoundPage/>}/>'));
  assert.ok(main.includes('errorElement: <RouteFailure />'));
  assert.ok(!/style=\{\{\s*(?:fontSize|padding)\s*:/.test(app), 'no inline font/padding overrides');
});
