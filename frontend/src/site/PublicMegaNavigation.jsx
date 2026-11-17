import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import {
  ArrowRight, BookOpen, Building2, ChartNoAxesCombined, ChevronDown,
  CheckCircle2, CreditCard, FileCheck2, FileText, House, KeyRound,
  Layers3, Menu, RefreshCw, ShieldCheck, Users, Wallet, Wrench, X
} from 'lucide-react';

/* Public destinations point only at actual routes or IDs on the home page.
 * The fourth column is a contextual illustration, not fabricated analytics. */
export const PUBLIC_MENUS = [
  {id:'platform',label:'Platform',columns:[
    {title:'Properties & people',links:[
      {title:'Property portfolio',detail:'Buildings, rooms and occupancy',href:'/#feature-properties',icon:Building2},
      {title:'Tenancies & leases',detail:'Stay on top of agreements',href:'/#feature-leases',icon:KeyRound}
    ]},
    {title:'Money & records',links:[
      {title:'Rent & verified payments',detail:'Invoices, collections and receipts',href:'/#feature-rent',icon:CreditCard},
      {title:'Financial reporting',detail:'Understand the position of your portfolio',href:'/#feature-reports',icon:ChartNoAxesCombined}
    ]},
    {title:'Day-to-day work',links:[
      {title:'Maintenance',detail:'Requests, work orders and follow-up',href:'/#feature-maintenance',icon:Wrench},
      {title:'Access & approvals',detail:'Keep each person in the right lane',href:'/#feature-access',icon:ShieldCheck}
    ]}
  ]},
  {id:'people',label:"Who it's for",columns:[
    {title:'Property oversight',links:[
      {title:'Owners & landlords',detail:'See collections, gaps and priorities',href:'/#role-owners',icon:House},
      {title:'Property managers',detail:'Keep units and tenancies organized',href:'/#role-managers',icon:Building2}
    ]},
    {title:'Finance teams',links:[
      {title:'Accountants',detail:'Review invoices, payments and expenses',href:'/#role-accountants',icon:Wallet},
      {title:'Approvers',detail:'Maintain clear operational controls',href:'/#feature-access',icon:FileCheck2}
    ]},
    {title:'Living & maintenance',links:[
      {title:'Tenants',detail:'Rent activity and home requests',href:'/#role-tenants',icon:Users},
      {title:'Caretakers',detail:'Track repairs and assignments',href:'/#role-caretakers',icon:Wrench}
    ]}
  ]},
  {id:'discover',label:'Explore',columns:[
    {title:'How KATS helps',links:[
      {title:'Problems we solve',detail:'Disconnected property records',href:'/#outcomes',icon:Layers3},
      {title:'See the workflow',detail:'From property setup to reporting',href:'/#workflow',icon:ChartNoAxesCombined}
    ]},
    {title:'Get access',links:[
      {title:'Request access',detail:'Start a conversation about your portfolio',href:'/request-access',icon:ArrowRight},
      {title:'Sign in',detail:'Continue to your workspace',href:'/login',icon:KeyRound}
    ]},
    {title:'Transparency',links:[
      {title:'Data protection',detail:'How access and data are handled',href:'/data-protection',icon:ShieldCheck},
      {title:'Privacy & terms',detail:'Read the applicable policies',href:'/privacy',icon:FileText},
      {title:'Photo attributions',detail:'Credits for images used on the site',href:'/image-attributions',icon:BookOpen}
    ]}
  ]}
];

