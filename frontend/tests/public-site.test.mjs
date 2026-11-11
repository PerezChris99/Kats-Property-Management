import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');

test('public routes use one focused homepage and preserve essential screens', () => {
  const app = read('src/App.jsx');
  const publicSite = read('src/site/Marketing.jsx');
  const paths = ['/', '/features', '/how-it-works', '/about', '/request-access', '/login', '/forgot-password'];
  assert.ok(app.includes('<Route element={<PublicShell user={user} logout={logout}/>}>'));
  for (const path of paths) assert.ok(app.includes('path="' + path + '"'));
  assert.ok(publicSite.includes('<PublicHeader user={user} logout={logout}/>'));
  assert.ok(publicSite.includes('<PublicFooter/>'));
  assert.ok(publicSite.includes('<Outlet/>'));
  assert.ok(app.includes('path="/features" element={<Navigate to="/#capabilities" replace/>}'));
  assert.ok(app.includes('path="/how-it-works" element={<Navigate to="/#workflow" replace/>}'));
  assert.ok(app.includes('path="/about" element={<Navigate to="/#about" replace/>}'));
  assert.equal(app.includes('<FeaturesPage/>'), false);
  assert.equal(app.includes('<HowItWorksPage/>'), false);
  assert.equal(app.includes('<AboutPage/>'), false);
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
  assert.equal(ui.includes('className="pm-credits"'), false);
  assert.ok(ui.includes('ImageAttributionsPage'));
  assert.ok(ui.includes('PHOTO_LICENSE'));
  assert.ok(app.includes('path="/image-attributions"'));
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
  assert.ok(ui.includes('setInterval(advance, 5200)'));
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
  assert.ok(legal.includes('not verified customer data'));
  assert.ok(legal.includes('UGANDA_POLICY_CONTEXT'));
  assert.ok(ui.includes('lawContext.sources.map'));
  assert.ok(ui.includes('published ?'));
});
test('sign in still uses backend login and MFA without nonfunctional social sign-in buttons', () => {
  const app = read('src/App.jsx');
  assert.ok(app.includes("api('auth/login'"));
  assert.ok(app.includes('mfa_code: mfaCode'));
  assert.ok(app.includes('onSuccess(payload.user)'));
  assert.ok(app.includes("navigate('/dashboard')"));
  assert.equal(app.includes('Sign in with Google'), false);
});


test('redesigned home hero is text-only and has centered editorial styling', () => {
  const ui = read('src/site/Marketing.jsx');
  const design = read('src/site/redesign.css');
  assert.ok(ui.includes('className="pm-hero-copy"'));
  assert.equal(ui.includes('className="pm-glass pm-hero-panel"'), false);
  assert.ok(design.includes('.pm-hero-copy'));
  assert.ok(design.includes('text-align:center'));
  assert.ok(design.includes('prefers-reduced-motion:reduce'));
  const entry = read('src/main.jsx');
  assert.ok(entry.indexOf("import './site/redesign.css'") > entry.indexOf("import './worldclass.css'"));
});

test('access request retains real submission and accessible glass review timeline', () => {
  const ui = read('src/site/Marketing.jsx');
  const design = read('src/site/redesign.css');
  assert.ok(ui.includes('aria-labelledby="pm-request-heading"'));
  assert.ok(ui.includes('className="pm-request-guide" aria-label="Access review process"'));
  assert.ok(ui.includes('method: \'POST\''));
  assert.ok(ui.includes('required onChange={e => change(\'consent\''));
  assert.ok(design.includes('backdrop-filter:blur'));
  assert.ok(design.includes('.pm-request-guide ol'));
  assert.ok(design.includes('pm-request-layout .pm-fields'));
});

test('workspace dashboard uses live response, not placeholder statistics', () => {
  const app = read('src/App.jsx');
  const css = read('src/worldclass.css');
  assert.ok(app.includes("api('dashboard').then(setSummary)"));
  assert.ok(app.includes('summary.collected_ugx'));
  assert.ok(app.includes('summary.open_maintenance'));
  assert.ok(app.includes('kats-overview-spotlight'));
  assert.ok(css.includes('.kats-overview-spotlight'));
  assert.ok(css.includes('prefers-reduced-transparency:reduce'));
});


