import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');

test('public pages have one shared header and footer layout without legacy placeholders', () => {
  const app = read('src/App.jsx');
  const publicSite = read('src/site/Marketing.jsx');
  const routes = ['/', '/features', '/how-it-works', '/about', '/contact', '/pricing', '/login', '/forgot-password'];
  assert.ok(app.includes('<Route element={<PublicShell user={user} logout={logout}/>}>'));
  for (const path of routes) assert.ok(app.includes('path="' + path + '"'));
  assert.ok(publicSite.includes('<PublicHeader user={user} logout={logout}/>'));
  assert.ok(publicSite.includes('<PublicFooter/>'));
  assert.ok(publicSite.includes('<Outlet/>'));
  assert.equal(app.includes('<TextPage'), false);
  assert.equal(app.includes('<PublicLegalPage'), false);
});

test('homepage hero uses multiple known Unsplash photo sources, with parallax and accessibility', () => {
  const media = read('src/site/media.js');
  const ui = read('src/site/Marketing.jsx');
  const css = read('src/site/site.css');
  const photos = [...media.matchAll(/images\.unsplash\.com\/photo-[^']+/g)];
  assert.equal(photos.length, 5);
  assert.equal(new Set(photos.map(x => x[0])).size, 5);
  assert.ok(media.includes('unsplash.com/photos/'));
  assert.ok(ui.includes('window.matchMedia'));
  assert.ok(ui.includes('setInterval(advance, 6500)'));
  assert.ok(ui.includes('parallax'));
  assert.ok(ui.includes('aria-label="Next residential photo"'));
  assert.ok(ui.includes('aria-label="Previous residential photo"'));
  assert.ok(css.includes('background-size:cover'));
  assert.ok(css.includes('prefers-reduced-motion:reduce'));
  assert.ok(css.includes('backdrop-filter:blur'));
});

test('contact form uses actual backend API with validation, consent and no fictitious reachability', () => {
  const ui = read('src/site/Marketing.jsx');
  assert.ok(ui.includes("api('public/contact-requests'"));
  assert.ok(ui.includes('values.consent'));
  assert.ok(ui.includes('values.website'));
  assert.ok(ui.includes('role="alert"'));
  assert.ok(ui.includes('role="status"'));
  assert.equal(ui.includes('hello@katspm.com'), false);
  assert.equal(ui.includes('(888) 555-KATS'), false);
});

test('legal pages have publication precedence and avoid claims of certification', () => {
  const legal = read('src/site/legal.js');
  const ui = read('src/site/Marketing.jsx');
  const backend = read('../backend/app/extra_api.py');
  for (const slug of ['privacy','terms','cookies','refund','data-protection','acceptable-use','disclaimer','accessibility']) {
    assert.ok(legal.includes('  '+(slug.includes('-') ? "'" + slug + "'" : slug)+':') ||
              legal.includes('  '+slug+':'), 'missing draft: ' + slug);
    assert.ok(backend.includes('"' + slug + '"'), 'missing server allowlist: ' + slug);
  }
  assert.ok(ui.includes('published ?'));
  assert.ok(ui.includes('operator/legal review'));
  assert.ok(legal.includes('not KATS customer results'));
});
test('sign in still uses backend login and MFA without nonfunctional social sign-in buttons', () => {
  const app = read('src/App.jsx');
  assert.ok(app.includes("api('auth/login'"));
  assert.ok(app.includes('mfa_code: mfaCode'));
  assert.ok(app.includes('onSuccess(payload.user)'));
  assert.ok(app.includes("navigate('/dashboard')"));
  assert.equal(app.includes('Sign in with Google'), false);
});
