import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  ArrowDown, ArrowRight, ArrowUpRight, Bell, BookOpen, Building2, CalendarDays,
  ChartNoAxesCombined, Check, CheckCircle2, ChevronLeft, ChevronRight, CircleHelp,
  CreditCard, FileCheck2, FolderLock, KeyRound, Mail, Menu, SearchCheck,
  ShieldCheck, Users, Wallet, Wrench, X
} from 'lucide-react';
import { api } from '../lib/api';
import { PHOTOS, PHOTO_LICENSE } from './media';
import { POLICY_LINKS, POLICY_PAGES } from './legal';
import './site.css';

const PRINCIPLES = [
  { icon: Building2, title: 'Owners', detail: 'See the portfolio and the records behind each decision.' },
  { icon: Users, title: 'Managers', detail: 'Keep occupancy, teams and maintenance organized.' },
  { icon: Wallet, title: 'Accountants', detail: 'Reconcile invoices, collections and expenses.' },
  { icon: Wrench, title: 'Caretakers', detail: 'Act on assigned rooms and maintenance work.' },
  { icon: KeyRound, title: 'Tenants', detail: 'See lease details, balances and requests.' }
];
const FEATURES = [
  { icon: Building2, eyebrow: 'PROPERTY RECORDS', title: 'Property and room hierarchy', body: 'Organize properties, buildings, floors and rooms without losing the relationships between them.', note: 'Track occupied, vacant and maintenance states in one place.' },
  { icon: FileCheck2, eyebrow: 'TENANCIES', title: 'Leases and renewals', body: 'Connect tenants to rooms and lease periods, manage renewals, deposits, amendments and documented handovers.', note: 'Keep a traceable history of tenancy changes.' },
  { icon: CreditCard, eyebrow: 'RENT OPERATIONS', title: 'Invoice and payment review', body: 'Issue rent invoices in UGX, record cash and bank transfers, confirm evidence, and control reversals.', note: 'Unverified cash is never presented as collected.' },
  { icon: Wrench, eyebrow: 'MAINTENANCE', title: 'Requests and work orders', body: 'Log issues, assign work, set priorities and follow progress across rooms and properties.', note: 'Avoid leaving repairs buried in chat messages.' },
  { icon: ChartNoAxesCombined, eyebrow: 'REPORTING', title: 'Portfolio and financial reports', body: 'Review occupancy, invoices, outstanding rent, expenses and period-based summaries with export options.', note: 'Figures reflect recorded data after sign-in.' },
  { icon: Users, eyebrow: 'ACCESS', title: 'Purpose-built role workspaces', body: 'Dedicated permissions for owners, managers, accountants, caretakers and tenants reduce unnecessary exposure.', note: 'Access decisions are enforced by the backend.' },
  { icon: FolderLock, eyebrow: 'DOCUMENTS', title: 'Controlled document workflows', body: 'Associate rental documents and inspection evidence with the right record using private storage integrations.', note: 'External object storage requires configuration.' },
  { icon: ShieldCheck, eyebrow: 'CONTROL', title: 'Review, audit and recovery', body: 'Manage approvals, activity records, administrative permissions, privacy requests and account security.', note: 'Designed around accountable operational decisions.' },
  { icon: Bell, eyebrow: 'OPTIONAL INTEGRATIONS', title: 'Payment and fiscal readiness', body: 'Dedicated workflows for mobile-money and fiscal submissions when the relevant providers are connected.', note: 'MTN, Airtel and URA integrations require provider approval.' }
];
const WORKFLOW = [
  { label: '01', icon: Building2, title: 'Structure your portfolio', body: 'Add properties, buildings, units and their current status.' },
  { label: '02', icon: KeyRound, title: 'Connect people and leases', body: 'Register tenants, accounts and lease details with the right access.' },
  { label: '03', icon: CreditCard, title: 'Run daily operations', body: 'Issue invoices, review collections and assign maintenance.' },
  { label: '04', icon: ChartNoAxesCombined, title: 'See the full picture', body: 'Use reports and activity records to make informed decisions.' }
];
const FAQS = [
  ['Is KATS designed for just one building?', 'No. It can model multiple properties with buildings, floors and rooms, and keeps related tenancy and financial records organized.'],
  ['Does a recorded cash payment mean the money is confirmed?', 'Not necessarily. Cash and bank workflows distinguish pending records from independently reviewed and reconciled payments.'],
  ['Can tenants and caretakers sign in?', 'Yes. They receive role-specific workspaces and are restricted to their authorized information and assignments.'],
  ['Does KATS process mobile money and URA EFRIS automatically?', 'The system includes integration workflows, but real transactions depend on provider credentials, onboarding, verification and a configured production environment.'],
  ['Can I explore KATS without Docker?', 'Yes. A separate SQLite preview supports local UI and API development. Full PostgreSQL access controls and Redis/Celery background processing require the full development stack.']
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
    ['/about', 'About'], ['/contact', 'Contact']
  ];
  return <header className="pm-header">
    <div className="pm-header-inner">
      <Brand />
      <button className="pm-menu-trigger" type="button" aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} aria-controls="pm-main-nav" onClick={() => setOpen(v => !v)}>{open ? <X/> : <Menu/>}</button>
      <nav id="pm-main-nav" className={'pm-nav' + (open ? ' is-open' : '')} aria-label="Main navigation">
        {links.map(([to, label]) => <NavLink end key={to} to={to} className={({isActive}) => isActive ? 'is-active' : ''}>{label}</NavLink>)}
        <span className="pm-nav-separator" aria-hidden="true"/>
        {user ? <><Link to="/dashboard">Workspace</Link><button type="button" className="pm-nav-signout" onClick={logout}>Sign out</button></> : <Link to="/login" className="pm-nav-login"><KeyRound size={16}/> Sign in</Link>}
        <Link to={user ? '/dashboard' : '/contact'} className="pm-cta pm-cta-yellow pm-nav-cta">{user ? 'Open workspace' : 'Request access'} <ArrowRight size={17}/></Link>
      </nav>
    </div>
  </header>;
}

