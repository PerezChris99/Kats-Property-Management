import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  ArrowRight, BookOpen, Building2, ChartNoAxesCombined, Check, CheckCircle2, House,
  ChevronLeft, ChevronRight, CreditCard, FileCheck2, KeyRound,
  Menu, ShieldCheck, Users, Wallet, Wrench, X
} from 'lucide-react';
import { api } from '../lib/api';
import { PHOTOS, PHOTO_LICENSE } from './media';
import { POLICY_LINKS, POLICY_PAGES, UGANDA_POLICY_CONTEXT } from './legal';
import './site.css';

const PRINCIPLES = [
  { icon: Building2, title: 'Owners', detail: 'Portfolio visibility.' },
  { icon: Users, title: 'Managers', detail: 'Units and operations.' },
  { icon: Wallet, title: 'Accountants', detail: 'Rent and expenses.' },
  { icon: Wrench, title: 'Caretakers', detail: 'Repairs and assignments.' },
  { icon: KeyRound, title: 'Tenants', detail: 'Leases and requests.' }
];
const FEATURES = [
  { icon: Building2, eyebrow: 'PORTFOLIO', title: 'Properties & rooms', body: 'Monitor buildings, rooms and occupancy.' },
  { icon: FileCheck2, eyebrow: 'TENANCIES', title: 'Leases & tenants', body: 'Manage tenants, deposits and renewals.' },
  { icon: CreditCard, eyebrow: 'FINANCE', title: 'Rent & payments', body: 'Record UGX invoices and review collections.' },
  { icon: Wrench, eyebrow: 'OPERATIONS', title: 'Maintenance', body: 'Track requests, work orders and repairs.' },
  { icon: ChartNoAxesCombined, eyebrow: 'OVERSIGHT', title: 'Reports', body: 'Understand occupancy, arrears and expenses.' },
  { icon: ShieldCheck, eyebrow: 'ADMINISTRATION', title: 'Access & approvals', body: 'Control roles, permissions and approvals.' }
];
const WORKFLOW = [
  { label: '01', icon: Building2, title: 'Add properties', body: 'Set up buildings, rooms and status.' },
  { label: '02', icon: KeyRound, title: 'Set up leases', body: 'Register tenants and their leases.' },
  { label: '03', icon: CreditCard, title: 'Run operations', body: 'Review rent and manage repairs.' },
  { label: '04', icon: ChartNoAxesCombined, title: 'Track results', body: 'Review reports and activity.' }
];
function Brand({ compact = false }) {
  return <Link to="/" className={'pm-brand' + (compact ? ' pm-brand-compact' : '')} aria-label="KATS Property Management, home">
    <img src="/brand-mark.svg" width="54" height="54" alt="" aria-hidden="true"/>
    <span><strong>KATS</strong><small>Property Management</small></span>
  </Link>;
}

function PublicHeader({ user, logout }) {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => { setOpen(false); }, [pathname]);
  const links = [['/', 'Home'], ['/request-access', 'Request access']];
  return <header className="pm-header">
    <div className="pm-header-inner">
      <Brand />
      <button className="pm-menu-trigger" type="button" aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} aria-controls="pm-main-nav" onClick={() => setOpen(v => !v)}>{open ? <X/> : <Menu/>}</button>
      <nav id="pm-main-nav" className={'pm-nav' + (open ? ' is-open' : '')} aria-label="Main navigation">
        {links.map(([to, label]) => <NavLink end key={to} to={to} className={({isActive}) => isActive ? 'is-active' : ''}>{label}</NavLink>)}
        <span className="pm-nav-separator" aria-hidden="true"/>
        {user ? <><Link to="/dashboard">Workspace</Link><button type="button" className="pm-nav-signout" onClick={logout}>Sign out</button></> : <Link to="/login" className="pm-nav-login"><KeyRound size={16}/> Sign in</Link>}
        
      </nav>
    </div>
  </header>;
}