test('landing hero scenery has smooth parallax and reduced-motion protection', () => {
  const ui = read('src/site/Marketing.jsx');
  const css = read('src/site/redesign.css');
  assert.ok(ui.includes("hero.style.setProperty('--pm-parallax-x'"));
  assert.ok(ui.includes("hero.style.setProperty('--pm-parallax-y'"));
  assert.ok(ui.includes("window.addEventListener('scroll', schedule, { passive: true })"));
  assert.ok(ui.includes("hero.addEventListener('pointermove', onPointerMove"));
  assert.ok(css.includes('translate3d(var(--pm-parallax-x,0px),var(--pm-parallax-y,0px),0)'));
  assert.ok(css.includes('.kats-public .pm-hero-copy {position:relative;z-index:2;}'));
  assert.ok(css.includes('prefers-reduced-motion:reduce'));
});

test('landing closing action is a page section, not a gradient card', () => {
  const ui = read('src/site/Marketing.jsx');
  const css = read('src/site/redesign.css');
  assert.ok(ui.includes('className="pm-endcap"'));
  assert.ok(ui.includes('className="pm-container pm-endcap-inner"'));
  assert.ok(ui.includes('className="pm-endcap-primary"'));
  assert.ok(ui.includes('<CoreCapabilities/><HowSteps/><AccessCallout user={user}/></main>'));
  assert.equal(ui.includes('className="pm-access-line"'), false);
  assert.ok(css.includes('.kats-public .pm-endcap-primary'));
  assert.ok(css.includes('background:#edf5fa'));
  assert.ok(css.includes('color:#fff!important'));
});


test('public navigation is limited to Home, Request Access and Sign in', () => {
  const ui = read('src/site/Marketing.jsx');
  const nav = ui.slice(ui.indexOf('function PublicHeader('), ui.indexOf('function PublicFooter('));
  assert.ok(nav.includes("['/', 'Home']"));
  assert.ok(nav.includes("['/request-access', 'Request access']"));
  assert.ok(nav.includes('to="/login"'));
  for (const stale of ["['/features', 'Features']", "['/how-it-works', 'How it works']", "['/about', 'About']"]) {
    assert.equal(nav.includes(stale), false);
  }
  assert.ok(ui.includes('id="capabilities"'));
  assert.ok(ui.includes('id="workflow"'));
  assert.ok(ui.includes('id="about"'));
  assert.ok(ui.includes('<HeroCarousel user={user}/><TrustBand/><CoreCapabilities/><HowSteps/><AccessCallout user={user}/>'));
});

test('redundant marketing views are removed without affecting operational modules', () => {
  const ui = read('src/site/Marketing.jsx');
  const app = read('src/App.jsx');
  assert.equal(ui.includes('export function FeaturesPage()'), false);
  assert.equal(ui.includes('export function HowItWorksPage()'), false);
  assert.equal(ui.includes('export function AboutPage()'), false);
  assert.equal(ui.includes('function Problems()'), false);
  assert.equal(ui.includes('function Solution()'), false);
  assert.equal(ui.includes('function FAQ('), false);
  assert.ok(app.includes("['dashboard', 'properties'"));
  assert.ok(app.includes('path="/request-access" element={<RequestAccessPage/>}'));
  assert.ok(app.includes('path="/forgot-password" element={<ForgotPasswordPage/>}'));
  assert.ok(app.includes("element={<LegalPage slug={slug}/> }") || app.includes('element={<LegalPage slug={slug}/>}'));
});


test('hero loads first Wikimedia image at high priority without starting every slide simultaneously', () => {
  const html = read('index.html');
  const ui = read('src/site/Marketing.jsx');
  const media = read('src/site/media.js');
  assert.ok(html.includes('rel="preload" as="image" fetchpriority="high"'));
  assert.ok(html.includes('preconnect" href="https://thumb.wikimedia.org"'));
  assert.equal(html.includes('images.unsplash.com'), false);
  assert.ok(media.includes('960px-Apartment_block_in_kololo_Kampala.jpg'));
  assert.ok(ui.includes('function prime(n)'));
  assert.ok(ui.includes('const [ready, setReady]'));
  assert.ok(ui.includes('style={ready.has(n) ?'));
});