function PublicFooter() {
  return <footer className="pm-footer">
    <div className="pm-footer-body">
      <div className="pm-footer-brand"><Brand compact/><p>A clear view of your properties, rent and maintenance.</p></div>
      <div><h3>Explore</h3><Link to="/">Home</Link><Link to="/features">Features</Link><Link to="/how-it-works">How it works</Link><Link to="/about">About KATS</Link><Link to="/contact">Contact</Link></div>
      <div><h3>Platform</h3><Link to="/login">Sign in</Link><Link to="/contact">Request a walkthrough</Link><Link to="/pricing">Pricing inquiries</Link><Link to="/accessibility">Accessibility</Link></div>
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
function CTABanner({ title = 'Bring your whole property operation into focus.', description = 'Get a walkthrough of the workflows that matter to your portfolio.' }) {
  return <section className="pm-final-cta"><div className="pm-final-graphic" aria-hidden="true"><Building2 size={150} strokeWidth={0.9}/></div><div><span className="pm-kicker">NEXT STEP</span><h2>{title}</h2><p>{description}</p></div><Link className="pm-cta pm-cta-yellow" to="/contact">Request a walkthrough <ArrowUpRight size={19}/></Link></section>;
}
function MiniDashboard() {
  return <div className="pm-product-preview" aria-label="Illustrative KATS dashboard layout, not live account information">
    <div className="pm-product-top"><span className="pm-preview-mark"><Building2 size={17}/> KATS / Overview</span><span>Illustrative interface</span></div>
    <div className="pm-preview-kpis"><div><small>Properties</small><strong>Portfolio</strong></div><div><small>Rent</small><strong>Review</strong></div><div><small>Maintenance</small><strong>Track</strong></div></div>
    <div className="pm-preview-panels"><div><span>Recorded monthly activity</span><svg viewBox="0 0 370 120" role="img" aria-label="Illustrative rising activity chart"><path d="M0 100 55 77 110 87 160 50 220 60 275 37 335 20 370 22" fill="none" stroke="#2a9bdb" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/><path d="M0 100 55 77 110 87 160 50 220 60 275 37 335 20 370 22V120H0Z" fill="rgba(56,189,248,.15)"/></svg><small>Example visualization — not actual portfolio data</small></div><div><span>Work queue</span>{['Rent review', 'Lease renewal', 'Repair request'].map((item, i) => <p key={item}><span className={'pm-preview-dot pm-preview-dot-' + i}/>{item}<CheckCircle2 size={16}/></p>)}</div></div>
  </div>;
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
    // Smooth compositor-layer parallax; avoids re-rendering five photo slides.
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const hero = heroRef.current;
    if (!hero || reduceMotion.matches) return undefined;
    let current = 0;
    let target = 0;
    let live = true;
    function tick() {
      raf.current = 0;
      if (!live) return;
      const bounds = hero.getBoundingClientRect();
      if (bounds.bottom <= 0 || bounds.top >= window.innerHeight) return;
      target = Math.max(-95, Math.min(95, -bounds.top * 0.20));
      current += (target - current) * 0.22;
      hero.style.setProperty('--pm-parallax-y', current.toFixed(2) + 'px');
      if (Math.abs(target - current) > 0.4) raf.current = window.requestAnimationFrame(tick);
    }
    function onScroll() {
      if (!raf.current) raf.current = window.requestAnimationFrame(tick);
    }
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      live = false;
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      window.cancelAnimationFrame(raf.current);
      hero.style.removeProperty('--pm-parallax-y');
    };
  }, []);
  function move(by) { setIndex(n => (n + by + PHOTOS.length) % PHOTOS.length); }
  return <section ref={heroRef} className="pm-hero" aria-label="Property management introduction" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={e => { if (!e.currentTarget.contains(e.relatedTarget)) setPaused(false); }}>
    <div className="pm-hero-images" aria-hidden="true">{PHOTOS.map((item, n) => <div className={'pm-slide' + (n === index ? ' is-current' : '')} key={item.url} style={{ backgroundImage: 'url("' + item.url + '")' }}/>)}</div>
    <div className="pm-hero-shade"/>
    <div className="pm-hero-inner"><div className="pm-glass pm-hero-panel"><span className="pm-kicker pm-kicker-light"><span className="pm-spark" /> BUILT FOR UGANDAN RENTALS</span><h1>Manage property. <em>Know the full picture.</em></h1><p>Manage units, leases, rent and repairs in one place.</p><div className="pm-hero-actions"><Link className="pm-cta pm-cta-yellow" to={user ? '/dashboard' : '/contact'}>{user ? 'Open workspace' : 'Request a walkthrough'} <ArrowRight size={19}/></Link><Link className="pm-cta pm-cta-ghost" to="/how-it-works">See how it works <ArrowDown size={17}/></Link></div><div className="pm-hero-points"><span><Check size={15}/> UGX rent records</span><span><Check size={15}/> Secure role access</span></div></div></div>
    <div className="pm-carousel-bottom"><div className="pm-carousel-controls"><button onClick={() => move(-1)} aria-label="Previous residential photo"><ChevronLeft/></button><span className="pm-carousel-count">0{index + 1} / 0{PHOTOS.length}</span><button onClick={() => move(1)} aria-label="Next residential photo"><ChevronRight/></button></div><div className="pm-carousel-dots" aria-label="Choose a residential photo">{PHOTOS.map((p, n) => <button type="button" key={p.credit} aria-label={'Show photo ' + (n + 1)} aria-current={index === n ? 'true' : undefined} onClick={() => setIndex(n)} className={index === n ? 'is-current' : ''}/>)}</div><a className="pm-hero-credit" href={PHOTOS[index].credit} target="_blank" rel="noopener noreferrer">{PHOTOS[index].location} · {PHOTOS[index].author}</a></div>
  </section>;
}

