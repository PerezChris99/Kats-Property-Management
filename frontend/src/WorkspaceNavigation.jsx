import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Bell, BookOpen, Building2, CalendarRange, ChartColumnIncreasing, ChevronRight, ClipboardCheck, CreditCard, Gauge, FileCheck2, FileClock, FileText, FolderLock, House, KeyRound, LayoutDashboard, LogOut, Mail, Menu, ReceiptText, Search, Settings2, ShieldCheck, Smartphone, Users, Wallet, Wrench, X } from 'lucide-react';
const GROUPS = [
    { title: 'Overview', pages: ['dashboard', 'notifications', 'trends', 'reports'] },
    { title: 'Portfolio', pages: ['properties', 'buildings', 'floors', 'rooms', 'room-placement', 'portfolio-editor'] },
    { title: 'Tenancies', pages: ['tenants', 'leases', 'renewals', 'inspections', 'deposits', 'disputes', 'documents'] },
    { title: 'Finance', pages: ['invoices', 'proration', 'payments', 'mobile-money', 'receipts', 'statements', 'efris', 'expenses', 'expense-approvals'] },
    { title: 'Operations', pages: ['maintenance', 'preventive-maintenance', 'work-orders', 'utilities', 'assignments', 'inquiries'] },
    { title: 'Administration', pages: ['users', 'invitations', 'permissions', 'legal', 'audit', 'settings', 'privacy-requests', 'security'] }
];
// Compact primary destinations; original URLs and backend permissions remain intact.
export const COMPACT_GROUPS = [
    { title: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard, pages: ['dashboard'] },
    { title: 'Portfolio', label: 'Portfolio', icon: Building2, pages: ['properties','buildings','floors','rooms','room-placement','portfolio-editor'] },
    { title: 'Tenancies', label: 'Tenancies', icon: Users, pages: ['tenants','leases','renewals','inspections','deposits','disputes'] },
    { title: 'Finance', label: 'Finance', icon: Wallet, pages: ['invoices','proration','payments','mobile-money','receipts','statements','efris','expenses','expense-approvals'] },
    { title: 'Operations', label: 'Operations', icon: Wrench, pages: ['maintenance','preventive-maintenance','work-orders','utilities','assignments'] },
    { title: 'Insights', label: 'Reports & files', icon: ChartColumnIncreasing, pages: ['reports','trends','documents','notifications','inquiries'] },
    { title: 'Administration', label: 'Administration', icon: ShieldCheck, pages: ['users','invitations','permissions','legal','audit','settings','privacy-requests','security'] }
];
export const TENANT_GROUPS = [
    { title: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard, pages: ['dashboard'] },
    { title: 'Rent', label: 'Rent & payments', icon: Wallet, pages: ['invoices','payments','mobile-money','receipts','statements','deposits'] },
    { title: 'Home', label: 'Property care', icon: Wrench, pages: ['maintenance','disputes','inspections','utilities'] },
    { title: 'Records', label: 'Records & updates', icon: FileText, pages: ['documents','notifications'] },
    { title: 'Account', label: 'My account', icon: ShieldCheck, pages: ['privacy-requests','security'] }
];
export function compactGroups(pages, role) {
    const groups = role === 'TENANT' ? TENANT_GROUPS : COMPACT_GROUPS;
    const allowed = new Set(pages);
    const filtered = groups.map(group => ({...group, pages:group.pages.filter(page=>allowed.has(page))}))
        .filter(group=>group.pages.length);
    const used = new Set(filtered.flatMap(group=>group.pages));
    const extra = pages.filter(page=>!used.has(page));
    if (extra.length) filtered.push({title:'Other',label:'Other',icon:Menu,pages:extra});
    return filtered;
}
export function WorkspaceSectionTabs({ pages, active, role }) {
    const group = compactGroups(pages,role).find(item => item.pages.includes(active));
    if (!group || group.pages.length < 2) return null;
    return <nav className="kats-section-tabs" aria-label={group.label + ' subpages'}>
      <div className="kats-section-tabs-heading"><span>{group.label}</span><small>Choose a section</small></div>
      <div className="kats-section-tabs-list">
        {group.pages.map((page,index) => <Link key={page} to={'/'+page}
            aria-current={page===active ? 'page':undefined}
            className={'kats-section-tab'+(page===active?' is-active':'')}>
          <span className="kats-tab-index">{index+1}</span>{labelFor(page)}
        </Link>)}
      </div>
    </nav>;
}
const PAGE_META = {
    dashboard: { label: 'Dashboard', icon: LayoutDashboard },
    notifications: { label: 'Notifications', icon: Bell },
    trends: { label: 'Financial trends', icon: ChartColumnIncreasing },
    reports: { label: 'Reports', icon: Activity },
    properties: { label: 'Properties', icon: House },
    buildings: { label: 'Buildings', icon: Building2 },
    floors: { label: 'Floors', icon: Building2 },
    rooms: { label: 'Rooms', icon: KeyRound },
    'room-placement': { label: 'Room placement', icon: ClipboardCheck },
    'portfolio-editor': { label: 'Edit portfolio', icon: Settings2 },
    tenants: { label: 'Tenants', icon: Users },
    leases: { label: 'Leases', icon: FileText },
    renewals: { label: 'Renewals', icon: CalendarRange },
    inspections: { label: 'Inspections', icon: ClipboardCheck },
    deposits: { label: 'Deposits', icon: Wallet },
    disputes: { label: 'Rental disputes', icon: ClipboardCheck },
    documents: { label: 'Documents', icon: FolderLock },
    invoices: { label: 'Invoices', icon: FileText },
    proration: { label: 'Rent proration', icon: CalendarRange },
    payments: { label: 'Payments', icon: CreditCard },
    'mobile-money': { label: 'Mobile money', icon: Smartphone },
    receipts: { label: 'Receipts', icon: ReceiptText },
    statements: { label: 'Statements', icon: FileText },
    efris: { label: 'EFRIS', icon: FileCheck2 },
    expenses: { label: 'Expenses', icon: Wallet },
    'expense-approvals': { label: 'Expense review', icon: ClipboardCheck },
    maintenance: { label: 'Maintenance', icon: Wrench },
    'preventive-maintenance': { label: 'Maintenance plans', icon: CalendarRange },
    utilities: { label: 'Utilities', icon: Gauge },
    'work-orders': { label: 'Work orders', icon: ClipboardCheck },
    assignments: { label: 'Assignments', icon: Users },
    inquiries: { label: 'Access requests', icon: Mail },
    users: { label: 'Users', icon: Users },
    invitations: { label: 'Invitations', icon: Mail },
    permissions: { label: 'Permissions', icon: ShieldCheck },
    legal: { label: 'Legal pages', icon: BookOpen },
    audit: { label: 'Audit log', icon: FileClock },
    settings: { label: 'Settings', icon: Settings2 },
    'privacy-requests': { label: 'Privacy requests', icon: FileClock },
    security: { label: 'Security', icon: ShieldCheck }
};
function labelFor(key) {
    return PAGE_META[key]?.label ?? key.replaceAll('-', ' ').replace(/^./, c => c.toUpperCase());
}
export function WorkspaceNavigation({ pages, active, user, onLogout }) {
    const [query, setQuery] = useState('');
    const [drawerOpen, setDrawerOpen] = useState(false);
    const desktopSearch = useRef(null);
    const drawerSearch = useRef(null);
    const drawerTrigger = useRef(null);
    const drawerPanel = useRef(null);
    const groups = useMemo(() => {
        const wanted = query.trim().toLowerCase();
        const available = compactGroups(pages,user.role);
        if (!wanted) return available;
        // Search still exposes the original direct page URLs, even though
        // the normal sidebar only shows grouped destinations.
        return available.map(group=>({
            ...group,
            pages:group.pages.filter(page=>labelFor(page).toLowerCase().includes(wanted)
                || group.label.toLowerCase().includes(wanted))
        })).filter(group=>group.pages.length);
    }, [pages,user.role,query]);
    useEffect(() => {
        setDrawerOpen(false);
        setQuery('');
    }, [active]);
    useEffect(() => {
        if (!drawerOpen)
            return;
        const previous = document.body.style.overflow;
        const trigger = drawerTrigger.current;
        document.body.style.overflow = 'hidden';
        drawerSearch.current?.focus();
        function trapFocus(event) {
            if (event.key !== 'Tab')
                return;
            const elements = drawerPanel.current?.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled])');
            if (!elements?.length)
                return;
            const first = elements[0];
            const last = elements[elements.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            }
            else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
        document.addEventListener('keydown', trapFocus);
        return () => {
            document.removeEventListener('keydown', trapFocus);
            document.body.style.overflow = previous;
            trigger?.focus();
        };
    }, [drawerOpen]);
    useEffect(() => {
        function keyDown(event) {
            if (event.key === 'Escape')
                setDrawerOpen(false);
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                if (window.matchMedia('(max-width: 800px)').matches)
                    setDrawerOpen(true);
                else
                    desktopSearch.current?.focus();
            }
        }
        window.addEventListener('keydown', keyDown);
        return () => window.removeEventListener('keydown', keyDown);
    }, []);
    function menuItems(close) {
        if (!groups.length) return <p className="nav-empty">No matching pages.</p>;
        // Normal mode: one navigational entry per section. Search mode:
        // direct links to the matching individual routes.
        if (!query.trim()) return groups.map(group=>{
            const Icon=group.icon;
            const selected=group.pages.includes(active);
            return <Link key={group.title} to={'/'+group.pages[0]}
                className={'nav-item kats-nav-section'+(selected?' active':'')}
                aria-current={selected?'location':undefined} onClick={close}>
                <Icon size={17} strokeWidth={1.8} aria-hidden="true"/>
                <span>{group.label}</span>
                <ChevronRight size={14} aria-hidden="true"/>
            </Link>;
        });
        return groups.map(group=><section className="nav-group" key={group.title} aria-label={group.label}>
            <h2 className="nav-group-label">{group.label}</h2>
            {group.pages.map(page=><Link className={'nav-item'+(active===page?' active':'')}
                key={page} to={'/'+page} onClick={close}
                aria-current={active===page?'page':undefined}>
                <ChevronRight size={16} aria-hidden="true"/><span>{labelFor(page)}</span>
            </Link>)}
        </section>);
    }
    const bottomPages = (user.role === 'TENANT'
        ? ['dashboard', 'invoices', 'payments', 'maintenance']
        : ['dashboard', 'rooms', 'payments', 'maintenance']).filter(page => pages.includes(page));
    const searched = query.length > 0;
    return <>
    <aside className="side" aria-label="Workspace navigation">
      <Link to="/dashboard" className="workspace-brand">
        <span className="brand-symbol" aria-hidden="true"><img src="/brand-mark.svg" alt="" width="39" height="39"/></span>
        <span><strong>KATS</strong><small>PROPERTY MANAGEMENT</small></span>
      </Link>
      <div className="side-account">
        <span className="side-account-label">WORKSPACE</span>
        <strong title={user.full_name}>{user.full_name}</strong>
        <span>{user.role.replaceAll('_', ' ').toLowerCase()}</span>
      </div>
      <div className="nav-search">
        <Search size={17} aria-hidden="true"/>
        <input ref={desktopSearch} type="search" placeholder="Find a page" aria-label="Search workspace navigation" value={query} onChange={event => setQuery(event.target.value)}/>
        {!searched && <kbd>Ctrl K</kbd>}
      </div>
      <nav className="workspace-links" aria-label="Workspace sections">{menuItems(() => setQuery(''))}</nav>
      <div className="side-utilities">
        <Link to="/security"><ShieldCheck size={17}/> Account security</Link>
        <button className="side-signout" type="button" onClick={onLogout}>
          <LogOut size={17}/> Sign out
        </button>
      </div>
    </aside>
    <nav className="mobile-nav" aria-label="Mobile workspace navigation">
      {bottomPages.map(page => {
            const Icon = PAGE_META[page]?.icon ?? LayoutDashboard;
            return <Link key={page} to={'/' + page} className={active === page ? 'active' : ''} aria-current={active === page ? 'page' : undefined}>
          <Icon size={20} strokeWidth={1.9}/><span>{labelFor(page)}</span>
        </Link>;
        })}
      <button ref={drawerTrigger} type="button" className={!bottomPages.includes(active) ? 'active' : ''} aria-label="Browse all workspace pages" aria-expanded={drawerOpen} aria-controls="mobile-workspace-drawer" onClick={() => setDrawerOpen(true)}>
        <Menu size={20} strokeWidth={1.9}/><span>More</span>
      </button>
    </nav>
    {drawerOpen && <div className="drawer-backdrop" onClick={() => setDrawerOpen(false)}>
      <section id="mobile-workspace-drawer" ref={drawerPanel} role="dialog" aria-modal="true" aria-label="Workspace navigation" className="workspace-drawer" onClick={event => event.stopPropagation()}>
        <div className="drawer-head">
          <div><strong>Browse workspace</strong><span>{user.role.replaceAll('_', ' ')}</span></div>
          <button aria-label="Close navigation" className="icon-button" type="button" onClick={() => setDrawerOpen(false)}><X size={21}/></button>
        </div>
        <div className="nav-search drawer-search">
          <Search size={18} aria-hidden="true"/>
          <input ref={drawerSearch} type="search" placeholder="Search pages" aria-label="Search all workspace pages" value={query} onChange={event => setQuery(event.target.value)}/>
        </div>
        <nav className="drawer-links" aria-label="All workspace sections">
          {menuItems(() => setDrawerOpen(false))}
        </nav>
        <div className="drawer-footer">
          <button className="side-signout" type="button" onClick={() => {
                setDrawerOpen(false);
                onLogout();
            }}><LogOut size={17}/> Sign out</button>
        </div>
      </section>
    </div>}
  </>;
}
