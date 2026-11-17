import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Bell, BookOpen, Building2, CalendarRange, ChartColumnIncreasing, ChevronRight, ClipboardCheck, CreditCard, Gauge, FileCheck2, FileClock, FileText, FolderLock, House, KeyRound, LayoutDashboard, LogOut, Mail, Menu, ReceiptText, Settings2, ShieldCheck, Smartphone, Users, Wallet, Wrench, X } from 'lucide-react';
export const COMPACT_GROUPS = [
    { title: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard, pages: ['dashboard'] },
    { title: 'Portfolio', label: 'Portfolio', icon: Building2, pages: ['properties','buildings','floors','rooms','room-placement','portfolio-editor'] },
    { title: 'Tenancies', label: 'Tenancies', icon: Users, pages: ['tenants','leases','renewals','inspections','deposits','disputes'] },
    { title: 'Finance', label: 'Finance', icon: Wallet, pages: ['invoices','proration','payments','mobile-money','receipts','statements','efris','expenses','expense-approvals','finance-health','journal-control','general-ledger','bank-reconciliation','arrears'] },
    { title: 'Operations', label: 'Operations', icon: Wrench, pages: ['maintenance','maintenance-aging','assets','preventive-maintenance','work-orders','utilities','assignments'] },
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
        {group.pages.map(page => <Link key={page} to={'/'+page}
            aria-current={page===active ? 'page':undefined}
            className={'kats-section-tab'+(page===active?' is-active':'')}>
          <PageIcon page={page}/>{labelFor(page)}
        </Link>)}
      </div>
    </nav>;
}
function PageIcon({page}) {
    const Icon = PAGE_META[page]?.icon ?? ChevronRight;
    return <Icon size={15} aria-hidden="true" strokeWidth={1.9}/>;
}
export const PAGE_META = {
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
    'finance-health': { label: 'Reconciliation', icon: ClipboardCheck },
    arrears: { label: 'Overdue rent', icon: FileClock },
    'journal-control': { label: 'Receipt journal', icon: FileText },
    'general-ledger': { label: 'General ledger', icon: BookOpen },
    'bank-reconciliation': { label: 'Bank reconciliation', icon: ClipboardCheck },
    expenses: { label: 'Expenses', icon: Wallet },
    'expense-approvals': { label: 'Expense review', icon: ClipboardCheck },
    maintenance: { label: 'Maintenance', icon: Wrench },
    assets: { label: 'Equipment register', icon: Building2 },
    'maintenance-aging': { label: 'Maintenance aging', icon: Activity },
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
export function labelFor(key) {
    return PAGE_META[key]?.label ?? key.replaceAll('-', ' ').replace(/^./, c => c.toUpperCase());
}
export function WorkspaceNavigation({ pages, active, user, onLogout }) {
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [expanded, setExpanded] = useState(() =>
        compactGroups(pages, user.role).find(group => group.pages.includes(active))?.title || '');
    const drawerTrigger = useRef(null);
    const drawerPanel = useRef(null);
    const groups = useMemo(() => compactGroups(pages, user.role), [pages, user.role]);
    useEffect(() => {
        setDrawerOpen(false);
        const current = compactGroups(pages, user.role).find(group => group.pages.includes(active));
        if (current) setExpanded(current.title);
    }, [active, pages, user.role]);
    useEffect(() => {
        if (!drawerOpen) return undefined;
        const previous = document.body.style.overflow;
        const trigger = drawerTrigger.current;
        document.body.style.overflow = 'hidden';
        const focusTarget = drawerPanel.current?.querySelector('button:not([disabled]), a[href]');
        focusTarget?.focus();
        function trapFocus(event) {
            if (event.key !== 'Tab') return;
            const elements = drawerPanel.current?.querySelectorAll(
                'a[href], button:not([disabled])');
            if (!elements?.length) return;
            const first = elements[0];
            const last = elements[elements.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault(); last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault(); first.focus();
            }
        }
        function escape(event) {
            if (event.key === 'Escape') setDrawerOpen(false);
        }
        document.addEventListener('keydown', trapFocus);
        document.addEventListener('keydown', escape);
        return () => {
            document.removeEventListener('keydown', trapFocus);
            document.removeEventListener('keydown', escape);
            document.body.style.overflow = previous;
            trigger?.focus();
        };
    }, [drawerOpen]);

    function menuItems(close) {
        return groups.map((group, index) => {
            const Icon = group.icon;
            const selected = group.pages.includes(active);
            const isDashboard = group.pages.length === 1 && group.pages[0] === 'dashboard';
            const isExpanded = expanded === group.title;
            const section = index === 0 ? 'OVERVIEW'
                : ['Insights', 'Administration', 'Records', 'Account'].includes(group.title)
                    ? 'REVIEW & CONTROL'
                    : 'MANAGE';
            return <section className="kats-nav-group" key={group.title} aria-label={group.label}>
                {(index === 0 || section !== (index === 1 ? 'OVERVIEW' :
                  ['Insights', 'Administration', 'Records', 'Account'].includes(groups[index - 1]?.title)
                    ? 'REVIEW & CONTROL' : 'MANAGE')) &&
                  <p className="kats-nav-eyebrow">{section}</p>}
                {isDashboard
                    ? <Link to={'/'+group.pages[0]}
                        className={'nav-item kats-nav-section'+(selected?' active':'')}
                        onClick={close} aria-current={selected?'page':undefined}>
                        <Icon size={17} aria-hidden="true" strokeWidth={1.8}/>
                        <span>{group.label}</span>
                      </Link>
                    : <>
                        <button type="button" className={'kats-nav-group-toggle'+
                            (selected ? ' is-current' : '')}
                            aria-expanded={isExpanded} aria-controls={'nav-'+group.title.toLowerCase()}
                            onClick={() => setExpanded(isExpanded ? '' : group.title)}>
                            <Icon size={18} aria-hidden="true" strokeWidth={1.8}/>
                            <span>{group.label}</span>
                            <ChevronRight className="kats-nav-chevron" size={15} aria-hidden="true"/>
                        </button>
                        {isExpanded && <div id={'nav-'+group.title.toLowerCase()}
                            className="kats-nav-children">
                            {group.pages.map(page => {
                                const ChildIcon = PAGE_META[page]?.icon ?? ChevronRight;
                                return <Link key={page} to={'/'+page}
                                    aria-current={active===page?'page':undefined}
                                    onClick={close}
                                    className={'nav-item kats-nav-child'+
                                        (active===page?' active':'')}>
                                    <ChildIcon size={16} strokeWidth={1.7} aria-hidden="true"/>
                                    <span>{labelFor(page)}</span>
                                </Link>;
                            })}
                        </div>}
                      </>}
            </section>;
        });
    }

    const bottomPages = (user.role === 'TENANT'
        ? ['dashboard', 'invoices', 'payments', 'maintenance']
        : ['dashboard', 'rooms', 'payments', 'maintenance']).filter(page => pages.includes(page));
    return <>
      <aside className="side" aria-label="Workspace navigation">
        <Link to="/dashboard" className="workspace-brand">
          <span className="brand-symbol" aria-hidden="true">
            <img src="/brand-mark.svg" alt="" width="39" height="39"/></span>
          <span><strong>KATS</strong><small>PROPERTY MANAGEMENT</small></span>
        </Link>
        <div className="side-account">
          <span className="side-account-label">YOUR WORKSPACE</span>
          <strong title={user.full_name}>{user.full_name}</strong>
          <span>{user.role.replaceAll('_', ' ').toLowerCase()}</span>
        </div>
        <nav className="workspace-links kats-nav-accordion" aria-label="Workspace sections">
          {menuItems(undefined)}
        </nav>
        <div className="side-utilities">
          <Link to="/security"><ShieldCheck size={17} aria-hidden="true"/> Account security</Link>
          <button className="side-signout" type="button" onClick={onLogout}>
            <LogOut size={17} aria-hidden="true"/> Sign out
          </button>
        </div>
      </aside>
      <nav className="mobile-nav" aria-label="Mobile workspace navigation">
        {bottomPages.map(page => {
          const Icon = PAGE_META[page]?.icon ?? LayoutDashboard;
          return <Link key={page} to={'/' + page}
            className={active === page ? 'active' : ''}
            aria-current={active === page ? 'page' : undefined}>
            <Icon size={20} strokeWidth={1.9}/><span>{labelFor(page)}</span>
          </Link>;
        })}
        <button ref={drawerTrigger} type="button"
          className={!bottomPages.includes(active) ? 'active' : ''}
          aria-label="Browse all workspace pages" aria-expanded={drawerOpen}
          aria-controls="mobile-workspace-drawer"
          onClick={() => setDrawerOpen(true)}>
          <Menu size={20} strokeWidth={1.9}/><span>More</span>
        </button>
      </nav>
      {drawerOpen && <div className="drawer-backdrop"
        onClick={() => setDrawerOpen(false)}>
        <section id="mobile-workspace-drawer" ref={drawerPanel} role="dialog"
          aria-modal="true" aria-label="Workspace navigation"
          className="workspace-drawer" onClick={event => event.stopPropagation()}>
          <div className="drawer-head">
            <div><strong>Browse workspace</strong>
              <span>{user.role.replaceAll('_', ' ')}</span></div>
            <button aria-label="Close navigation" className="icon-button"
              type="button" onClick={() => setDrawerOpen(false)}>
              <X size={21}/>
            </button>
          </div>
          <nav className="drawer-links kats-nav-accordion"
            aria-label="All workspace sections">{menuItems(() => setDrawerOpen(false))}</nav>
          <div className="drawer-footer">
            <button className="side-signout" type="button"
              onClick={() => {setDrawerOpen(false); onLogout();}}>
              <LogOut size={17}/> Sign out
            </button>
          </div>
        </section>
      </div>}
    </>;
}
