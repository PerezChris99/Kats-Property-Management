import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  ArrowRight, Bell, BookOpen, Building2, ChartNoAxesCombined, Check, CheckCircle2,
  ChevronLeft, ChevronRight, CreditCard, FileCheck2, FolderLock, KeyRound,
  Menu, ShieldCheck, Users, Wallet, Wrench, X
} from 'lucide-react';
import { api } from '../lib/api';
import { PHOTOS, PHOTO_LICENSE } from './media';
import { POLICY_LINKS, POLICY_PAGES } from './legal';
import './site.css';

const PRINCIPLES = [
  { icon: Building2, title: 'Owners', detail: 'Portfolio visibility.' },
  { icon: Users, title: 'Managers', detail: 'Units and operations.' },
  { icon: Wallet, title: 'Accountants', detail: 'Rent and expenses.' },
  { icon: Wrench, title: 'Caretakers', detail: 'Repairs and assignments.' },
  { icon: KeyRound, title: 'Tenants', detail: 'Leases and requests.' }
];
const FEATURES = [
  { icon: Building2, eyebrow: 'PROPERTIES', title: 'Buildings and rooms', body: 'Track properties, floors, rooms and occupancy.', note: 'Vacancies and availability at a glance.' },
  { icon: FileCheck2, eyebrow: 'LEASES', title: 'Tenancies and renewals', body: 'Manage leases, deposits, renewals and handovers.', note: 'Keep a clear tenancy history.' },
  { icon: CreditCard, eyebrow: 'RENT', title: 'Invoices and payments', body: 'Issue UGX invoices and review payment evidence.', note: 'Recorded does not mean verified.' },
  { icon: Wrench, eyebrow: 'MAINTENANCE', title: 'Requests and work orders', body: 'Log repairs, assign work and track progress.', note: 'Keep each issue visible.' },
  { icon: ChartNoAxesCombined, eyebrow: 'REPORTS', title: 'Portfolio reporting', body: 'Review occupancy, arrears, rent and expenses.', note: 'Based on recorded data.' },
  { icon: Users, eyebrow: 'ACCESS', title: 'Role-based workspaces', body: 'Separate views for owners, staff and tenants.', note: 'Permissions enforced by the API.' },
  { icon: FolderLock, eyebrow: 'DOCUMENTS', title: 'Rental documents', body: 'Connect documents to properties and leases.', note: 'Private storage needs setup.' },
  { icon: ShieldCheck, eyebrow: 'CONTROL', title: 'Approvals and audit trails', body: 'Review activity, permissions and reversals.', note: 'Accountable changes.' },
  { icon: Bell, eyebrow: 'INTEGRATIONS', title: 'Mobile money and fiscal', body: 'Provider-ready payment and tax workflows.', note: 'Approval and setup required.' }
];
const WORKFLOW = [
  { label: '01', icon: Building2, title: 'Add properties', body: 'Set up buildings, rooms and status.' },
  { label: '02', icon: KeyRound, title: 'Set up leases', body: 'Register tenants and their leases.' },
  { label: '03', icon: CreditCard, title: 'Run operations', body: 'Review rent and manage repairs.' },
  { label: '04', icon: ChartNoAxesCombined, title: 'Track results', body: 'Review reports and activity.' }
];
const FAQS = [
  ['Can I manage multiple buildings?', 'Yes. KATS supports multiple properties, buildings and rooms.'],
  ['Are all recorded payments verified?', 'No. Review and reconciliation are separate from recording a payment.'],
  ['Can tenants and caretakers sign in?', 'Yes, through role-specific workspaces with restricted access.'],
  ['Is mobile money or EFRIS built in?', 'Workflows are available. Live use requires provider approval and setup.'],
  ['Does local development need Docker?', 'No. SQLite preview is available; full infrastructure is needed for PostgreSQL and Celery testing.']
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
  const links = [
    ['/', 'Home'], ['/features', 'Features'], ['/how-it-works', 'How it works'],
    ['/about', 'About'], ['/request-access', 'Request access']
  ];
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
  return <footer className="pm-footer">
    <div className="pm-footer-body">
      <div className="pm-footer-brand"><Brand compact/><p>A clear view of your properties, rent and maintenance.</p></div>
      <div><h3>Explore</h3><Link to="/">Home</Link><Link to="/features">Features</Link><Link to="/how-it-works">How it works</Link><Link to="/about">About KATS</Link><Link to="/request-access">Request access</Link></div>
      <div><h3>Platform</h3><Link to="/login">Sign in</Link><Link to="/request-access">Request access</Link><Link to="/accessibility">Accessibility</Link></div>
      <div className="pm-footer-legal"><h3>Legal & trust</h3>{POLICY_LINKS.map(([name, slug]) => <Link to={'/' + slug} key={slug}>{name}</Link>)}</div>
    </div>
    <div className="pm-footer-base"><span>© {new Date().getFullYear()} KATS Property Management.</span><span>Ugandan residential photos · <a href={PHOTO_LICENSE} target="_blank" rel="noopener noreferrer">CC BY-SA 4.0</a> · No customer endorsement implied.</span></div><details className="pm-credits"><summary>Photo credits & license</summary><ul>{PHOTOS.map(photo => <li key={photo.credit}><a href={photo.credit} target="_blank" rel="noopener noreferrer">{photo.author} — {photo.location}</a> · <a href={PHOTO_LICENSE} target="_blank" rel="noopener noreferrer">CC BY-SA 4.0</a> · CSS cropped for layout</li>)}</ul></details>
  </footer>;
}