function PublicFooter() {
  const [nearViewport, setNearViewport] = useState(false);
  const footerRef = useRef(null);
  useEffect(() => {
    const node = footerRef.current;
    if (!node) return undefined;
    if (typeof IntersectionObserver === 'undefined') {
      setNearViewport(true);
      return undefined;
    }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setNearViewport(true);
        observer.disconnect();
      }
    }, { rootMargin: '280px 0px' });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return <footer ref={footerRef}
    className={'pm-footer' + (nearViewport ? ' has-photo' : '')}
    style={nearViewport ? { '--pm-footer-photo': 'url("' + PHOTOS[4].url + '")' } : undefined}
    aria-label="KATS footer">
    <div className="pm-footer-body">
      <div className="pm-footer-brand">
        <Brand compact/>
        <p>A clear view of your properties, rent and maintenance.</p>
      </div>
      <nav className="pm-footer-links" aria-label="Footer navigation">
        <div className="pm-footer-group">
          <h3>Overview</h3>
          <Link to="/">Home</Link>
          <Link to="/#capabilities">What KATS does</Link>
          <Link to="/#workflow">How it works</Link>
          <Link to="/#about">About KATS</Link>
        </div>
        <div className="pm-footer-group">
          <h3>Access</h3>
          <Link to="/login">Sign in</Link>
          <Link to="/request-access">Request access</Link>
          <Link to="/forgot-password">Recover account</Link>
        </div>
        <div className="pm-footer-group pm-footer-legal">
          <h3>Legal &amp; trust</h3>
          {POLICY_LINKS.map(([name, slug]) => <Link to={'/' + slug} key={slug}>{name}</Link>)}
          <Link to="/image-attributions">Image licenses</Link>
        </div>
      </nav>
    </div>
    <div className="pm-footer-base">
      <span>© {new Date().getFullYear()} KATS Property Management.</span>
      <a className="pm-developer-link" href="https://kweeziperez.com" target="_blank" rel="noopener noreferrer">Developed by Kweezi Perez Christopher</a>
    </div>
  </footer>;
}