function TrustBand() {
  return <section className="pm-trust" aria-labelledby="pm-trust-heading"><div className="pm-container"><div className="pm-trust-heading"><span className="pm-kicker">THE PEOPLE BEHIND EVERY PROPERTY</span><h2 id="pm-trust-heading">One system. Five different perspectives.</h2><p>Designed for real operational roles, not one generic dashboard.</p></div><div className="pm-trust-grid">{PRINCIPLES.map(({icon: Icon, title, detail}) => <article key={title}><Icon size={26}/><h3>{title}</h3><p>{detail}</p></article>)}</div></div></section>;
}
function Problems() {
  const items = [
    'Rent details scattered across notebooks and spreadsheets',
    'Maintenance requests lost between calls and messages',
    'Unclear room status and overdue invoice visibility',
    'Teams with different responsibilities sharing the same information'
  ];
  return <section className="pm-section pm-problem"><div className="pm-container pm-split"><div className="pm-problem-photo"><Photo photo={PHOTOS[3]}/><span className="pm-image-stamp"><SearchCheck size={19}/> Clarity where it counts</span></div><div><SectionTitle eyebrow="THE PROBLEM" title="Properties are complex enough. Your workflow shouldn't be." text="When records are fragmented, even simple questions take too long to answer."/><ul className="pm-check-list pm-problem-list">{items.map(x => <li key={x}><CircleHelp size={21}/>{x}</li>)}</ul></div></div></section>;
}
function Solution() {
  return <section className="pm-section pm-solution"><div className="pm-container pm-split"><div><SectionTitle eyebrow="THE KATS APPROACH" title="Everything connected. Nothing buried." text="Keep each property, lease, payment review and maintenance task linked to the right context."/><div className="pm-solution-list">{[
    ['01', 'Know your inventory', 'See structures and room states at a glance.'],
    ['02', 'Trust the rent records', 'Distinguish invoices, collections and approval status.'],
    ['03', 'Keep work moving', 'Assign and review maintenance with accountability.']
  ].map(([n,t,b])=><div key={n}><span>{n}</span><div><h3>{t}</h3><p>{b}</p></div></div>)}</div><Link to="/features" className="pm-text-link">Explore KATS capabilities <ArrowRight size={18}/></Link></div><MiniDashboard/></div></section>;
}
function HowSteps({ title = 'From your first property to a clearer day-to-day.', short = false }) {
  return <section className={'pm-section pm-how ' + (short ? 'pm-how-short' : '')} id="how"><div className="pm-container"><SectionTitle center eyebrow="HOW IT WORKS" title={title} text="A straightforward workflow grounded in what property teams actually do."/><div className="pm-step-grid">{WORKFLOW.map(({label,icon:Icon,title:stepTitle,body})=><article key={label}><div className="pm-step-top"><span>{label}</span><Icon size={27}/></div><h3>{stepTitle}</h3><p>{body}</p></article>)}</div></div></section>;
}
function FAQ({ items = FAQS }) {
  return <section className="pm-section pm-faq"><div className="pm-container pm-faq-grid"><div><SectionTitle eyebrow="FAQ" title="Good questions deserve clear answers." text="A few things worth knowing before getting started."/><Photo photo={PHOTOS[4]} className="pm-faq-photo"/></div><div className="pm-faq-items">{items.map(([q,answer])=><details key={q}><summary>{q}<span className="pm-faq-plus" aria-hidden="true">+</span></summary><p>{answer}</p></details>)}</div></div></section>;
}
export function LandingPage({ user }) {
  return <main className="pm-main"><HeroCarousel user={user}/><TrustBand/><Problems/><Solution/><HowSteps short/><FAQ/><div className="pm-container pm-cta-wrap"><CTABanner/></div></main>;
}

