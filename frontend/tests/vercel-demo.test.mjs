import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const src = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');

test('public synthetic credentials panel is explicit opt-in and beside sign in', () => {
  const app=src('src/App.jsx');
  const css=src('src/site/redesign.css');
  assert.ok(app.includes("import.meta.env.VITE_KATS_PUBLIC_DEMO === 'true'"));
  assert.ok(app.includes("import.meta.env.VITE_KATS_DEMO_PASSWORD.length >= 12"));
  assert.ok(app.includes('aria-label="Demo Accounts — for testing only"'));
  assert.ok(app.includes('<aside className="pm-public-demo-pane"'));
  assert.ok(app.includes('PUBLIC_DEMO_ACCOUNTS.map(account =>'));
  assert.ok(app.includes('setEmail(account.email)'));
  assert.ok(app.includes('setPassword(import.meta.env.VITE_KATS_DEMO_PASSWORD)'));
  assert.ok(app.includes('landlord@demo.kats.invalid'));
  assert.ok(app.includes('tenant'));
  assert.ok(css.includes('grid-template-columns:minmax(225px,.72fr) minmax(370px,1fr) minmax(295px,.76fr)'));
  assert.ok(css.includes('@media(max-width:720px)'));
  assert.equal(app.includes('sk_live_'), false);
});

test('Vercel services preserve backend, same-origin API and SPA paths', () => {
  const config=JSON.parse(src('../vercel.json'));
  const frontend=JSON.parse(src('vercel.json'));
  assert.equal(config.services.api.root, 'backend/');
  assert.equal(config.services.api.entrypoint, 'wsgi:app');
  assert.equal(config.services.web.root, 'frontend/');
  assert.equal(config.rewrites[0].source, '/api/(.*)');
  assert.equal(config.rewrites[0].destination.service, 'api');
  assert.ok(config.rewrites.some(x => x.source === '/readyz'));
  assert.ok(config.rewrites.some(x => x.source === '/healthz'));
  assert.equal(frontend.rewrites[0].destination, '/index.html');
});