export function PublicShell({ user, logout }) {
  const { pathname, hash } = useLocation();
  const [showTop, setShowTop] = useState(false);
  useEffect(() => {
    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        setShowTop(window.scrollY > 420);
        frame = 0;
      });
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => { window.removeEventListener('scroll', onScroll); window.cancelAnimationFrame(frame); };
  }, []);
  function returnToTop() {
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    });
  }
  useEffect(() => {
    document.title = pathname === '/' ? 'KATS · Property management workspace' : 'KATS Property Management · ' + (pathname.slice(1).replaceAll('-', ' ') || 'Home');
    const frame = window.requestAnimationFrame(() => {
      const id = pathname === '/' ? decodeURIComponent(hash.slice(1)) : '';
      const target = id ? document.getElementById(id) : null;
      if (target) target.scrollIntoView({ behavior: 'auto', block: 'start' });
      else window.scrollTo({ top: 0, behavior: 'auto' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [pathname, hash]);
  return <div className="kats-public"><a className="pm-skip" href="#pm-content">Skip to content</a><PublicHeader user={user} logout={logout}/><div id="pm-content"><Outlet/></div><PublicFooter/><button className={'pm-back-top' + (showTop ? ' is-visible' : '')} type="button" onClick={returnToTop} aria-label="Return to top" title="Return to top" tabIndex={showTop ? 0 : -1} aria-hidden={showTop ? undefined : 'true'}><House size={22} strokeWidth={1.9} aria-hidden="true"/></button></div>;
}

function SectionTitle({ eyebrow, title, text, center = false }) {
  return <div className={'pm-section-title' + (center ? ' is-centered' : '')}><span className="pm-kicker">{eyebrow}</span><h2>{title}</h2>{text && <p>{text}</p>}</div>;
}
function AccessCallout({ user }) {
  const title = 'Everything your property team needs. One workspace.';
  const description = 'Less chasing records. More time managing properties.';
  return <section className="pm-endcap" aria-label="Get started with KATS">
    <div className="pm-container pm-endcap-inner">
      <div className="pm-endcap-copy">
        <span className="pm-kicker">GET STARTED</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="pm-endcap-actions">
        <Link className="pm-endcap-primary" to={user ? '/dashboard' : '/request-access'}>{user ? 'Open workspace' : 'Request access'} <ArrowRight size={18} aria-hidden="true"/></Link>
        {!user && <span>Already registered? <Link to="/login">Sign in</Link></span>}
      </div>
    </div>
  </section>;
}
function HeroCarousel({ user }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [ready, setReady] = useState(() => new Set([0]));
  const heroRef = useRef(null);
  const { pathname } = useLocation();
  const raf = useRef(0);
  useEffect(() => {
    // Prioritise the first image (also preloaded in HTML). Load other slides
    // sequentially after decode so they cannot compete with the hero's LCP.
    let alive = true;
    let pending;
    function prime(n) {
      if (!alive || n >= PHOTOS.length) return;
      const img = new Image();
      pending = img;
      img.decoding = 'async';
      img.onload = () => {
        if (!alive) return;
        setReady(prev => new Set(prev).add(n));
        prime(n + 1);
      };
      img.onerror = () => { if (alive) prime(n + 1); };
      img.src = PHOTOS[n].url;
    }
    prime(0);
    return () => {
      alive = false;
      if (pending) pending.onload = pending.onerror = null;
    };
  }, []);
  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reduceMotion.matches || paused) return undefined;
    const advance = () => {
      if (document.hidden) return;
      setIndex(n => {
        const next = (n + 1) % PHOTOS.length;
        return ready.has(next) ? next : n;
      });
    };
    const timer = window.setInterval(advance, 5200);
    return () => window.clearInterval(timer);
  }, [paused, pathname, ready]);
  useEffect(() => {
    // Only the scenery moves. Copy and CTAs stay still for legibility.
    // One eased, passive RAF loop handles scroll and fine desktop pointer depth.
    const hero = heroRef.current;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (!hero || reducedMotion.matches) return undefined;
    let live = true;
    let x = 0;
    let y = 0;
    let pointerX = 0;
    let pointerY = 0;
    function tick() {
      raf.current = 0;
      if (!live || document.hidden) return;
      const bounds = hero.getBoundingClientRect();
      if (bounds.bottom <= 0 || bounds.top >= window.innerHeight) return;
      const scrollDepth = Math.max(0, Math.min(86, -bounds.top * 0.19));
      const targetX = pointerX;
      const targetY = scrollDepth + pointerY;
      x += (targetX - x) * 0.13;
      y += (targetY - y) * 0.13;
      hero.style.setProperty('--pm-parallax-x', x.toFixed(2) + 'px');
      hero.style.setProperty('--pm-parallax-y', y.toFixed(2) + 'px');
      if (Math.abs(targetX - x) > 0.12 || Math.abs(targetY - y) > 0.12) {
        raf.current = window.requestAnimationFrame(tick);
      }
    }
    const schedule = () => {
      if (!raf.current) raf.current = window.requestAnimationFrame(tick);
    };
    function onPointerMove(event) {
      if (event.pointerType !== 'mouse') return;
      const bounds = hero.getBoundingClientRect();
      pointerX = (((event.clientX - bounds.left) / bounds.width) - 0.5) * 16;
      pointerY = (((event.clientY - bounds.top) / bounds.height) - 0.5) * 10;
      schedule();
    }
    function onPointerLeave() {
      pointerX = 0;
      pointerY = 0;
      schedule();
    }
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    document.addEventListener('visibilitychange', schedule);
    hero.addEventListener('pointermove', onPointerMove, { passive: true });
    hero.addEventListener('pointerleave', onPointerLeave);
    schedule();
    return () => {
      live = false;
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      document.removeEventListener('visibilitychange', schedule);
      hero.removeEventListener('pointermove', onPointerMove);
      hero.removeEventListener('pointerleave', onPointerLeave);
      window.cancelAnimationFrame(raf.current);
      raf.current = 0;
      hero.style.removeProperty('--pm-parallax-x');
      hero.style.removeProperty('--pm-parallax-y');
    };
  }, []);
  function move(by) { setIndex(n => { const next = (n + by + PHOTOS.length) % PHOTOS.length; return ready.has(next) ? next : n; }); }
  return <section ref={heroRef} className="pm-hero" aria-label="Property management introduction" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={e => { if (!e.currentTarget.contains(e.relatedTarget)) setPaused(false); }}>
    <div className="pm-hero-images" aria-hidden="true">{PHOTOS.map((item, n) => <div className={'pm-slide' + (n === index ? ' is-current' : '')} key={item.url} style={ready.has(n) ? { backgroundImage: 'url("' + item.url + '")' } : undefined}/>)}</div>
    <div className="pm-hero-shade"/>
    <div className="pm-hero-inner"><div className="pm-hero-copy"><span className="pm-kicker pm-kicker-light"><span className="pm-spark" /> BUILT FOR UGANDAN RENTALS</span><h1>Manage property. <em>Know the full picture.</em></h1><p>Manage units, leases, rent and repairs in one place.</p><div className="pm-hero-actions"><Link className="pm-cta pm-cta-yellow" to={user ? '/dashboard' : '/request-access'}>{user ? 'Open workspace' : 'Request access'} <ArrowRight size={18}/></Link><Link className="pm-cta pm-cta-ghost" to="/#workflow">How it works</Link></div><div className="pm-hero-points"><span><Check size={15}/> UGX rent records</span><span><Check size={15}/> Secure role access</span></div></div></div>
    <div className="pm-carousel-bottom"><div className="pm-carousel-controls"><button onClick={() => move(-1)} aria-label="Previous residential photo"><ChevronLeft/></button><span className="pm-carousel-count">0{index + 1} / 0{PHOTOS.length}</span><button onClick={() => move(1)} aria-label="Next residential photo"><ChevronRight/></button></div><div className="pm-carousel-dots" aria-label="Choose a residential photo">{PHOTOS.map((p, n) => <button type="button" key={p.credit} aria-label={'Show photo ' + (n + 1)} aria-current={index === n ? 'true' : undefined} onClick={() => { if (ready.has(n)) setIndex(n); }} disabled={!ready.has(n)} className={index === n ? 'is-current' : ''}/>)}</div><a className="pm-hero-credit" href={PHOTOS[index].credit} target="_blank" rel="noopener noreferrer">{PHOTOS[index].location} · {PHOTOS[index].author}</a></div>
  </section>;
}

function TrustBand() {
  return <section id="about" className="pm-role-strip" aria-label="About KATS">
    <div className="pm-container"><span>Built for Ugandan rental operations, with UGX records and role-specific access.</span>
      <div>{PRINCIPLES.map(({ title }) => <span key={title}>{title}</span>)}</div>
    </div>
  </section>;
}
function CoreCapabilities() {
  return <section id="capabilities" className="pm-section pm-core" aria-label="KATS capabilities">
    <div className="pm-container">
      <SectionTitle eyebrow="THE WORKSPACE" title="Manage the essentials." text="One connected place for your daily property work."/>
      <div className="pm-feature-grid pm-core-grid">
        {FEATURES.map(({icon:Icon,eyebrow,title,body}) => <article className="pm-feature-card" key={title}>
          <Icon size={25} aria-hidden="true"/>
          <span className="pm-card-eyebrow">{eyebrow}</span><h3>{title}</h3><p>{body}</p>
        </article>)}
      </div>
    </div>
  </section>;
}
function HowSteps() {
  return <section className="pm-section pm-how pm-how-short" id="workflow">
    <div className="pm-container">
      <SectionTitle eyebrow="THE PROCESS" title="From setup to daily work." text="Four practical steps. Nothing complicated."/>
      <div className="pm-step-grid">{WORKFLOW.map(({label,icon:Icon,title,body}) => <article key={label}>
        <div className="pm-step-top"><span>{label}</span><Icon size={22} aria-hidden="true"/></div>
        <h3>{title}</h3><p>{body}</p>
      </article>)}</div>
    </div>
  </section>;
}
export function LandingPage({ user }) {
  return <main className="pm-main"><HeroCarousel user={user}/><TrustBand/><CoreCapabilities/><HowSteps/><AccessCallout user={user}/></main>;
}

function PageHero({ eyebrow, title, text, photo = PHOTOS[0], children }) {
  const heroRef = useRef(null);
  useEffect(() => {
    const hero = heroRef.current;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (!hero || reduced.matches) return undefined;
    let frame = 0;
    const update = () => {
      frame = 0;
      const rect = hero.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) return;
      hero.style.setProperty('--pm-page-shift', Math.max(-65, Math.min(65, -rect.top * .13)).toFixed(1) + 'px');
    };
    const onScroll = () => { if (!frame) frame = window.requestAnimationFrame(update); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      window.cancelAnimationFrame(frame);
      hero.style.removeProperty('--pm-page-shift');
    };
  }, []);
  return <section ref={heroRef} className="pm-page-hero"><div className="pm-page-hero-image" style={{backgroundImage: 'linear-gradient(90deg,rgba(7,24,49,.88),rgba(7,28,55,.42)),url("' + photo.url + '")'}}/><div className="pm-container pm-page-hero-inner"><span className="pm-kicker pm-kicker-light">{eyebrow}</span><h1>{title}</h1><p>{text}</p>{children}</div></section>;
}
export function RequestAccessPage() {
  const blank = { full_name: '', email: '', phone: '', role: '', portfolio: '', message: '', consent: false, website: '' };
  const [values, setValues] = useState(blank);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const change = (name, value) => setValues(current => ({ ...current, [name]: value }));
  async function submit(event) {
    event.preventDefault();
    setBusy(true); setError(''); setSuccess('');
    try {
      const detail = [
        'Role: ' + (values.role || 'Not specified'),
        'Portfolio: ' + (values.portfolio.trim() || 'Not specified'),
        values.message.trim()
      ].join('\\n');
      const result = await api('public/access-requests', {
        method: 'POST',
        body: JSON.stringify({
          full_name: values.full_name.trim(), email: values.email.trim(),
          phone: values.phone.trim(), subject: 'ACCESS', message: detail,
          consent: values.consent, website: values.website
        })
      });
      setValues(blank);
      setSuccess(result.message || 'Your request has been submitted for review.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Request could not be submitted.');
    } finally { setBusy(false); }
  }
  return <main className="pm-main pm-request-page">
    <section className="pm-section pm-request-section" aria-labelledby="pm-request-heading"><div className="pm-container pm-request-layout">
      <div className="pm-contact-form">
        <div className="pm-request-form-head"><span className="pm-form-index">01 / REQUEST</span><span className="pm-request-security"><ShieldCheck size={15} aria-hidden="true"/> Reviewed by an administrator</span></div>
        <div className="pm-section-title"><span className="pm-kicker">REQUEST ACCESS</span><h1 id="pm-request-heading">Request your workspace.</h1><p>Share a few details. An administrator reviews your request before any account is created.</p></div>
        {success && <p role="status" className="pm-form-success"><CheckCircle2 size={20}/>{success}</p>}
        {error && <p role="alert" className="error">{error}</p>}
        <form onSubmit={submit}>
          <div className="pm-fields">
            <label>Full name<input required maxLength="160" autoComplete="name" value={values.full_name} onChange={e => change('full_name', e.target.value)}/></label>
            <label>Email address<input required type="email" maxLength="254" autoComplete="email" value={values.email} onChange={e => change('email', e.target.value)}/></label>
            <label>Role<select aria-label="Your role" value={values.role} required onChange={e => change('role', e.target.value)}><option value="">Select your role</option><option>Owner</option><option>Manager</option><option>Accountant</option><option>Caretaker</option><option>Tenant</option></select></label>
            <label>Phone (optional)<input type="tel" maxLength="30" autoComplete="tel" value={values.phone} onChange={e => change('phone', e.target.value)}/></label>
          </div>
          <label>Property or building (optional)<input maxLength="120" value={values.portfolio} onChange={e => change('portfolio', e.target.value)}/></label>
          <label>Why do you need access?<textarea required minLength="10" maxLength="2000" rows="3" value={values.message} onChange={e => change('message', e.target.value)} placeholder="Your property or team and the work you manage"/></label>
          <label className="pm-consent"><input type="checkbox" checked={values.consent} required onChange={e => change('consent', e.target.checked)}/><span>I agree to the handling of this request under the <Link to="/privacy">Privacy policy</Link>.</span></label>
          <input className="pm-honeypot" aria-hidden="true" tabIndex={-1} autoComplete="off" name="website" value={values.website} onChange={e => change('website', e.target.value)}/>
          <div className="pm-form-submit"><button className="pm-cta pm-cta-yellow" type="submit" disabled={busy}>{busy ? 'Submitting…' : 'Submit request'} <ArrowRight size={17}/></button><small>Submitting does not create an account.</small></div>
        </form>
        <p className="pm-request-mobile-note"><ShieldCheck size={17} aria-hidden="true"/> Every request is reviewed. Approved accounts receive an invitation to sign in.</p>
      </div>
      <aside className="pm-request-guide" aria-label="Access review process"><span className="pm-form-index">02 / REVIEW</span>
        <div className="pm-guide-mark" aria-hidden="true"><ShieldCheck size={29} strokeWidth={1.5}/></div>
        <span className="pm-kicker">WHAT HAPPENS NEXT</span>
        <h2>Secure access, without the friction.</h2>
        <p className="pm-guide-intro">Your property records stay private. Every new account is reviewed before access is granted.</p>
        <ol><li><strong>Submit details</strong><span>Tell us your role and property.</span></li><li><strong>Administrator review</strong><span>Your request is checked for the correct permissions.</span></li><li><strong>Account invitation</strong><span>If approved, you’ll receive instructions to sign in.</span></li></ol>
        <div className="pm-guide-footer"><span>ALREADY REGISTERED?</span><Link to="/login" className="pm-text-link">Sign in <ArrowRight size={16}/></Link></div>
      </aside>
    </div></section>
  </main>;
}