function PageHero({ eyebrow, title, text, photo = PHOTOS[0], children }) {
  return <section className="pm-page-hero"><div className="pm-page-hero-image" style={{backgroundImage: 'linear-gradient(90deg,rgba(7,24,49,.88),rgba(7,28,55,.42)),url("' + photo.url + '")'}}/><div className="pm-container pm-page-hero-inner"><span className="pm-kicker pm-kicker-light">{eyebrow}</span><h1>{title}</h1><p>{text}</p>{children}</div></section>;
}
export function FeaturesPage() {
  return <main className="pm-main"><PageHero eyebrow="THE PLATFORM" title="The practical tools behind a better-run property." text="Purpose-built workflows for leases, rent operations, repairs and oversight — without disconnected systems." photo={PHOTOS[2]}><Link className="pm-cta pm-cta-yellow" to="/contact">Talk through your workflow <ArrowRight size={18}/></Link></PageHero>
    <section className="pm-section"><div className="pm-container"><SectionTitle eyebrow="AT A GLANCE" title="What KATS helps you manage" text="No inflated promises, no invented automation. These are the product workflows."/><div className="pm-feature-grid">{FEATURES.map(({icon:Icon,eyebrow,title,body,note})=><article className="pm-feature-card" key={title}><div className="pm-feature-icon"><Icon size={27}/></div><span className="pm-card-eyebrow">{eyebrow}</span><h3>{title}</h3><p>{body}</p><div className="pm-feature-note"><CheckCircle2 size={16}/>{note}</div></article>)}</div></div></section>
    <section className="pm-section pm-feature-focus"><div className="pm-container pm-split"><div><SectionTitle eyebrow="FINANCIAL CONFIDENCE" title="Know the difference between recorded and received." text="A rental business depends on getting its money story right. Review evidence before applying verified collections to invoices, and preserve an audit trail when a transaction changes."/><ul className="pm-check-list"><li><CheckCircle2/> Rent invoices and UGX totals</li><li><CheckCircle2/> Cash custody and review workflows</li><li><CheckCircle2/> Arrears and reconciled financial summaries</li></ul><Link to="/contact" className="pm-text-link">See this workflow <ArrowRight size={18}/></Link></div><MiniDashboard/></div></section>
    <div className="pm-container pm-cta-wrap"><CTABanner title="Put your property records on the same page." description="We can walk through roles, workflows and the integrations your business actually needs."/></div></main>;
}

