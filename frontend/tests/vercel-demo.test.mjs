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

test('Vercel client review remains a real two-service app with strict no-store API routes', () => {
  const root=JSON.parse(src('../vercel.json'));
  const frontend=JSON.parse(src('vercel.json'));
  assert.equal(root.services.web.root, 'frontend/');
  assert.equal(root.services.api.root, 'backend/');
  assert.equal(root.services.api.entrypoint, 'wsgi:app');
  const source=rule=>root.headers.find(x=>x.source===rule);
  assert.ok(source('/api/(.*)').headers.some(h=>h.key==='Cache-Control'&&h.value.includes('no-store')));
  assert.ok(source('/readyz').headers.some(h=>h.key==='Cache-Control'&&h.value.includes('no-store')));
  assert.ok(source('/sw.js').headers.some(h=>h.key==='Cache-Control'&&h.value.includes('no-cache')));
  assert.ok(frontend.headers.some(h=>h.source==='/app-version.json'&&h.headers.some(z=>z.value.includes('no-store'))));
  assert.equal(root.rewrites[0].destination.service, 'api');
  assert.equal(root.rewrites[root.rewrites.length-1].destination.service, 'web');
  const vite=src('vite.config.js');
  assert.ok(vite.includes("process.env.VERCEL === '1'"));
  assert.ok(vite.includes("new URL('../ops/dev_ports.json', import.meta.url)"));
});

test('client review config defaults to private staff invitations and synthetic data only', () => {
  const config=src('../ops/vercel.env.sample');
  const docs=src('../docs/VERCEL_CLIENT_PREVIEW.md');
  assert.ok(config.includes('APP_ENV=production'));
  assert.ok(config.includes('COOKIE_SECURE=true'));
  assert.ok(config.includes('PUBLIC_REGISTRATION_ENABLED=false'));
  assert.ok(config.includes('VITE_KATS_PUBLIC_DEMO=false'));
  assert.ok(config.includes('DB_POOL_SIZE=1'));
  assert.ok(config.includes('RATELIMIT_STORAGE_URI=katsdb://'));
  assert.ok(config.includes('KATS_TASK_MODE=inline'));
  assert.ok(!config.includes('REDIS_URL='));
  assert.ok(docs.includes('ops/setup_neon_demo.py'));
  for(const key of ['RATELIMIT_STORAGE_URI','KATS_TASK_MODE','JWT_SECRET_KEY','CORS_ORIGINS','TRUSTED_HOSTS','SMTP_HOST','MAIL_FROM']){
    assert.ok(config.includes(key+'='), 'missing '+key);
  }
  for(const word of ['Hobby','Pro','Hostwares','fictional','Redis','Celery','verify_vercel_preview.py']) {
    assert.ok(docs.includes(word), 'missing preview runbook guidance: '+word);
  }
  assert.ok(docs.includes('not a production release'));
  assert.ok(docs.includes('Root Directory: repo root'));
});