export function PublicShell({ user, logout }) {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'auto' }); document.title = pathname === '/' ? 'KATS · A clearer way to manage property' : 'KATS Property Management · ' + (pathname.slice(1).replaceAll('-', ' ') || 'Home'); }, [pathname]);
  return <div className="kats-public"><a className="pm-skip" href="#pm-content">Skip to content</a><PublicHeader user={user} logout={logout}/><div id="pm-content"><Outlet/></div><PublicFooter/></div>;
}

function SectionTitle({ eyebrow, title, text, center = false }) {
  return <div className={'pm-section-title' + (center ? ' is-centered' : '')}><span className="pm-kicker">{eyebrow}</span><h2>{title}</h2>{text && <p>{text}</p>}</div>;
}
function Photo({ photo, className = '' }) {
  return <figure className={'pm-photo ' + className}><img loading="lazy" src={photo.url} alt={photo.alt}/><figcaption><a href={photo.credit} target="_blank" rel="noopener noreferrer">{photo.location} · {photo.author}</a></figcaption></figure>;
}
function AccessCallout({ title = 'Your portfolio, finally in one place.', description = 'Bring properties, rent and daily operations into a clearer workspace.' }) {
  return <section className="pm-endcap" aria-label="Get started with KATS">
    <div className="pm-container pm-endcap-inner">
      <div className="pm-endcap-copy">
        <span className="pm-kicker">GET STARTED</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="pm-endcap-actions">
        <Link className="pm-endcap-primary" to="/request-access">Request access <ArrowRight size={18} aria-hidden="true"/></Link>
        <span>Already registered? <Link to="/login">Sign in</Link></span>
      </div>
    </div>
  </section>;
}
function HeroCarousel({ user }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const heroRef = useRef(null);
  const { pathname } = useLocation();
  const raf = useRef(0);
  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reduceMotion.matches || paused) return undefined;
    const advance = () => { if (!document.hidden) setIndex(n => (n + 1) % PHOTOS.length); };
    const timer = window.setInterval(advance, 6500);
    return () => window.clearInterval(timer);
  }, [paused, pathname]);
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
  function move(by) { setIndex(n => (n + by + PHOTOS.length) % PHOTOS.length); }
  return <section ref={heroRef} className="pm-hero" aria-label="Property management introduction" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={e => { if (!e.currentTarget.contains(e.relatedTarget)) setPaused(false); }}>
    <div className="pm-hero-images" aria-hidden="true">{PHOTOS.map((item, n) => <div className={'pm-slide' + (n === index ? ' is-current' : '')} key={item.url} style={{ backgroundImage: 'url("' + item.url + '")' }}/>)}</div>
    <div className="pm-hero-shade"/>
    <div className="pm-hero-inner"><div className="pm-hero-copy"><span className="pm-kicker pm-kicker-light"><span className="pm-spark" /> BUILT FOR UGANDAN RENTALS</span><h1>Manage property. <em>Know the full picture.</em></h1><p>Manage units, leases, rent and repairs in one place.</p><div className="pm-hero-actions"><Link className="pm-cta pm-cta-yellow" to={user ? '/dashboard' : '/request-access'}>{user ? 'Open workspace' : 'Request access'} <ArrowRight size={18}/></Link><Link className="pm-cta pm-cta-ghost" to="/how-it-works">How it works</Link></div><div className="pm-hero-points"><span><Check size={15}/> UGX rent records</span><span><Check size={15}/> Secure role access</span></div></div></div>
    <div className="pm-carousel-bottom"><div className="pm-carousel-controls"><button onClick={() => move(-1)} aria-label="Previous residential photo"><ChevronLeft/></button><span className="pm-carousel-count">0{index + 1} / 0{PHOTOS.length}</span><button onClick={() => move(1)} aria-label="Next residential photo"><ChevronRight/></button></div><div className="pm-carousel-dots" aria-label="Choose a residential photo">{PHOTOS.map((p, n) => <button type="button" key={p.credit} aria-label={'Show photo ' + (n + 1)} aria-current={index === n ? 'true' : undefined} onClick={() => setIndex(n)} className={index === n ? 'is-current' : ''}/>)}</div><a className="pm-hero-credit" href={PHOTOS[index].credit} target="_blank" rel="noopener noreferrer">{PHOTOS[index].location} · {PHOTOS[index].author}</a></div>
  </section>;
}