export function HowItWorksPage() {
  return <main className="pm-main"><PageHero eyebrow="A SIMPLE START" title="From property records to daily control." text="KATS follows the real sequence of setting up and operating a rental portfolio." photo={PHOTOS[1]}/><HowSteps title="Four connected stages. One clear process."/><section className="pm-section pm-feature-focus"><div className="pm-container pm-split"><Photo photo={PHOTOS[0]}/><div><SectionTitle eyebrow="AFTER SETUP" title="Keep your information useful as the portfolio grows." text="Use role-appropriate views, maintain up-to-date records, track what needs attention and review outcomes from your workspace."/><ul className="pm-check-list"><li><CheckCircle2/> Adjust rooms, occupancy and tenancy records</li><li><CheckCircle2/> See approvals, maintenance and review queues</li><li><CheckCircle2/> Export available financial and portfolio reports</li></ul></div></div></section><div className="pm-container pm-cta-wrap"><CTABanner/></div></main>;
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
  return <section className="pm-section pm-about-charts"><div className="pm-container"><SectionTitle eyebrow="WHAT GOOD RECORDS MAKE POSSIBLE" title="Better decisions start with a clear view." text="Illustrative sample data shows the kinds of trends property teams can investigate. These are not KATS customer results or performance claims."/><div className="pm-chart-grid">
    <ChartPanel title="Occupancy trend" subtitle="Example occupied units as a percentage of available units" foot="Illustrative 6-month trend"><ChartLine values={[82,85,84,88,90,91]} label="Sample occupancy rises from 82 to 91 percent over six months"/><div className="pm-chart-axis">Jan <span>Feb</span><span>Mar</span><span>Apr</span><span>May</span><span>Jun</span></div></ChartPanel>
    <ChartPanel title="Rent collection review" subtitle="Example of recorded invoices and reviewed collections" foot="Illustrative approval distribution"><div className="pm-chart-bars">{[['Reviewed',75],['Pending',18],['Needs follow-up',7]].map(([label,num])=><div key={label}><span>{label}</span><div className="pm-bar-track"><span style={{width:num+'%'}}/></div><strong>{num}%</strong></div>)}</div></ChartPanel>
    <ChartPanel title="Maintenance queue" subtitle="Example distribution of open work items by status" foot="Illustrative work-order mix"><div className="pm-donut-layout"><div className="pm-donut"><strong>Work</strong><small>queue</small></div><div className="pm-donut-key"><span><i className="pm-key-blue"/>Assigned · 45%</span><span><i className="pm-key-sky"/>In progress · 35%</span><span><i className="pm-key-gold"/>New · 20%</span></div></div></ChartPanel>
  </div><p className="pm-data-note"><ShieldCheck size={18}/> Live, customer-specific reports appear only inside authorized workspaces. Public examples never expose tenant or financial records.</p></div></section>;
}
export function AboutPage() {
  return <main className="pm-main"><PageHero eyebrow="ABOUT KATS" title="Property operations built around people." text="A practical system for turning scattered rental information into organized, accountable work." photo={PHOTOS[0]}/><section className="pm-section"><div className="pm-container pm-split"><div><SectionTitle eyebrow="OUR PURPOSE" title="Give every property decision the right context." text="Property owners need visibility. Managers need operational control. Tenants need reliable follow-through. KATS connects those responsibilities without making everyone use the same screen."/><p className="pm-long-copy">The platform focuses on inventory, tenancies, invoices, verified rent records, maintenance and reporting. It is designed around the everyday realities of rental administration, including UGX-denominated records and distinct staff responsibilities.</p></div><Photo photo={PHOTOS[3]}/></div></section><TrustBand/><OperationalCharts/><section className="pm-section pm-about-values"><div className="pm-container"><SectionTitle eyebrow="OUR DESIGN PRINCIPLES" title="A working tool, not a decorative dashboard."/><div className="pm-values-grid">{[['Clarity','Show what is due, what is paid and what still needs review.'],['Accountability','Keep actions connected to roles, records and evidence.'],['Privacy','Keep access scoped to the work each person is authorized to do.'],['Practicality','Fit actual property workflows before adding complexity.']].map(([name,desc])=><article key={name}><CheckCircle2 size={26}/><h3>{name}</h3><p>{desc}</p></article>)}</div></div></section><div className="pm-container pm-cta-wrap"><CTABanner title="The right foundation for a better-run portfolio."/></div></main>;
}

