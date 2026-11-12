import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read = path => readFileSync(new URL('../'+path, import.meta.url), 'utf8');

test('preview account picker uses real server-issued sessions, not client passwords', () => {
  const ui=read('src/App.jsx');
  assert.ok(ui.includes("api('auth/demo-accounts')"));
  assert.ok(ui.includes("api('auth/demo-sign-in'"));
  assert.ok(ui.includes("onSuccess(payload.user)"));
  assert.ok(ui.includes("navigate('/dashboard')"));
  assert.ok(ui.includes('demoAccounts.length > 0'));
  assert.ok(ui.includes("setDemoStatus('offline')"), 'failed local Flask must show a visible status');
  assert.ok(ui.includes('setTimeout(query'), 'demo discovery must retry while Flask warms up');
  assert.ok(ui.includes('Retry local connection'), 'user needs explicit retry');
  assert.ok(ui.includes('signInDemo(\'landlord\')'));
  assert.ok(ui.includes('signInDemo(account.key)'));
  assert.ok(ui.includes('role="group" aria-label="Sign in as a demo tenant"'));
  // Local preview signs in via server-issued sessions, never bundled reusable
  // credentials. The separate public synthetic demo is explicitly opt-in.
  assert.ok(ui.includes("api('auth/demo-sign-in'"));
  assert.ok(ui.includes("import.meta.env.VITE_KATS_PUBLIC_DEMO === 'true'"));
  assert.equal(ui.includes('password: "LocalDemoSecret"'), false);
});

test('demo endpoints have strict preview and loopback safety gates', () => {
  const backend=read('../backend/app/demo_preview.py');
  const api=read('../backend/app/api.py');
  const seeder=read('../ops/seed_demo_preview.py');
  assert.ok(backend.includes('APP_ENV'));
  assert.ok(backend.includes('KATS_PREVIEW_MODE'));
  assert.ok(backend.includes('request.remote_addr'));
  assert.ok(backend.includes('kats-preview.sqlite3'));
  assert.ok(backend.includes('not actual_app.config.get("TESTING", False)'));
  assert.ok(api.includes('if not demo_http_allowed():'));
  assert.ok(api.includes('event="auth.demo_login"'));
  assert.ok(seeder.includes('assert_preview_database()'));
  assert.ok(seeder.includes('if verify_existing():'));
  assert.ok(seeder.includes('30 linked leases'));
});

test('preview launchers prepare sample dataset without changing real database mode', () => {
  const runner=read('../ops/run_windows.py');
  assert.ok(runner.includes('seed_demo_preview.py'));
  assert.ok(runner.includes('if preview:'));
  assert.ok(runner.includes('quick and preview'));
  assert.ok(runner.includes('KATS_SEED_DEMO'));
  assert.ok(runner.includes('if run_back and not reuse_back and quick and preview and os.getenv("KATS_SEED_DEMO") == "1":'));
});