function TrustBand() {
  return <section className="pm-role-strip"><div className="pm-container"><span>One management system. Role-specific access.</span><div>{PRINCIPLES.map(({ title }) => <span key={title}>{title}</span>)}</div></div></section>;
}
function Problems() {
  const items = [
    'Rent spread across spreadsheets',
    'Repairs lost in messages',
    'Unclear vacancies and arrears',
    'Access not matched to roles'
  ];
  return <section className="pm-section pm-problem"><div className="pm-container pm-split"><div className="pm-problem-photo"><Photo photo={PHOTOS[3]}/></div><div><SectionTitle eyebrow="THE PROBLEM" title="Property work shouldn't be guesswork." text="Scattered records slow everyone down."/><ul className="pm-check-list pm-problem-list">{items.map(x => <li key={x}><Check size={18}/>{x}</li>)}</ul></div></div></section>;
}
function Solution() {
  return <section className="pm-section pm-solution"><div className="pm-container pm-split"><div><SectionTitle eyebrow="THE KATS APPROACH" title="One connected workspace." text="Link properties, leases, rent and repairs."/><div className="pm-solution-list">{[
    ['01', 'Know your units', 'Track vacancy and occupancy.'],
    ['02', 'Review rent', 'Separate invoices from verified payments.'],
    ['03', 'Manage repairs', 'Assign and track work.']
  ].map(([n,t,b])=><div key={n}><span>{n}</span><div><h3>{t}</h3><p>{b}</p></div></div>)}</div><Link to="/features" className="pm-text-link">View capabilities <ArrowRight size={18}/></Link></div><Photo photo={PHOTOS[1]} className="pm-solution-photo"/></div></section>;
}
function HowSteps({ title = 'From setup to daily operations.', short = false }) {
  return <section className={'pm-section pm-how ' + (short ? 'pm-how-short' : '')} id="how"><div className="pm-container"><SectionTitle center eyebrow="HOW IT WORKS" title={title} text="Four steps to organized property work."/><div className="pm-step-grid">{WORKFLOW.map(({label,icon:Icon,title:stepTitle,body})=><article key={label}><div className="pm-step-top"><span>{label}</span><Icon size={22}/></div><h3>{stepTitle}</h3><p>{body}</p></article>)}</div></div></section>;
}
function FAQ({ items = FAQS }) {
  return <section className="pm-section pm-faq"><div className="pm-container pm-faq-grid"><div><SectionTitle eyebrow="FAQ" title="Questions, answered." text="The essentials, without the jargon."/><Photo photo={PHOTOS[4]} className="pm-faq-photo"/></div><div className="pm-faq-items">{items.map(([q,answer])=><details key={q}><summary>{q}<span className="pm-faq-plus" aria-hidden="true">+</span></summary><p>{answer}</p></details>)}</div></div></section>;
}
export function LandingPage({ user }) {
  return <main className="pm-main"><HeroCarousel user={user}/><TrustBand/><Problems/><Solution/><HowSteps short/><FAQ/><AccessCallout/></main>;
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
export function FeaturesPage() {
  return <main className="pm-main"><PageHero eyebrow="THE PLATFORM" title="Everything you need to manage rentals." text="Keep units, tenants, rent and repairs organized." photo={PHOTOS[2]}/>
    <section className="pm-section"><div className="pm-container"><SectionTitle eyebrow="AT A GLANCE" title="What KATS helps you manage" text="Practical property workflows."/><div className="pm-feature-grid">{FEATURES.map(({icon:Icon,eyebrow,title,body,note})=><article className="pm-feature-card" key={title}><Icon size={23} aria-hidden="true"/><span className="pm-card-eyebrow">{eyebrow}</span><h3>{title}</h3><p>{body}</p><small className="pm-feature-note">{note}</small></article>)}</div></div></section>
    <section className="pm-section pm-feature-focus"><div className="pm-container pm-split"><div><SectionTitle eyebrow="FINANCIAL CONFIDENCE" title="Recorded isn't the same as received." text="Review collections before counting them as paid."/><ul className="pm-check-list"><li><CheckCircle2/> Rent invoices and UGX totals</li><li><CheckCircle2/> Cash custody and review workflows</li><li><CheckCircle2/> Arrears and reconciled financial summaries</li></ul><Link to="/request-access" className="pm-text-link">Request access <ArrowRight size={18}/></Link></div><Photo photo={PHOTOS[0]}/></div></section>
    </main>;
}

export function HowItWorksPage() {
  return <main className="pm-main"><PageHero eyebrow="A SIMPLE START" title="A clear path from setup to operations." text="Four steps for a working rental portfolio." photo={PHOTOS[1]}/><HowSteps title="Four connected steps."/><section className="pm-section pm-feature-focus"><div className="pm-container pm-split"><Photo photo={PHOTOS[0]}/><div><SectionTitle eyebrow="AFTER SETUP" title="Stay in control as you grow." text="Keep rooms, records and tasks up to date."/><ul className="pm-check-list"><li><CheckCircle2/> Adjust rooms, occupancy and tenancy records</li><li><CheckCircle2/> See approvals, maintenance and review queues</li><li><CheckCircle2/> Export available financial and portfolio reports</li></ul></div></div></section></main>;
}

function ChartLine({ values, color = '#188ad0', label }) {
  const width = 420, height = 150, min = Math.min(...values) - 2, max = Math.max(...values) + 2;
  const coords = values.map((v,i) => [22 + i * (width - 44) / (values.length - 1), 15 + (max-v)/(max-min)*(height-38)]);
  const d = coords.map(([x,y],i)=>(i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1)).join(' ');
  return <svg className="pm-chart-line" viewBox={'0 0 '+width+' '+height} role="img" aria-label={label}><path d="M22 25H398M22 66H398M22 107H398M22 127H398" fill="none" stroke="#dbe8f2" strokeWidth="1.5"/><path d={d} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>{coords.map(([x,y],i)=><circle cx={x} cy={y} key={i} r="4" fill="#fff" stroke={color} strokeWidth="2.5"/>)}</svg>;
}
function ChartPanel({ title, subtitle, children, foot }) {
  return <article className="pm-chart-panel"><h3>{title}</h3><p>{subtitle}</p>{children}<span className="pm-chart-foot">{foot}</span></article>;
}
function OperationalCharts() {
  return <section className="pm-section pm-about-charts"><div className="pm-container"><SectionTitle eyebrow="WHAT GOOD RECORDS MAKE POSSIBLE" title="See the trends that matter." text="Example charts only — not actual customer results."/><div className="pm-chart-grid">
    <ChartPanel title="Occupancy trend" subtitle="Example occupied units as a percentage of available units" foot="Illustrative 6-month trend"><ChartLine values={[82,85,84,88,90,91]} label="Sample occupancy rises from 82 to 91 percent over six months"/><div className="pm-chart-axis">Jan <span>Feb</span><span>Mar</span><span>Apr</span><span>May</span><span>Jun</span></div></ChartPanel>
    <ChartPanel title="Rent collection review" subtitle="Example of recorded invoices and reviewed collections" foot="Illustrative approval distribution"><div className="pm-chart-bars">{[['Reviewed',75],['Pending',18],['Needs follow-up',7]].map(([label,num])=><div key={label}><span>{label}</span><div className="pm-bar-track"><span style={{width:num+'%'}}/></div><strong>{num}%</strong></div>)}</div></ChartPanel>
    <ChartPanel title="Maintenance queue" subtitle="Example distribution of open work items by status" foot="Illustrative work-order mix"><div className="pm-donut-layout"><div className="pm-donut"><strong>Work</strong><small>queue</small></div><div className="pm-donut-key"><span><i className="pm-key-blue"/>Assigned · 45%</span><span><i className="pm-key-sky"/>In progress · 35%</span><span><i className="pm-key-gold"/>New · 20%</span></div></div></ChartPanel>
  </div><p className="pm-data-note"><ShieldCheck size={18}/> Live reports are private to authorized users.</p></div></section>;
}
export function AboutPage() {
  return <main className="pm-main"><PageHero eyebrow="ABOUT KATS" title="Built for property teams." text="Clear records. Better decisions." photo={PHOTOS[0]}/><section className="pm-section"><div className="pm-container pm-split"><div><SectionTitle eyebrow="OUR PURPOSE" title="Keep everyone informed." text="Give each role the information it needs."/><p className="pm-long-copy">Built around Ugandan rental workflows, UGX records and accountable teams.</p></div><Photo photo={PHOTOS[3]}/></div></section><OperationalCharts/><AccessCallout title="A better view of your day-to-day property work."/></main>;
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
  return <main className="pm-main"><PageHero eyebrow="REQUEST ACCESS" title="Get access to KATS." text="Request an account for an existing property operation. An administrator reviews every request." photo={PHOTOS[2]}/>
    <section className="pm-section pm-request-section" aria-labelledby="pm-request-heading"><div className="pm-container pm-request-layout">
      <div className="pm-contact-form">
        <div className="pm-request-form-head"><span className="pm-form-index">01 / REQUEST</span><span className="pm-request-security"><ShieldCheck size={15} aria-hidden="true"/> Reviewed by an administrator</span></div>
        <div className="pm-section-title"><span className="pm-kicker">YOUR DETAILS</span><h2 id="pm-request-heading">Request your workspace.</h2><p>Share a few details. We’ll route your request for review.</p></div>
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
  const [published,setPublished]=useState(null);
  useEffect(()=>{
    let live=true;setPublished(null);
    api('public/legal/'+slug).then(result=>{if(live && result.page?.content) setPublished(result.page);}).catch(()=>{});
    return ()=>{live=false;};
  },[slug]);
  if(!policy) return <main className="pm-section"><div className="pm-container"><h1>Page not found</h1><Link to="/">Return home</Link></div></main>;
  return <main className="pm-main"><PageHero eyebrow="LEGAL & TRUST" title={published?.title || policy.title} text={published ? 'Operator-published policy · version '+published.version : policy.intro} photo={PHOTOS[3]}/><section className="pm-section pm-legal-section"><div className="pm-container pm-legal-layout"><aside><span className="pm-kicker">LEGAL LIBRARY</span><nav aria-label="Other legal pages">{POLICY_LINKS.map(([label,s])=><Link key={s} aria-current={slug===s?'page':undefined} to={'/'+s}>{label}</Link>)}</nav></aside><article className="pm-legal-body">{published ? <><span className="pm-policy-state"><CheckCircle2 size={19}/> Operator-published version {published.version}</span><div className="pm-legal-published">{published.content}</div></> : <><span className="pm-policy-draft"><BookOpen size={19}/> Informational draft — requires operator/legal review and publication</span><p className="pm-policy-intro">{policy.intro}</p>{policy.sections.map(([heading,body])=><section key={heading}><h2>{heading}</h2><p>{body}</p></section>)}<p className="pm-legal-note">This is an informational draft, not the approved terms for a specific deployment. The responsible operator must review and publish an accurate final version in the Legal admin workspace.</p></>}</article></div></section></main>;
}
