import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');

test('public pages have one shared header and footer layout without legacy placeholders', () => {
  const app = read('src/App.jsx');
  const publicSite = read('src/site/Marketing.jsx');
  const routes = ['/', '/features', '/how-it-works', '/about', '/request-access', '/login', '/forgot-password'];
  assert.ok(app.includes('<Route element={<PublicShell user={user} logout={logout}/>}>'));
  for (const path of routes) assert.ok(app.includes('path="' + path + '"'));
  assert.ok(publicSite.includes('<PublicHeader user={user} logout={logout}/>'));
  assert.ok(publicSite.includes('<PublicFooter/>'));
  assert.ok(publicSite.includes('<Outlet/>'));
  assert.equal(app.includes('<TextPage'), false);
  assert.equal(app.includes('<PublicLegalPage'), false);
});

test('Ugandan property photos have verified file sources, license and visible attribution', () => {
  const media = read('src/site/media.js');
  const ui = read('src/site/Marketing.jsx');
  const css = read('src/site/site.css');
  const app = read('src/App.jsx');
  const photos = [...media.matchAll(/https:\/\/(?:thumb|upload)\.wikimedia\.org\/wikipedia\/commons\/thumb\/[^']+/g)];
  assert.equal(photos.length, 5);
  assert.equal(new Set(photos.map(p => p[0])).size, 5);
  assert.ok(media.includes('Kololo, Kampala'));
  assert.ok(media.includes('Entebbe'));
  assert.ok(media.includes('creativecommons.org/licenses/by-sa/4.0'));
  assert.ok(ui.includes('pm-credits'));
  assert.ok(ui.includes('PHOTO_LICENSE'));
  assert.ok(app.includes("'--pm-auth-photo'"));
  assert.equal(css.includes('images.unsplash.com'), false);
});

test('the carousel uses smooth layer parallax, independent slides and reduced-motion protections', () => {
  const ui = read('src/site/Marketing.jsx');
  const css = read('src/site/site.css');
  assert.ok(ui.includes('ref={heroRef}'));
  assert.ok(ui.includes("window.requestAnimationFrame(tick)"));
  assert.ok(ui.includes("hero.style.setProperty('--pm-parallax-y'"));
  assert.ok(ui.includes("window.matchMedia('(prefers-reduced-motion: reduce)')"));
  assert.ok(ui.includes('setInterval(advance, 6500)'));
  assert.equal(ui.includes('setParallax'), false);
  assert.ok(css.includes('translate3d(0,var(--pm-parallax-y,0px),0)'));
  assert.ok(css.includes('prefers-reduced-motion:reduce'));
  assert.ok(css.includes('background-size:cover'));
  assert.ok(ui.includes('aria-label="Next residential photo"'));
  assert.ok(ui.includes('aria-label="Previous residential photo"'));
});

test('cards and forms have bounded grids and mobile layouts without shrinking checkboxes', () => {
  const css = read('src/site/site.css');
  const portal = read('src/styles.css');
  assert.ok(css.includes('minmax(0,1fr)'));
  assert.ok(css.includes('max-width:100%'));
  assert.ok(css.includes('min-width:0'));
  assert.ok(css.includes('@media(max-width:520px)'));
  assert.ok(css.includes('.pm-hero-panel{width:min(535px,55%)'));
  assert.ok(css.includes('input:not([type=checkbox])'));
  assert.ok(portal.includes('.page .data-table-wrap{overflow-x:auto'));
  assert.ok(portal.includes('.page .fields{gap:13px 15px}'));
});

test('request access remains a real, consent-gated and admin-reviewed workflow', () => {
  const ui = read('src/site/Marketing.jsx');
  assert.ok(ui.includes("api('public/access-requests'"));
  assert.ok(ui.includes('values.consent'));
  assert.ok(ui.includes('values.website'));

  assert.ok(ui.includes("subject: 'ACCESS'"));
  assert.ok(ui.includes('Submitting does not create an account.'));
  assert.ok(ui.includes('RequestAccessPage'));
  assert.ok(read('src/App.jsx').includes('path="/contact" element={<Navigate to="/request-access" replace/>}'));
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
  assert.ok(legal.includes('not measured KATS customer outcomes'));
});
test('sign in still uses backend login and MFA without nonfunctional social sign-in buttons', () => {
  const app = read('src/App.jsx');
  assert.ok(app.includes("api('auth/login'"));
  assert.ok(app.includes('mfa_code: mfaCode'));
  assert.ok(app.includes('onSuccess(payload.user)'));
  assert.ok(app.includes("navigate('/dashboard')"));
  assert.equal(app.includes('Sign in with Google'), false);
});