export function MarketingNavigation({ user, logout, brand }) {
  const {pathname,hash} = useLocation();
  const [mobileOpen,setMobileOpen] = useState(false);
  const [menu,setMenu] = useState(null);
  const [highlight,setHighlight] = useState(null);
  const frame = useRef(null);
  const menuTriggers = useRef({});
  const selected = PUBLIC_MENUS.find(item=>item.id===menu);
  const firstLink = selected?.columns[0]?.links[0];
  const focus = highlight && selected?.columns.some(col=>col.links.includes(highlight))
    ? highlight : firstLink;
  useEffect(()=>{
    setMenu(null);setMobileOpen(false);setHighlight(null);
  },[pathname,hash]);
  useEffect(()=>{
    function onKey(event){
      if(event.key==='Escape'){
        setMenu(current=>{
          if(current) menuTriggers.current[current]?.focus();
          return null;
        });
        setMobileOpen(false);
      }
    }
    function onPointer(event){
      if(!frame.current?.contains(event.target)){
        setMenu(null);setMobileOpen(false);
      }
    }
    document.addEventListener('keydown',onKey);
    document.addEventListener('pointerdown',onPointer);
    return ()=>{
      document.removeEventListener('keydown',onKey);
      document.removeEventListener('pointerdown',onPointer);
    };
  },[]);
  const dismiss = ()=>{setMenu(null);setMobileOpen(false);};
  const toggle = id=>{
    setMenu(value=>value===id?null:id);
    setHighlight(null);
  };
  return <header className="pm-header pm-floating-header">
    <div ref={frame} className="pm-header-inner pm-floating-shell"
      onMouseLeave={()=>{if(window.matchMedia('(min-width:1101px)').matches)setMenu(null);}}
      onBlurCapture={event=>{
        if(!event.currentTarget.contains(event.relatedTarget))setMenu(null);
      }}>
      {brand}
      <button className="pm-menu-trigger" type="button"
        aria-label={mobileOpen?'Close navigation':'Open navigation'}
        aria-expanded={mobileOpen} aria-controls="pm-main-nav"
        onClick={()=>{setMobileOpen(v=>!v);setMenu(null);}}>
        {mobileOpen?<X size={22}/>:<Menu size={22}/>}
      </button>
      <nav id="pm-main-nav" className={'pm-nav pm-floating-nav'+(mobileOpen?' is-open':'')}
        aria-label="Main navigation">
        <NavLink end to="/" onClick={dismiss}
          className={({isActive})=>isActive?'is-active':''}>Home</NavLink>
        {PUBLIC_MENUS.map(item=><button key={item.id} type="button"
          ref={el=>{menuTriggers.current[item.id]=el;}}
          className={'pm-mega-trigger'+(menu===item.id?' is-active':'')}
          aria-expanded={menu===item.id} aria-haspopup="true"
          aria-controls={menu===item.id?'pm-mega-panel':undefined}
          onClick={()=>toggle(item.id)}
          onMouseEnter={()=>{if(window.matchMedia('(min-width:1101px)').matches){setMenu(item.id);setHighlight(null);}}}>
          {item.label}<ChevronDown size={15} aria-hidden="true"/>
        </button>)}
        <Link to="/#workflow" onClick={dismiss} className="pm-workflow-link">How it works</Link>
        <Link to="/request-access" onClick={dismiss} className="pm-nav-request">Request access</Link>
        <span className="pm-nav-separator" aria-hidden="true"/>
        {user
          ? <><Link to="/dashboard" onClick={dismiss}>Workspace</Link>
              <button type="button" className="pm-nav-signout"
                onClick={()=>{dismiss();logout();}}>Sign out</button></>
          : <Link to="/login" onClick={dismiss} className="pm-nav-login">
              <KeyRound size={16} aria-hidden="true"/> Sign in</Link>}
      {selected && <section id="pm-mega-panel" className="pm-mega-panel"
        aria-label={selected.label+' menu'}>
        <div className="pm-mega-top">
          <span>EXPLORE KATS / {selected.label.toUpperCase()}</span>
          <button type="button" aria-label="Close menu" onClick={dismiss}>
            <X size={17} aria-hidden="true"/></button>
        </div>
        <div className="pm-mega-columns">
          {selected.columns.map(col=><div className="pm-mega-column" key={col.title}>
            <h2>{col.title}</h2>
            {col.links.map(entry=>{
              const Icon=entry.icon;
              return <Link key={entry.href+entry.title} to={entry.href}
                onMouseEnter={()=>setHighlight(entry)}
                onFocus={()=>setHighlight(entry)}
                onClick={dismiss} className={'pm-mega-link'+(focus===entry?' is-highlighted':'')}>
                <span className="pm-mega-link-icon"><Icon size={18} aria-hidden="true"/></span>
                <span><strong>{entry.title}</strong><small>{entry.detail}</small></span>
                <ArrowRight size={15} aria-hidden="true"/>
              </Link>;
            })}
          </div>)}
          <aside className="pm-mega-support" aria-live="off">
            <span className="pm-mega-support-kicker">IN FOCUS</span>
            <div className="pm-mega-support-art" aria-hidden="true">
              <div className="pm-mega-support-orbit"/>
              {focus && <focus.icon size={63} strokeWidth={1.2}/>}
            </div>
            {focus && <>
              <strong>{focus.title}</strong><p>{focus.detail}. See how the
                KATS workspace brings this part of property operations together.</p>
              <Link to={focus.href} onClick={dismiss}>Explore this area
                <ArrowRight size={16} aria-hidden="true"/></Link>
            </>}
          </aside>
        </div>
        <div className="pm-mega-foot">
          <span><CheckCircle2 size={15} aria-hidden="true"/> Built around the real property workflow</span>
          <button type="button" onClick={()=>{
            dismiss();window.dispatchEvent(new Event('kats:check-update'));
          }}><RefreshCw size={14} aria-hidden="true"/> Check for app updates</button>
        </div>
      </section>}
      </nav>
    </div>
  </header>;
}