export function ContactPage() {
  const blank={ full_name:'', email:'', phone:'', company:'', role:'', subject:'DEMO', message:'', consent:false, website:'' };
  const [values,setValues]=useState(blank);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [success,setSuccess]=useState('');
  const change=(key,val)=>setValues(v=>({...v,[key]:val}));
  async function submit(e) {
    e.preventDefault();setBusy(true);setError('');setSuccess('');
    const note=[values.company.trim() && 'Organization: '+values.company.trim(), values.role && 'Role: '+values.role, values.message.trim()].filter(Boolean).join('\n');
    try {
      const result=await api('public/contact-requests',{method:'POST',body:JSON.stringify({
        full_name:values.full_name.trim(),email:values.email.trim(),phone:values.phone.trim(),
        subject:values.subject,message:note,consent:values.consent,website:values.website
      })});
      setSuccess(result.message || 'Your request has been recorded.');
      setValues(blank);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to submit this request.'); }
    finally {setBusy(false);}
  }
  return <main className="pm-main"><PageHero eyebrow="CONTACT" title="Let's talk about your properties." text="Tell us what you manage and the workflows you want to simplify. Your inquiry goes directly into the KATS contact queue." photo={PHOTOS[4]}/><section className="pm-section"><div className="pm-container pm-contact-grid"><div className="pm-contact-form"><SectionTitle eyebrow="SEND AN INQUIRY" title="A few details. A useful conversation." text="Complete the form and the property-management team can review your request. No automatic demo booking or response-time guarantee is implied."/>
      {success && <p role="status" className="pm-form-success"><CheckCircle2 size={20}/>{success}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      <form onSubmit={submit}><div className="pm-fields"><label>Full name <span aria-hidden="true">*</span><input required maxLength="160" autoComplete="name" value={values.full_name} onChange={e=>change('full_name',e.target.value)} placeholder="Your full name"/></label><label>Email address <span aria-hidden="true">*</span><input required type="email" autoComplete="email" maxLength="254" value={values.email} onChange={e=>change('email',e.target.value)} placeholder="you@organization.com"/></label><label>Company or portfolio<input maxLength="120" value={values.company} onChange={e=>change('company',e.target.value)} placeholder="Optional"/></label><label>Your role<select value={values.role} onChange={e=>change('role',e.target.value)}><option value="">Select if applicable</option><option>Owner</option><option>Property manager</option><option>Accountant</option><option>Caretaker</option><option>Tenant</option><option>Other</option></select></label><label>Phone (optional)<input type="tel" maxLength="30" autoComplete="tel" value={values.phone} onChange={e=>change('phone',e.target.value)} placeholder="+256…"/></label><label>What can we help with?<select value={values.subject} onChange={e=>change('subject',e.target.value)}><option value="DEMO">Request a walkthrough</option><option value="PRICING">Pricing and deployment</option><option value="SUPPORT">Support inquiry</option><option value="OTHER">Other question</option></select></label></div><label>Tell us more <span aria-hidden="true">*</span><textarea required minLength="20" maxLength="2400" rows="6" placeholder="Describe your portfolio, question or concern…" value={values.message} onChange={e=>change('message',e.target.value)}/></label><label className="pm-consent"><input required type="checkbox" checked={values.consent} onChange={e=>change('consent',e.target.checked)}/><span>I agree to the processing of this inquiry as described in the <Link to="/privacy">Privacy policy</Link>.</span></label><input aria-hidden="true" tabIndex={-1} autoComplete="off" className="pm-honeypot" name="website" value={values.website} onChange={e=>change('website',e.target.value)}/><button className="pm-cta pm-cta-yellow" disabled={busy}>{busy?'Sending…':'Send inquiry'} <ArrowRight size={18}/></button></form></div>
      <aside className="pm-contact-aside"><div className="pm-contact-aside-head"><span className="pm-kicker">A DIRECT LINE TO THE PRODUCT</span><h2>Start with the information that matters.</h2><p>We won't invent a phone number, office address or live-chat channel. Use the verified form to reach the in-app inquiry queue.</p></div><div className="pm-contact-cards"><article><Mail size={28}/><h3>General inquiries</h3><p>Questions about using or evaluating the platform.</p></article><article><CalendarDays size={28}/><h3>Request a walkthrough</h3><p>Explain your portfolio and the workflows you want covered.</p></article><article><ShieldCheck size={28}/><h3>Security questions</h3><p>Raise privacy or account-access concerns without sharing secrets.</p></article></div><Photo photo={PHOTOS[2]}/><p className="pm-contact-note">Please never include passwords, payment-card numbers or identity documents in this public form.</p></aside></div></section></main>;
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
export function PricingPage() {
  return <main className="pm-main"><PageHero eyebrow="PRICING & DEPLOYMENT" title="Discuss a setup that fits your operation." text="Pricing is determined by the operator and its deployment agreement. We do not advertise invented plans, tiers or free trials." photo={PHOTOS[1]}><Link className="pm-cta pm-cta-yellow" to="/contact">Request a pricing discussion <ArrowRight size={18}/></Link></PageHero><div className="pm-container pm-cta-wrap"><CTABanner title="Start with your buildings, not a generic pricing tier."/></div></main>;
}