export function LegalPage({ slug }) {
  const policy=POLICY_PAGES[slug];
  const lawContext=UGANDA_POLICY_CONTEXT[slug];
  const [published,setPublished]=useState(null);
  useEffect(()=>{
    let live=true;setPublished(null);
    api('public/legal/'+slug).then(result=>{if(live && result.page?.content) setPublished(result.page);}).catch(()=>{});
    return ()=>{live=false;};
  },[slug]);
  if(!policy) return <main className="pm-section"><div className="pm-container"><h1>Page not found</h1><Link to="/">Return home</Link></div></main>;
  return <main className="pm-main"><PageHero eyebrow="LEGAL & TRUST" title={published?.title || policy.title} text={published ? 'Operator-published policy · version '+published.version : policy.intro} photo={PHOTOS[3]}/><section className="pm-section pm-legal-section"><div className="pm-container pm-legal-layout"><aside><span className="pm-kicker">LEGAL LIBRARY</span><nav aria-label="Other legal pages">{POLICY_LINKS.map(([label,s])=><Link key={s} aria-current={slug===s?'page':undefined} to={'/'+s}>{label}</Link>)}<Link to="/image-attributions">Image licenses</Link></nav></aside><article className="pm-legal-body">{published ? <><span className="pm-policy-state"><CheckCircle2 size={19}/> Operator-published version {published.version}</span><div className="pm-legal-published">{published.content}</div></> : <><span className="pm-policy-draft"><BookOpen size={19}/> Informational draft — requires operator/legal review and publication</span><p className="pm-policy-intro">{policy.intro}</p>{policy.sections.map(([heading,body])=><section key={heading}><h2>{heading}</h2><p>{body}</p></section>)}<p className="pm-legal-note">This is an informational draft, not the approved terms for a specific deployment. The responsible operator must review and publish an accurate final version in the Legal admin workspace.</p></>}
      {lawContext && <section className="pm-uganda-law" aria-label="Uganda statutory context">
        <span className="pm-kicker">UGANDAN LEGAL FRAMEWORK</span>
        <h2>Relevant statutory guidance</h2>
        <p>{lawContext.summary}</p>
        {lawContext.sections.map(([heading,body]) => <div className="pm-law-entry" key={heading}><h3>{heading}</h3><p>{body}</p></div>)}
        <h3>Primary legislation and regulations</h3>
        <ul className="pm-law-sources">{lawContext.sources.map(([label,url]) => <li key={url}><a href={url} target="_blank" rel="noopener noreferrer">{label} <ArrowRight size={14} aria-hidden="true"/></a></li>)}</ul>
        <p className="pm-law-review-note">General information only; not legal advice or a binding tenancy agreement. An authorised Uganda-qualified adviser should review operator-specific policies and tenancy documentation before publication.</p>
      </section>}</article></div></section></main>;
}

export function ImageAttributionsPage() {
  return <main className="pm-main"><section className="pm-section pm-license-page">
    <div className="pm-container"><span className="pm-kicker">MEDIA RIGHTS</span>
      <h1>Image sources & licenses</h1>
      <p>Photographs of Ugandan buildings are credited to their original Wikimedia Commons contributors. Responsive CSS cropping may alter the visible composition. These properties are not represented as KATS customers.</p>
      <ul>{PHOTOS.map(photo => <li key={photo.credit}><a href={photo.credit} target="_blank" rel="noopener noreferrer">{photo.author} — {photo.location}</a> · <a href={PHOTO_LICENSE} target="_blank" rel="noopener noreferrer">Creative Commons Attribution-ShareAlike 4.0</a> · Cropped for display</li>)}</ul>
      <Link to="/privacy" className="pm-text-link">Privacy and legal information <ArrowRight size={16}/></Link>
    </div>
  </section></main>;
}