test('typography, house back-to-top and developer link preserve accessible controls', () => {
  const ui = read('src/site/Marketing.jsx');
  const css = read('src/site/redesign.css');
  const html = read('index.html');
  assert.ok(html.includes('family=Newsreader:opsz,wght@6..72,400..700'));
  assert.ok(html.includes('family=IBM+Plex+Sans'));
  assert.ok(css.includes("font-family:'Newsreader'"));
  assert.ok(css.includes('html {scroll-behavior:smooth'));
  assert.ok(css.includes('html {scroll-behavior:auto!important;}'));
  assert.ok(ui.includes('aria-label="Return to top"'));
  assert.ok(ui.includes('<House size={22}'));
  assert.ok(ui.includes('window.scrollTo({'));
  assert.ok(ui.includes('href="https://kweeziperez.com" target="_blank" rel="noopener noreferrer"'));
  assert.ok(ui.includes('Developed by Kweezi Perez Christopher'));
  const footer = ui.slice(ui.indexOf('function PublicFooter('),ui.indexOf('export function PublicShell('));
  assert.equal(footer.includes('Photo credits'), false);
  assert.equal(footer.includes('pm-credits'), false);
  assert.equal(footer.includes('Ugandan residential photos'), false);
});

test('Uganda legal context names primary law and preserves operator publication precedence', () => {
  const ui = read('src/site/Marketing.jsx');
  const legal = read('src/site/legal.js');
  for (const law of ['Landlord and Tenant Act, 2022', 'Data Protection and Privacy Act, 2019', 'Data Protection and Privacy Regulations, 2021', 'Electronic Transactions Act, 2011', 'Land Act, 1998']) {
    assert.ok(legal.includes(law), law);
  }
  for (const slug of ['privacy', 'terms', 'cookies', 'refund', 'data-protection', 'acceptable-use', 'disclaimer', 'accessibility']) {
    assert.ok(legal.includes("  '"+slug+"':") || legal.includes('  '+slug+':'));
  }
  assert.ok(ui.includes('UGANDA_POLICY_CONTEXT[slug]'));
  assert.ok(ui.includes('lawContext.sections.map'));
  assert.ok(ui.includes('lawContext.sources.map'));
  assert.ok(ui.includes('Operator-published version'));
  assert.ok(ui.includes('not legal advice'));
  assert.ok(read('src/App.jsx').includes('path="/image-attributions" element={<ImageAttributionsPage/>}'));
});


test('footer has a single semantic responsive grid, aligned navigation and preserved attribution', () => {
  const ui = read('src/site/Marketing.jsx');
  const css = read('src/site/redesign.css');
  const footer = ui.slice(ui.indexOf('function PublicFooter()'), ui.indexOf('export function PublicShell('));
  assert.ok(footer.includes('<nav className="pm-footer-links" aria-label="Footer navigation">'));
  assert.ok(footer.includes('className="pm-footer-brand"'));
  assert.ok(footer.includes('className="pm-footer-group pm-footer-legal"'));
  assert.equal((footer.match(/className="pm-footer-group/g) || []).length, 3);
  assert.ok(footer.includes('<Link to="/image-attributions">Image licenses</Link>'));
  assert.ok(footer.includes('href="https://kweeziperez.com" target="_blank" rel="noopener noreferrer"'));
  assert.equal(footer.includes('Photo credits & license'), false);
  assert.ok(css.includes('.kats-public .pm-footer-body > .pm-footer-links'));
  assert.ok(css.includes('grid-template-columns:repeat(3,minmax(0,1fr));'));
  assert.ok(css.includes('grid-template-columns:repeat(2,minmax(0,1fr));'));
  assert.ok(css.includes('grid-template-columns:minmax(0,1fr);'));
  assert.ok(css.includes('@media (max-width:1100px)'));
  assert.ok(css.includes('@media (max-width:700px)'));
  assert.ok(css.includes('@media (max-width:360px)'));
  assert.ok(css.includes('overflow-wrap:anywhere'));
  assert.ok(css.includes('.pm-footer-base .pm-developer-link'));
});

test('narrow landscape and operational workspaces keep flexible content widths', () => {
  const css = read('src/site/redesign.css');
  const portal = read('src/styles.css');
  assert.ok(css.includes('@media (max-height:480px) and (orientation:landscape)'));
  assert.ok(css.includes('.portal .portal-content .page .data-table-wrap'));
  assert.ok(css.includes('overflow-x:auto;'));
  assert.ok(css.includes('overscroll-behavior-x:contain;'));
  assert.ok(portal.includes('.mobile-nav'));
});
