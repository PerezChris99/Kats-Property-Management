import { api } from './lib/api';
import { WorkspaceNavigation, WorkspaceSectionTabs } from './WorkspaceNavigation';
import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react';
const LandlordAnalytics = lazy(() => import('./charts/WorkspaceAnalytics').then(m => ({default:m.LandlordAnalytics})));
const TenantAnalytics = lazy(() => import('./charts/WorkspaceAnalytics').then(m => ({default:m.TenantAnalytics})));
const ProrationPage = lazy(() => import('./ProrationPage').then(m => ({ default: m.ProrationPage })));
const UtilitiesPage = lazy(() => import('./UtilitiesPage'));
const PrivacyRequestsPage = lazy(() => import('./PrivacyRequestsPage'));
const DisputesPage = lazy(() => import('./DisputesPage'));
const PreventiveMaintenancePage = lazy(() => import('./PreventiveMaintenancePage'));
const AnnualTrendsPage = lazy(() => import('./AnnualTrendsPage').then(m => ({ default: m.AnnualTrendsPage })));
const PortfolioEditPage = lazy(() => import('./PortfolioEditPage').then(m => ({ default: m.PortfolioEditPage })));
const ExpenseApprovalsPage = lazy(() => import('./ExpenseApprovalsPage').then(m => ({ default: m.ExpenseApprovalsPage })));
const ForgotPasswordPage = lazy(() => import('./AccountScreens').then(m => ({ default: m.ForgotPasswordPage })));
const CompleteAccountLinkPage = lazy(() => import('./AccountScreens').then(m => ({ default: m.CompleteAccountLinkPage })));
const InvitationsPage = lazy(() => import('./AccountScreens').then(m => ({ default: m.InvitationsPage })));
const PermissionMatrixPage = lazy(() => import('./AccountScreens').then(m => ({ default: m.PermissionMatrixPage })));
const RoomPlacementPage = lazy(() => import('./AccountScreens').then(m => ({ default: m.RoomPlacementPage })));
const NotificationsPage = lazy(() => import('./Modules').then(m => ({ default: m.NotificationsPage })));
const InspectionsPage = lazy(() => import('./Modules').then(m => ({ default: m.InspectionsPage })));
const MobileMoneyPage = lazy(() => import('./Modules').then(m => ({ default: m.MobileMoneyPage })));
const FiscalPage = lazy(() => import('./Modules').then(m => ({ default: m.FiscalPage })));
const LegalAdminPage = lazy(() => import('./Modules').then(m => ({ default: m.LegalAdminPage })));
const DocumentsPage = lazy(() => import('./Modules').then(m => ({ default: m.DocumentsPage })));
const SecurityPage = lazy(() => import('./Modules').then(m => ({ default: m.SecurityPage })));
const AuditPage = lazy(() => import('./Modules').then(m => ({ default: m.AuditPage })));
const RenewalsPage = lazy(() => import('./Modules').then(m => ({ default: m.RenewalsPage })));
const DepositsPage = lazy(() => import('./Modules').then(m => ({ default: m.DepositsPage })));
const WorkOrdersPage = lazy(() => import('./Modules').then(m => ({ default: m.WorkOrdersPage })));
const SettingsAdminPage = lazy(() => import('./Modules').then(m => ({ default: m.SettingsAdminPage })));
const ReceiptsPage = lazy(() => import('./Modules').then(m => ({ default: m.ReceiptsPage })));
const TenantStatementsPage = lazy(() => import('./Modules').then(m => ({ default: m.TenantStatementsPage })));
const TenantStatementSelfPage = lazy(() => import('./Modules').then(m => ({ default: m.TenantStatementSelfPage })));
const ContactInboxPage = lazy(() => import('./Modules').then(m => ({ default: m.ContactInboxPage })));
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Building2, CheckCircle2, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { PublicShell, LandingPage, RequestAccessPage, LegalPage, ImageAttributionsPage } from './site/Marketing';
import { PHOTOS } from './site/media';
import { NotFoundPage } from './RouteFailure';
const RESOURCES = {
    properties: { title: 'Properties', path: 'properties', columns: ['name', 'address', 'district'], writable: ['OWNER', 'MANAGER', 'SUPER_ADMIN'],
        fields: [{ name: 'name', label: 'Property name', required: true }, { name: 'address', label: 'Address', required: true }, { name: 'district', label: 'District', required: true }] },
    buildings: { title: 'Buildings', path: 'buildings', columns: ['name', 'property_id', 'description'], writable: ['OWNER', 'MANAGER', 'SUPER_ADMIN'],
        fields: [{ name: 'property_id', label: 'Property', required: true }, { name: 'name', label: 'Building name', required: true }, { name: 'description', label: 'Notes' }] },
    floors: { title: 'Floors', path: 'floors', columns: ['building_id', 'level', 'label'], writable: ['OWNER', 'MANAGER', 'SUPER_ADMIN'],
        fields: [{ name: 'building_id', label: 'Building', required: true }, { name: 'level', label: 'Floor level (0 is ground, negative for basements)', type: 'number', required: true }, { name: 'label', label: 'Floor label', required: true }] },
    rooms: { title: 'Rooms', path: 'rooms', columns: ['number', 'floor_id', 'status', 'rent_ugx', 'deposit_ugx'], writable: ['OWNER', 'MANAGER', 'SUPER_ADMIN'],
        fields: [{ name: 'property_id', label: 'Property', required: true }, { name: 'floor_id', label: 'Floor (optional)' }, { name: 'number', label: 'Room number', required: true }, { name: 'rent_ugx', label: 'Monthly rent (UGX)', type: 'number', required: true }, { name: 'deposit_ugx', label: 'Deposit (UGX)', type: 'number' }] },
    tenants: { title: 'Tenants', path: 'tenants', columns: ['full_name', 'phone', 'email'], writable: ['OWNER', 'MANAGER', 'SUPER_ADMIN'],
        fields: [{ name: 'full_name', label: 'Full name', required: true }, { name: 'phone', label: 'Phone', required: true }, { name: 'email', label: 'Email', type: 'email' }, { name: 'user_id', label: 'Linked tenant account' }] },
    leases: { title: 'Leases', path: 'leases', columns: ['room_id', 'tenant_id', 'start_date', 'end_date', 'rent_ugx', 'status'], writable: ['OWNER', 'MANAGER', 'SUPER_ADMIN'],
        fields: [{ name: 'room_id', label: 'Room ID', required: true }, { name: 'tenant_id', label: 'Tenant ID', required: true }, { name: 'start_date', label: 'Start date', type: 'date', required: true }, { name: 'end_date', label: 'End date', type: 'date', required: true }, { name: 'rent_ugx', label: 'Rent (UGX)', type: 'number', required: true }, { name: 'deposit_ugx', label: 'Deposit (UGX)', type: 'number' }] },
    invoices: { title: 'Rent invoices', path: 'invoices', columns: ['invoice_number', 'due_date', 'total_ugx', 'paid_ugx', 'status'], writable: ['OWNER', 'MANAGER', 'ACCOUNTANT', 'SUPER_ADMIN'],
        fields: [{ name: 'lease_id', label: 'Lease ID', required: true }, { name: 'period_start', label: 'Period starts', type: 'date', required: true }, { name: 'period_end', label: 'Period ends', type: 'date', required: true }, { name: 'due_date', label: 'Payment due', type: 'date', required: true }, { name: 'total_ugx', label: 'Amount (UGX)', type: 'number', required: true }] },
    payments: { title: 'Payments', path: 'payments', columns: ['invoice_id', 'method', 'amount_ugx', 'status'], writable: ['OWNER', 'MANAGER', 'ACCOUNTANT', 'SUPER_ADMIN'],
        fields: [{ name: 'invoice_id', label: 'Invoice ID', required: true }, { name: 'method', label: 'Method', required: true, options: ['CASH', 'BANK_TRANSFER'] }, { name: 'amount_ugx', label: 'Amount (UGX)', type: 'number', required: true }, { name: 'reference', label: 'Bank transaction reference' }, { name: 'idempotency_key', label: 'Unique command reference', required: true }] },
    maintenance: { title: 'Maintenance', path: 'maintenance', columns: ['title', 'room_id', 'priority', 'status'], writable: ['OWNER', 'MANAGER', 'ACCOUNTANT', 'SUPER_ADMIN', 'TENANT'],
        fields: [{ name: 'room_id', label: 'Room ID', required: true }, { name: 'title', label: 'Issue', required: true }, { name: 'description', label: 'Description', required: true }, { name: 'priority', label: 'Priority', options: ['LOW', 'MEDIUM', 'HIGH', 'URGENT'] }] },
    receipts: { title: 'Non-fiscal receipts', path: 'receipts', columns: ['receipt_number', 'amount_ugx', 'valid', 'fiscal_status'], writable: [], fields: [] },
    expenses: { title: 'Expenses', path: 'expenses', columns: ['property_id', 'category', 'amount_ugx', 'incurred_on', 'status'], writable: ['OWNER', 'MANAGER', 'ACCOUNTANT', 'SUPER_ADMIN'],
        fields: [{ name: 'property_id', label: 'Property ID', required: true }, { name: 'category', label: 'Category', required: true }, { name: 'description', label: 'Description', required: true }, { name: 'amount_ugx', label: 'Amount (UGX)', type: 'number', required: true }, { name: 'incurred_on', label: 'Date', type: 'date', required: true }, { name: 'idempotency_key', label: 'Unique command reference', required: true }] }
};
const CARETAKER_RESOURCES = {
    rooms: { ...RESOURCES.rooms, path: 'caretaker/rooms', columns: ['number', 'status'], fields: [], writable: [] },
    payments: { ...RESOURCES.payments, path: 'caretaker/payments',
        fields: [{ name: 'invoice_id', label: 'Invoice', required: true }, { name: 'amount_ugx', label: 'Cash collected (UGX)', type: 'number', required: true }, { name: 'idempotency_key', label: 'Unique cash reference', required: true }],
        writable: ['CARETAKER'] },
    maintenance: { ...RESOURCES.maintenance, path: 'caretaker/maintenance', writable: ['CARETAKER'] }
};
RESOURCES.users = { title: 'User accounts', path: 'admin/users', columns: ['full_name', 'email', 'role', 'is_active'],
    writable: [], fields: [] };
RESOURCES.assignments = { title: 'Caretaker assignments', path: 'caretaker/assignments',
    columns: ['caretaker_user_id', 'room_id', 'assigned_at'], writable: ['OWNER', 'MANAGER', 'SUPER_ADMIN'],
    fields: [{ name: 'caretaker_user_id', label: 'Caretaker user ID', required: true },
        { name: 'room_id', label: 'Room ID', required: true }] };
const roles = ['OWNER', 'MANAGER', 'ACCOUNTANT', 'SUPER_ADMIN'];
const formats = (key, value) => key.endsWith('_ugx') && typeof value === 'number'
    ? 'UGX ' + value.toLocaleString('en-UG')
    : String(value ?? '—');
function DataCell({ column, value }) {
    if (column === 'status' || column === 'is_active') {
        const state = column === 'is_active' ? (value ? 'ACTIVE' : 'DISABLED') : String(value ?? 'UNKNOWN').toUpperCase();
        const ok = new Set(['ACTIVE', 'APPROVED', 'ACCEPTED', 'PAID', 'RECONCILED', 'COMPLETED', 'UPLOADED', 'OCCUPIED', 'VERIFIED']);
        const pending = new Set(['PENDING', 'PENDING_REVIEW', 'PENDING_APPROVAL', 'REVIEW_REQUIRED', 'OPEN', 'ASSIGNED', 'IN_PROGRESS', 'CLEANING', 'INITIATED', 'RETRYING', 'PARTIALLY_PAID']);
        const danger = new Set(['VOID', 'REJECTED', 'REVERSED', 'FAILED', 'TERMINATED', 'DISABLED', 'OVERDUE', 'UNRECONCILED']);
        const tone = ok.has(state) ? 'ok' : pending.has(state) ? 'warn' : danger.has(state) ? 'danger' : 'neutral';
        return <span className="status-pill" data-tone={tone}>{state.replaceAll('_', ' ')}</span>;
    }
    return <>{formats(column, value)}</>;
}
// Public demos use only synthetic records. The shared password is an
// intentionally public TEST credential, never an administrator secret.
const PUBLIC_DEMO_ENABLED = import.meta.env.VITE_KATS_PUBLIC_DEMO === 'true' &&
  typeof import.meta.env.VITE_KATS_DEMO_PASSWORD === 'string' &&
  import.meta.env.VITE_KATS_DEMO_PASSWORD.length >= 12 &&
  !import.meta.env.VITE_KATS_DEMO_PASSWORD.startsWith('REPLACE');
const PUBLIC_DEMO_ACCOUNTS = [
  { email: 'landlord@demo.kats.invalid', name: 'Landlord' },
  ...Array.from({ length: 30 }, (_, i) => ({
    email: 'tenant' + String(i + 1).padStart(2, '0') + '@demo.kats.invalid',
    name: 'Tenant ' + String(i + 1).padStart(2, '0')
  }))
];

function Login({ onSuccess }) {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [mfaCode, setMfaCode] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [demoAccounts, setDemoAccounts] = useState([]);
    const [demoSearch, setDemoSearch] = useState('');
    const [demoExpanded, setDemoExpanded] = useState(() =>
        typeof window === 'undefined' || window.matchMedia('(min-width: 761px)').matches);
    useEffect(() => {
        const media = window.matchMedia('(min-width: 761px)');
        const onResize = event => setDemoExpanded(event.matches);
        media.addEventListener('change', onResize);
        return () => media.removeEventListener('change', onResize);
    }, []);
    useEffect(() => {
        // Never request or render demo shortcuts in the production frontend bundle.
        if (!import.meta.env.DEV) return undefined;
        let live = true;
        api('auth/demo-accounts')
            .then(payload => { if (live && payload.enabled) setDemoAccounts(payload.accounts || []); })
            .catch(() => { /* Demo shortcuts are not exposed outside local preview. */ });
        return () => { live = false; };
    }, []);
    async function signInDemo(key) {
        if (busy) return;
        setBusy(true);
        setError('');
        try {
            const payload = await api('auth/demo-sign-in', {
                method: 'POST', body: JSON.stringify({ account: key })
            });
            onSuccess(payload.user);
            navigate('/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Demo sign-in unavailable');
        } finally {
            setBusy(false);
        }
    }
    async function submit(event) {
        event.preventDefault();
        setBusy(true);
        setError('');
        try {
            const payload = await api('auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password, mfa_code: mfaCode })
            });
            onSuccess(payload.user);
            navigate('/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unable to sign in');
        } finally {
            setBusy(false);
        }
    }
    return <main className="auth-layout"><div className="pm-login-layout">
      <div className="pm-login-aside" style={{ '--pm-auth-photo': 'url("' + PHOTOS[2].url + '")' }}><div><span className="pm-kicker pm-kicker-light">WELCOME BACK</span><h2>Property work,<br/><span>simplified.</span></h2><p>Your properties, tenants, rent records and maintenance in one carefully organized workspace.</p><div className="pm-login-benefits"><div><Building2 size={23}/> See your property portfolio</div><div><CheckCircle2 size={23}/> Keep rental activity accountable</div><div><ShieldCheck size={23}/> Work with role-scoped access</div></div></div></div>
      <section className="auth-card pm-login-card" aria-labelledby="pm-signin-title"><Link to="/" className="pm-brand" aria-label="KATS Property Management home"><img src="/brand-mark.svg" width="56" height="56" alt=""/><span><strong>KATS</strong><small>Property Management</small></span></Link><h1 id="pm-signin-title">Sign in to your account</h1><p className="pm-login-caption">Use the credentials issued by your property administrator. An authenticator code is required only if MFA is enabled for your account.</p>
      <form onSubmit={submit}><label>Email address<input type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} maxLength={254} required placeholder="you@company.com"/></label>
      <label>Password<div className="pm-password-field"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="Enter your password"/><button type="button" className="pm-reveal-password" onClick={() => setShowPassword(v => !v)} aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}>{showPassword ? <EyeOff size={19}/> : <Eye size={19}/>}</button></div></label>
      <label>Authenticator code (if enabled)<input type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={mfaCode} onChange={e => setMfaCode(e.target.value.replace(/\D/g,'').slice(0,6))} placeholder="Six-digit code"/></label>
      {error && <p role="alert" className="error">{error}</p>}
      <button className="pm-cta pm-cta-yellow" disabled={busy}>{busy ? 'Signing in…' : 'Sign in securely'} <ArrowRight size={18}/></button></form>
      <div className="pm-login-links"><Link to="/forgot-password">Forgot your password?</Link><Link to="/request-access">Request access</Link></div><div className="pm-login-security"><ShieldCheck size={23}/><span>Session protection and role-based authorization help keep private property records in the right hands. No third-party social login is claimed.</span></div></section>
      {!PUBLIC_DEMO_ENABLED && demoAccounts.length === 31 && <aside className="pm-local-demo-pane" aria-label="Local demo accounts">
        <details className="pm-demo-disclosure" open={demoExpanded}
          onToggle={event => setDemoExpanded(event.currentTarget.open)}>
          <summary>Explore 31 demo accounts</summary>
        <section className="pm-demo-signins" aria-label="Demo accounts for local preview">
        <div className="pm-demo-header"><div><span className="pm-demo-kicker">LOCAL DEMO</span><h2>Explore the live workspace</h2><p>Fictional rental records. Click an account to sign in instantly.</p></div><span className="pm-demo-count">31 accounts</span></div>
        <button type="button" className="pm-demo-owner" disabled={busy}
          onClick={() => signInDemo('landlord')}>
          <span className="pm-demo-avatar" aria-hidden="true">L</span>
          <span><strong>Landlord workspace</strong><small>{demoAccounts[0]?.name}</small></span>
          <ArrowRight size={18} aria-hidden="true"/>
        </button>
        <div className="pm-demo-tenant-head"><label htmlFor="pm-demo-search">Tenant workspaces</label><span>30 linked leases</span></div>
        <input id="pm-demo-search" className="pm-demo-search" type="search" value={demoSearch}
          onChange={event => setDemoSearch(event.target.value)} placeholder="Find a demo tenant…" autoComplete="off"/>
        <div className="pm-demo-tenant-list" role="group" aria-label="Sign in as a demo tenant">
          {demoAccounts.filter(account => account.role === 'TENANT' &&
            account.name.toLowerCase().includes(demoSearch.trim().toLowerCase())).map(account =>
            <button type="button" key={account.key} disabled={busy}
              onClick={() => signInDemo(account.key)}>
              <span>{account.name}</span><ArrowRight size={15} aria-hidden="true"/>
            </button>)}
        </div>
      </section>
        </details>
      </aside>}
      {PUBLIC_DEMO_ENABLED && <aside className="pm-public-demo-pane" aria-label="Demo Accounts — for testing only">
        <details className="pm-public-demo-disclosure" open={demoExpanded}
          onToggle={event => setDemoExpanded(event.currentTarget.open)}>
          <summary>Demo accounts for testing · 31 users</summary>
        <span className="pm-public-demo-label">PUBLIC DEMONSTRATION · SYNTHETIC RECORDS</span>
        <h2>Demo Accounts</h2>
        <p className="pm-demo-context">For testing only. Select an account to fill the form, then sign in. All records are fictional.</p>
        <div className="pm-demo-shared-password"><span>Shared demonstration password</span><code>{import.meta.env.VITE_KATS_DEMO_PASSWORD}</code></div>
        <div className="pm-public-demo-scroll">
          {PUBLIC_DEMO_ACCOUNTS.map(account => <button key={account.email} type="button" className="pm-public-demo-choice"
            onClick={() => { setEmail(account.email); setPassword(import.meta.env.VITE_KATS_DEMO_PASSWORD); setMfaCode(''); setError(''); }}>
            <span><strong>{account.name}</strong><small>{account.email}</small></span><span className="pm-demo-action">Use account <ArrowRight size={13} aria-hidden="true"/></span>
          </button>)}
        </div>
        <p className="pm-demo-disclaimer">Credentials are intentionally public. Never use these accounts for real tenancies, customers or payments.</p>
        </details>
      </aside>}</div></main>;
}
function ResourcePage({ resource, user }) {
    const [rows, setRows] = useState([]);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [total, setTotal] = useState(null);
    const [filter, setFilter] = useState('');
    const [serverFilter, setServerFilter] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [editing, setEditing] = useState(false);
    const [values, setValues] = useState({});
    const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
    const [busy, setBusy] = useState(false);
    const [references, setReferences] = useState({});
    const latestLoad = useRef(0);
    const canWrite = resource.writable?.includes(user.role) ?? false;
    const searchable = new Set(['properties', 'buildings', 'floors', 'rooms', 'tenants',
        'invoices', 'payments', 'maintenance', 'expenses']).has(resource.path);
    const search = filter.trim().toLowerCase();
    const visibleRows = searchable ? rows : search
        ? rows.filter(row => Object.values(row).some(value => String(value ?? '').toLowerCase().includes(search))) : rows;
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(1);
            setServerFilter(filter.trim().length >= 2 ? filter.trim() : '');
        }, 300);
        return () => clearTimeout(timer);
    }, [filter]);
    const load = useCallback(async (signal) => {
        const requestNumber = ++latestLoad.current;
        setLoading(true);
        setError('');
        try {
            const join = resource.path.includes('?') ? '&' : '?';
            const q = searchable && serverFilter ? '&q=' + encodeURIComponent(serverFilter) : '';
            const payload = await api(resource.path + join + 'page=' + page + '&page_size=' + pageSize + '&include_total=0' + q,
                signal ? { signal } : {});
            if (requestNumber !== latestLoad.current || signal?.aborted) return;
            setRows(payload.items || []);
            setTotal(typeof payload.total === 'number' ? payload.total : null);
        } catch (err) {
            if (requestNumber !== latestLoad.current || signal?.aborted ||
                (err instanceof DOMException && err.name === 'AbortError')) return;
            setError(err instanceof Error ? err.message : 'Could not load');
        } finally {
            if (requestNumber === latestLoad.current && !signal?.aborted) setLoading(false);
        }
    }, [resource.path, page, pageSize, searchable, serverFilter]);
    useEffect(() => {
        const controller = new AbortController();
        void load(controller.signal);
        return () => { controller.abort(); };
    }, [load]);
    useEffect(() => { setPage(1); setFilter(''); setServerFilter(''); }, [resource.path]);
    useEffect(() => {
        if (!editing)
            return;
        const entities = { property_id: 'properties', building_id: 'buildings', floor_id: 'floors', room_id: 'rooms', tenant_id: 'tenants', lease_id: 'leases', invoice_id: 'invoices', caretaker_user_id: 'caretaker/roster', user_id: 'tenants/accounts' };
        const related = resource.fields.filter(field => entities[field.name]);
        Promise.all(related.map(async (field) => {
            try {
                const endpoint = user.role === 'CARETAKER' && field.name === 'room_id' ? 'caretaker/rooms' : user.role === 'TENANT' && field.name === 'room_id' ? 'tenant/rooms' : user.role === 'CARETAKER' && field.name === 'invoice_id' ? 'caretaker/invoices' : entities[field.name];
                const payload = await api(endpoint);
                const items = field.name === 'caretaker_user_id' ? (payload.items || []).filter((item) => item.role === 'CARETAKER') : (payload.items || []);
                return [field.name, items];
            }
            catch {
                return [field.name, []];
            }
        })).then(result => setReferences(Object.fromEntries(result)));
    }, [editing, resource.fields, user.role]);
    async function submit(event) {
        event.preventDefault();
        setBusy(true);
        setError('');
        const body = {};
        for (const field of resource.fields) {
            const value = field.name === 'idempotency_key' ? idempotencyKey : (values[field.name] || '').trim();
            if (field.type === 'number' && value && !/^-?\d+$/.test(value)) {
                setError(field.label + ' must be a whole number.');
                setBusy(false);
                return;
            }
            if (value || field.required)
                body[field.name] = field.type === 'number' ? Number(value) : value;
        }
        // An interrupted mobile response must not create a second work order
        // when the operator presses Save again: reuse the same key until success.
        if (resource.path === 'maintenance') body.idempotency_key = idempotencyKey;
        try {
            await api(resource.path === 'payments' ? 'payments/manual' : resource.path, { method: 'POST', body: JSON.stringify(body) });
            setEditing(false);
            setValues({});
            setIdempotencyKey(crypto.randomUUID());
            await load();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Could not save');
        }
        finally {
            setBusy(false);
        }
    }
    async function financeAction(endpoint) {
        const reason = window.prompt('Reason for this accounting correction (required)');
        if (!reason?.trim())
            return;
        setBusy(true);
        setError('');
        try {
            await api(endpoint, { method: 'POST', body: JSON.stringify({ reason }) });
            await load();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Correction failed');
        }
        finally {
            setBusy(false);
        }
    }
    async function unassign(id) {
        if (!window.confirm('Remove this caretaker assignment?'))
            return;
        setBusy(true);
        setError('');
        try {
            await api('caretaker/assignments/' + id, { method: 'DELETE' });
            await load();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Could not remove assignment');
        }
        finally {
            setBusy(false);
        }
    }
    async function caretakerRoomStatus(id, status) {
        const reason = window.prompt('Reason for this room status change');
        if (!reason?.trim())
            return;
        setBusy(true);
        setError('');
        try {
            await api('caretaker/rooms/' + id + '/status', { method: 'POST', body: JSON.stringify({ status, reason }) });
            await load();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Could not change status');
        }
        finally {
            setBusy(false);
        }
    }
    async function toggleAccess(id, current) {
        if (!window.confirm(current ? 'Disable this account?' : 'Re-enable this account?'))
            return;
        setBusy(true);
        setError('');
        try {
            await api('admin/users/' + id + '/status', { method: 'POST', body: JSON.stringify({ is_active: !current }) });
            await load();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Could not change access');
        }
        finally {
            setBusy(false);
        }
    }
    async function approve(id) {
        setBusy(true);
        setError('');
        try {
            await api('payments/' + id + '/approve', { method: 'POST' });
            await load();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Could not approve');
        }
        finally {
            setBusy(false);
        }
    }
    return <section className="page"><div className="page-head"><div><span className="eyebrow">OPERATIONS</span><h1>{resource.title}</h1></div>{canWrite && <button className="button" onClick={() => setEditing(!editing)}>{editing ? 'Cancel' : 'Add ' + resource.title.toLowerCase()}</button>}</div>
    {error && <div role="alert" className="error">{error} <button type="button" className="outline-button" onClick={() => { void load(); }}>Retry</button></div>}
    {editing && canWrite && <form className="resource-form" onSubmit={submit}><h2>New record</h2><div className="fields">{resource.fields.filter(field => field.name !== 'idempotency_key').map(field => <label key={field.name}>{field.label}{field.options ? <select value={values[field.name] || ''} onChange={e => setValues({ ...values, [field.name]: e.target.value })} required={field.required}><option value="">Select</option>{field.options.map(option => <option key={option}>{option}</option>)}</select> : references[field.name]?.length ? <select value={values[field.name] || ''} onChange={e => setValues({ ...values, [field.name]: e.target.value })} required={field.required}><option value="">Select a record</option>{references[field.name].map(row => <option key={String(row.id)} value={String(row.id)}>{String(row.name || row.number || row.full_name || row.invoice_number || row.email || row.title || row.id)}</option>)}</select> : <input required={field.required} type={field.type || 'text'} min={field.type === 'number' ? (field.name === 'level' ? '-10' : '0') : undefined} value={values[field.name] || ''} onChange={e => setValues({ ...values, [field.name]: e.target.value })}/>}</label>)}</div><button className="button" disabled={busy}>{busy ? 'Saving…' : 'Save record'}</button></form>}
    <div className="record-toolbar">
      <label className="record-filter">{searchable ? 'Search all authorized records' : 'Filter loaded records'}
        <input type="search" placeholder={searchable ? 'Search all records (2+ characters)' : 'Filter this page'} value={filter} onChange={event => setFilter(event.target.value)}/></label>
      <span aria-live="polite">{searchable && serverFilter ? 'Database search' : 'Loaded records'}: {visibleRows.length} shown</span>
    </div>
    {loading ? <p role="status" className="data-loading">Loading records…</p> : rows.length === 0 ? <div className="empty"><h2>{serverFilter || search ? 'No matching records' : 'No records yet'}</h2><p>{serverFilter || search ? 'Try another search or clear the filter.' : 'Authorized records will appear here after they are created.'}</p>{(serverFilter || search) && <button type="button" className="outline-button" onClick={() => setFilter('')}>Clear search</button>}</div> : visibleRows.length === 0 ? <div className="empty"><h2>No matching records</h2><p>Clear the filter to see the loaded records.</p><button type="button" className="outline-button" onClick={() => setFilter('')}>Clear filter</button></div> : <div className="data-table-wrap"><table><thead><tr>{resource.columns.map(col => <th key={col}>{col.replaceAll('_', ' ')}</th>)}{resource.path === 'payments' && <th>Cash receipt</th>}{resource.path === 'payments' && canWrite && <th>Review</th>}{(resource.path === 'payments' && ['OWNER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role) || resource.path === 'invoices' && ['OWNER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role) || resource.path === 'caretaker/rooms' || resource.path === 'caretaker/assignments' || resource.path === 'admin/users') && <th>Actions</th>}</tr></thead><tbody>{visibleRows.map((item, i) => <tr key={String(item.id || i)}>{resource.columns.map(col => <td key={col}><DataCell column={col} value={item[col]}/></td>)}{resource.path === 'payments' && <td>{item.method === 'CASH' && ['PENDING_REVIEW','RECONCILED','REVERSED'].includes(item.status) ?
        <a className="outline-button" href={'/api/v1/payments/' + encodeURIComponent(String(item.id)) + '/cash-acknowledgement.pdf'}>Written cash receipt</a> : '—'}</td>}{resource.path === 'payments' && canWrite && <td>{item.status === 'PENDING_REVIEW' ? <button className="outline-button" disabled={busy} onClick={() => approve(String(item.id))}>Approve*</button> : <span>—</span>}</td>}
    {resource.path === 'payments' && ['OWNER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role) && <td>{item.status === 'RECONCILED' ? <button className="outline-button" disabled={busy} onClick={() => financeAction('payments/' + String(item.id) + '/reverse')}>Reverse</button> : '—'}</td>}
    {resource.path === 'invoices' && ['OWNER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role) && <td>{item.status === 'ISSUED' && Number(item.paid_ugx) === 0 ? <button className="outline-button" disabled={busy} onClick={() => financeAction('invoices/' + String(item.id) + '/void')}>Void</button> : '—'}</td>}
    {resource.path === 'caretaker/rooms' && <td><button className="outline-button" disabled={busy} onClick={() => caretakerRoomStatus(String(item.id), 'MAINTENANCE')}>Needs repair</button> <button className="outline-button" disabled={busy} onClick={() => caretakerRoomStatus(String(item.id), 'CLEANING')}>Cleaning</button></td>}
    {resource.path === 'caretaker/assignments' && <td><button className="outline-button" disabled={busy} onClick={() => unassign(String(item.id))}>Unassign</button></td>}
    {resource.path === 'admin/users' && <td><button className="outline-button" disabled={busy} onClick={() => toggleAccess(String(item.id), Boolean(item.is_active))}>{item.is_active ? 'Disable' : 'Enable'}</button></td>}</tr>)}</tbody></table></div>}
    {!loading && rows.length > 0 && <div className="pagination-controls" aria-label="Record pages">
      <div className="page-size"><label>Rows per page
        <select value={pageSize} onChange={event => { setPageSize(Number(event.target.value)); setPage(1); }}>
          <option value={10}>10</option><option value={25}>25</option><option value={50}>50</option>
        </select></label></div>
      <span aria-live="polite">Page {page}{total !== null ? ' of ' + Math.max(1, Math.ceil(total / pageSize)) : ''}</span>
      <div className="actions">
        <button className="outline-button" type="button" disabled={page <= 1 || loading} onClick={() => setPage(p => Math.max(1, p - 1))}>Previous</button>
        <button className="outline-button" type="button" disabled={loading || page >= 200 || (total !== null ? page * pageSize >= total : rows.length < pageSize)} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>
    </div>}
    {resource.path === 'payments' && <p className="note">*Cash collections have a written custody receipt immediately, even before independent verification. The official URA EFRIS fiscal document is separate. Approval requires another staff member to verify source evidence. Approval credits the invoice; authorized owners or accountants can post an auditable accounting reversal. Reversal never automatically refunds cash.</p>}
    <p className="note">Access is enforced by the server. Search filters this page only; use Previous / Next to browse more records.</p></section>;
}
function Dashboard({ user }) {
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState('');
    useEffect(() => { api('dashboard').then(setSummary).catch(err => setError(String(err))); }, []);
    const money = value => 'UGX ' + Number(value || 0).toLocaleString('en-UG');
    const occupied = Number(summary?.occupied_rooms || 0);
    const vacant = Number(summary?.vacant_rooms || 0);
    const occupancy = (occupied + vacant) > 0 ? Math.round(100 * occupied / (occupied + vacant)) : null;
    const collected = Number(summary?.collected_ugx || 0);
    const expected = Number(summary?.expected_ugx || 0);
    const collection = expected > 0 ? Math.min(100, Math.max(0, Math.round(100 * collected / expected))) : null;
    return <section className="page kats-overview">
      <div className="kats-overview-head">
        <div><span className="eyebrow">YOUR PORTFOLIO, AT A GLANCE</span>
          <h1>Welcome back, {user.full_name.split(' ')[0]}.</h1>
          <p>Recorded balances and operational activity. Unverified payments are not counted as collected.</p>
        </div>
        <Link className="button" to="/reports">View reports <ArrowRight size={16}/></Link>
      </div>
      {error && <p role="alert" className="error">{error}</p>}
      {!summary && !error ? <p role="status" className="data-loading">Loading your portfolio overview…</p> : !summary ? <div className="empty" role="alert"><p>Portfolio overview is unavailable.</p><button className="button small" onClick={() => { setError(''); api('dashboard').then(setSummary).catch(e=>setError(String(e))); }}>Retry</button></div> : <>
        <div className="kats-overview-spotlight">
          <div className="kats-overview-primary">
            <span className="kats-overview-label">RENT PERFORMANCE</span>
            <span className="kats-overview-desc">Collected rent</span>
            <strong>{money(summary.collected_ugx)}</strong>
            <div className="kats-meter" role="img" aria-label={collection === null ? 'No expected rent recorded' : collection + '% of expected rent collected'}>
              <span style={{width: (collection ?? 0) + '%'}}/>
            </div>
            <div className="kats-meter-notes"><span>{collection === null ? 'No expected rent recorded' : collection + '% of expected'}</span><span>Expected: {money(summary.expected_ugx)}</span></div>
          </div>
          <div className="kats-overview-secondary">
            <span className="kats-overview-label">ATTENTION REQUIRED</span>
            <div><small>Outstanding</small><strong>{money(summary.outstanding_ugx)}</strong></div>
            <div><small>Open maintenance</small><strong>{Number(summary.open_maintenance || 0).toLocaleString('en-UG')}</strong></div>
            <Link to="/maintenance">Review maintenance <ArrowRight size={16}/></Link>
          </div>
        </div>
        <div className="kats-overview-section-head"><h2>Portfolio health</h2><span>Recorded units</span></div>
        <div className="stat-grid">
          <div className="stat"><small>Occupied rooms</small><strong>{occupied.toLocaleString('en-UG')}</strong></div>
          <div className="stat"><small>Vacant / other rooms</small><strong>{vacant.toLocaleString('en-UG')}</strong></div>
          <div className="stat"><small>Recorded occupancy</small><strong>{occupancy === null ? '—' : occupancy + '%'}</strong></div>
        </div>
      </>}
      <Suspense fallback={<p className="data-loading" role="status">Loading portfolio charts…</p>}><LandlordAnalytics /></Suspense>
      <div className="quick kats-overview-actions"><h2>Go to workspace</h2><div><Link to="/properties">Properties <ArrowRight size={15}/></Link><Link to="/rooms">Rooms <ArrowRight size={15}/></Link><Link to="/invoices">Invoices <ArrowRight size={15}/></Link><Link to="/payments">Payments <ArrowRight size={15}/></Link></div></div>
    </section>;
}
function ReportsPage() {
    const [month, setMonth] = useState('');
    const [summary, setSummary] = useState(null);
    const [arrears, setArrears] = useState(null);
    const [error, setError] = useState('');
    useEffect(() => {
        setError('');
        Promise.all([api('reports/summary' + (month ? '?month=' + month : '')), api('reports/arrears')])
            .then(([a, b]) => { setSummary(a); setArrears(b); })
            .catch(err => setError(err instanceof Error ? err.message : 'Could not load reports'));
    }, [month]);
    return <section className="page"><span className="eyebrow">FINANCIAL OVERSIGHT</span><h1>Reports</h1>
    <p>Invoice-period reporting. Payments applied to an invoice are not necessarily cash received in the selected month.</p>
    <label style={{ maxWidth: 280 }}>Invoice period <input type="month" value={month} onChange={e => setMonth(e.target.value)}/></label>
    {error && <p className="error" role="alert">{error}</p>}
    {summary ? <><div className="stat-grid">
      {[['Invoiced UGX', summary.billed_ugx], ['Applied to invoices UGX', summary.applied_to_invoices_ugx],
                ['Outstanding UGX', summary.outstanding_on_invoices_ugx], ['Period expenses UGX', summary.expenses_in_period_ugx],
                ['Occupied units', summary.occupied_units], ['Occupancy %', summary.occupancy_percent]].map(([label, value]) => <div key={label} className="stat"><small>{label}</small><strong>{typeof value === 'number' ? value.toLocaleString('en-UG') : value}</strong></div>)}
    </div><p className="note">{String(summary.methodology)}</p></> : <p role="status">Loading financial report…</p>}
    {arrears && <div className="quick"><h2>Overdue rent</h2><p>{arrears.overdue_invoices} overdue invoice(s) · UGX {arrears.total_ugx.toLocaleString('en-UG')}</p>
      <div className="stat-grid">{Object.entries(arrears.ageing_ugx).map(([label, value]) => <div className="stat" key={label}><small>{label.replaceAll('_', ' ')}</small><strong>UGX {value.toLocaleString('en-UG')}</strong></div>)}</div></div>}
    <div className="quick"><h2>Exports</h2><a className="button" href="/api/v1/reports/export/invoices.csv">Download invoice CSV</a> <a className="button" href="/api/v1/reports/export/invoices.xlsx">Download invoice Excel</a> <Link to="/statements" className="button">Tenant statements</Link></div>
  </section>;
}
function TenantHome() {
    const [summary, setSummary] = useState(null);
    const [lease, setLease] = useState(null);
    const [error, setError] = useState('');
    const [leaseError, setLeaseError] = useState('');
    const [leaseLoading, setLeaseLoading] = useState(true);
    const [reload, setReload] = useState(0);
    useEffect(() => {
        let active = true;
        setError('');
        setLeaseError('');
        setLeaseLoading(true);
        // Fetch these independently: an unavailable lease service must not
        // suppress successful payment/balance information (or vice versa).
        api('tenant/dashboard').then(result => {
            if (active) setSummary(result);
        }).catch(err => { if (active) setError(err.message || 'Could not load rent summary'); });
        api('tenant/lease').then(result => {
            if (active) setLease(result.lease || null);
        }).catch(err => { if (active) setLeaseError(err.message || 'Could not load lease'); })
            .finally(() => { if (active) setLeaseLoading(false); });
        return () => { active = false; };
    }, [reload]);
    return <section className="page"><span className="eyebrow">TENANT PORTAL</span><h1>My rental account</h1><p>Your current lease and recorded rent activity.</p>
    {error && <p role="alert" className="error">{error}</p>}
    {summary ? <div className="stat-grid"><div className="stat"><small>Invoiced</small><strong>UGX {summary.total_ugx.toLocaleString('en-UG')}</strong></div><div className="stat"><small>Paid</small><strong>UGX {summary.paid_ugx.toLocaleString('en-UG')}</strong></div><div className="stat"><small>Outstanding</small><strong>UGX {summary.outstanding_ugx.toLocaleString('en-UG')}</strong></div></div> : !error ? <p role="status">Loading rent summary…</p> : <p role="alert">Unable to load rental summary. Check the API and reload.</p>}
    <Suspense fallback={<p className="data-loading" role="status">Loading rental charts…</p>}><TenantAnalytics /></Suspense>
    <div className="quick"><h2>My lease</h2>{leaseError && <p role="alert">{leaseError} <button type="button" className="outline-button small" onClick={() => setReload(n=>n+1)}>Retry</button></p>}{leaseLoading ? <p role="status">Loading lease…</p> : lease ? <p><strong>{lease.property_name || 'Your property'}</strong> · Unit {lease.room_number || lease.room_id} · Monthly rent: UGX {Number(lease.rent_ugx).toLocaleString('en-UG')} · Lease ends: {lease.end_date}.</p> : !leaseError ? <p>No active lease is currently linked to your account.</p> : null}<Link to="/invoices">Invoices</Link><Link to="/payments">Payments</Link><Link to="/maintenance">Maintenance</Link></div>
  </section>;
}
function CaretakerHome() {
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState('');
    useEffect(() => { api('caretaker/dashboard').then(setSummary).catch(err => setError(String(err))); }, []);
    return <section className="page"><span className="eyebrow">CARETAKER PORTAL</span><h1>My assigned rooms</h1><p>Only assigned rooms and their tasks are visible.</p>
    {error && <p role="alert" className="error">{error}</p>}
    {summary ? <div className="stat-grid">
      <div className="stat"><small>Assigned rooms</small><strong>{summary.assigned_rooms}</strong></div>
      <div className="stat"><small>Open maintenance</small><strong>{summary.open_maintenance}</strong></div>
      <div className="stat"><small>Cash awaiting approval</small><strong>{summary.pending_cash}</strong></div>
    </div> : <p>Loading assigned work…</p>}
    <div className="quick"><Link to="/rooms">Rooms</Link><Link to="/maintenance">Maintenance</Link><Link to="/payments">Cash records</Link></div>
  </section>;
}
function Portal({ user, logout, systemReady }) {
    const location = useLocation();
    const page = location.pathname.slice(1);
    const canOperate = roles.includes(user.role);
    const nav = canOperate ? ['dashboard', 'properties', 'buildings', 'floors', 'rooms', 'room-placement', 'portfolio-editor', 'tenants', 'leases', 'proration', 'invoices', 'payments', 'utilities', 'maintenance', 'preventive-maintenance', 'disputes', 'expenses', 'expense-approvals', 'reports', 'trends', 'statements', 'receipts', 'mobile-money', 'efris', 'inspections', 'renewals', 'deposits', 'work-orders', 'documents', 'notifications', 'privacy-requests', 'security', ...(user.role === 'OWNER' || user.role === 'SUPER_ADMIN' ? ['settings'] : []), ...(user.role === 'OWNER' || user.role === 'SUPER_ADMIN' ? ['users', 'invitations', 'permissions', 'legal', 'audit', 'inquiries'] : []), ...(user.role === 'OWNER' || user.role === 'SUPER_ADMIN' || user.role === 'MANAGER' ? ['assignments'] : [])] : user.role === 'CARETAKER' ? ['dashboard', 'rooms', 'payments', 'utilities', 'maintenance', 'preventive-maintenance', 'work-orders', 'inspections', 'documents', 'notifications', 'privacy-requests', 'security', 'receipts'] : ['dashboard', 'invoices', 'payments', 'utilities', 'statements', 'receipts', 'deposits', 'maintenance', 'disputes', 'inspections', 'documents', 'mobile-money', 'notifications', 'privacy-requests', 'security'];
    const viewResource = user.role === 'CARETAKER' ? CARETAKER_RESOURCES[page] : RESOURCES[page];
    const pageTitle = page.replaceAll('-', ' ').replace(/^./, c => c.toUpperCase());
    const [readFailed, setReadFailed] = useState(false);
    useEffect(() => {
        setReadFailed(false);
        const onFailure = () => setReadFailed(true);
        window.addEventListener('kats:workspace-read-error', onFailure);
        return () => window.removeEventListener('kats:workspace-read-error', onFailure);
    }, [page]);
    return <div className="portal">
    <WorkspaceNavigation pages={nav} active={page} user={user} onLogout={logout}/>
    <div className="portal-main">
      <header className="portal-bar">
        <div className="portal-location">
          <span>Workspace <span aria-hidden="true">/</span> {pageTitle}</span>
          <strong>{pageTitle}</strong>
        </div>
        <div className="portal-header-tools"><span className={'portal-system-state ' + (systemReady === true ? 'is-connected' : systemReady === false ? 'is-disconnected' : '')} role="status"><span className="portal-status-dot" aria-hidden="true"/>{systemReady === null ? 'Checking API' : systemReady ? 'System connected' : 'API unavailable'}</span><div className="portal-identity" title={user.full_name}>
          <span className="identity-avatar" aria-hidden="true">{user.full_name.trim().charAt(0).toUpperCase()}</span>
          <span><strong>{user.full_name}</strong><small>{user.role.replaceAll('_', ' ')}</small></span>
        </div></div>
      </header>
      <main className="portal-content" data-view={page} key={page}>
        {readFailed && <div className="kats-workspace-read-alert" role="alert">
          Some workspace records could not be loaded. Check your connection or
          <button className="outline-button small" onClick={() => window.location.reload()}>Reload this page</button>.
        </div>}
        {page !== "dashboard" && page !== "more" && <WorkspaceSectionTabs pages={nav} active={page} role={user.role}/>}
        <Suspense fallback={<p className="data-loading" role="status">Opening workspace…</p>}>{page === 'more' ? <section className="page"><span className="eyebrow">YOUR WORKSPACE</span><h1>More</h1><div className="quick">{nav.map(key => <Link key={key} to={'/' + key}>{key[0].toUpperCase() + key.slice(1)}</Link>)}</div><button className="button" onClick={logout}>Sign out</button></section> : page === 'statements' && nav.includes(page) ? (user.role === 'TENANT' ? <TenantStatementSelfPage /> : <TenantStatementsPage />) :
            page === 'receipts' && nav.includes(page) ? <ReceiptsPage /> :
                page === 'utilities' && nav.includes(page) ? <UtilitiesPage role={user.role}/> :
                page === 'privacy-requests' && nav.includes(page) ? <PrivacyRequestsPage role={user.role}/> :
                page === 'disputes' && nav.includes(page) ? <DisputesPage role={user.role}/> :
                page === 'preventive-maintenance' && nav.includes(page) ? <PreventiveMaintenancePage role={user.role}/> :
                page === 'notifications' && nav.includes(page) ? <NotificationsPage /> : page === 'inspections' && nav.includes(page) ? <InspectionsPage user={user}/> :
                    page === 'mobile-money' && nav.includes(page) ? <MobileMoneyPage /> : page === 'efris' && nav.includes(page) ? <FiscalPage /> :
                        page === 'documents' && nav.includes(page) ? <DocumentsPage /> : page === 'legal' && nav.includes(page) ? <LegalAdminPage /> :
                            page === 'audit' && nav.includes(page) ? <AuditPage /> : page === 'inquiries' && nav.includes(page) ? <ContactInboxPage /> :
                                page === 'invitations' && nav.includes(page) ? <InvitationsPage /> :
                                    page === 'proration' && nav.includes(page) ? <ProrationPage role={user.role}/> :
                                        page === 'expense-approvals' && nav.includes(page) ? <ExpenseApprovalsPage role={user.role}/> :
                                            page === 'trends' && nav.includes(page) ? <AnnualTrendsPage /> :
                                                page === 'permissions' && nav.includes(page) ? <PermissionMatrixPage user={user}/> :
                                                    page === 'room-placement' && nav.includes(page) ? <RoomPlacementPage /> :
                                                        page === 'portfolio-editor' && nav.includes(page) ? <PortfolioEditPage /> :
                                                            page === 'renewals' && nav.includes(page) ? <RenewalsPage role={user.role}/> : page === 'deposits' && nav.includes(page) ? <DepositsPage user={user}/> :
                                                                page === 'work-orders' && nav.includes(page) ? <WorkOrdersPage user={user}/> :
                                                                    page === 'settings' && nav.includes(page) ? <SettingsAdminPage /> : page === 'security' && nav.includes(page) ? <SecurityPage onSignedOut={logout}/> :
                                                                        page === 'reports' && canOperate ? <ReportsPage /> : page === 'dashboard' ? (canOperate ? <Dashboard user={user}/> : user.role === 'TENANT' ? <TenantHome /> : user.role === 'CARETAKER' ? <CaretakerHome /> : <div className="page"><h1>Workspace</h1><p>Your role does not yet have an assigned operational portal.</p></div>) : viewResource && nav.includes(page) ? <ResourcePage resource={viewResource} user={user}/> : <div className="page"><h1>Access restricted</h1><p>This area is not available to your account.</p></div>}</Suspense></main>
      <div className="portal-footnote"><span>© {new Date().getFullYear()} KATS Property Management</span><nav aria-label="Workspace legal and support"><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><Link to="/data-protection">Data protection</Link><Link to="/request-access">Request access</Link></nav></div>
    </div>
  </div>;
}
export default function App() {
    const [user, setUser] = useState(null);
    const [ready, setReady] = useState(false);
    const [online, setOnline] = useState(navigator.onLine);
    // A successful Vite HTML fallback must never count as backend readiness.
    // Only Flask's JSON response plus request ID confirms API ↔ DB availability.
    const [systemReady, setSystemReady] = useState(null);
    useEffect(() => {
        let active = true;
        const check = async () => {
            try {
                const response = await fetch('/readyz', { cache: 'no-store', signal: AbortSignal.timeout(5000) });
                const result = await response.json();
                if (active) setSystemReady(response.ok && result.status === 'ready'
                    && Boolean(response.headers.get('X-Request-ID')));
            } catch {
                if (active) setSystemReady(false);
            }
        };
        void check();
        const wake = () => { if (!document.hidden && navigator.onLine) void check(); };
        // Probe less often under load, but refresh immediately on network
        // recovery or when the operator returns to the active workspace.
        const id = window.setInterval(wake, 90000);
        window.addEventListener('online', wake);
        document.addEventListener('visibilitychange', wake);
        return () => {
            active = false;
            window.clearInterval(id);
            window.removeEventListener('online', wake);
            document.removeEventListener('visibilitychange', wake);
        };
    }, []);

    const navigate = useNavigate();
    useEffect(() => { api('auth/me').then(p => setUser(p.user)).catch(() => { }).finally(() => setReady(true)); }, []);
    useEffect(() => {
        const expired = () => setUser(null);
        window.addEventListener('kats:session-expired', expired);
        return () => window.removeEventListener('kats:session-expired', expired);
    }, []);
    useEffect(() => { const update = () => setOnline(navigator.onLine); window.addEventListener('online', update); window.addEventListener('offline', update); return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update); }; }, []);
    function logout() { api('auth/logout', { method: 'POST' }).catch(() => { }).finally(() => { setUser(null); navigate('/'); }); }
    if (!ready)
        return <div className="loading">Loading Kats…</div>;
    return <>{!online && <div className="offline" role="status">Offline. Reconnect to view private records.</div>}<Suspense fallback={<div className="loading" role="status">Opening page…</div>}><Routes>
    <Route element={<PublicShell user={user} logout={logout}/>}>
      <Route path="/" element={<LandingPage user={user}/>}/>
      <Route path="/features" element={<Navigate to="/#capabilities" replace/>}/>
      <Route path="/how-it-works" element={<Navigate to="/#workflow" replace/>}/>
      <Route path="/about" element={<Navigate to="/#about" replace/>}/>
      <Route path="/request-access" element={<RequestAccessPage/>}/>
      <Route path="/image-attributions" element={<ImageAttributionsPage/>}/>
      <Route path="/contact" element={<Navigate to="/request-access" replace/>}/>
      <Route path="/pricing" element={<Navigate to="/request-access" replace/>}/>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace/> : <Login onSuccess={setUser}/>}/>
      <Route path="/forgot-password" element={<ForgotPasswordPage/>}/>
      <Route path="/reset-password" element={<CompleteAccountLinkPage kind="reset"/>}/>
      <Route path="/account/activate" element={<CompleteAccountLinkPage kind="invitation"/>}/>
      {['privacy','terms','cookies','refund','data-protection','acceptable-use','disclaimer','accessibility'].map(slug=>
        <Route key={slug} path={'/'+slug} element={<LegalPage slug={slug}/>}/>
      )}
    </Route>
    {['dashboard', 'properties', 'buildings', 'floors', 'rooms', 'room-placement', 'portfolio-editor', 'tenants', 'leases', 'proration', 'invoices', 'payments', 'utilities', 'maintenance', 'expenses', 'expense-approvals', 'reports', 'trends', 'statements', 'receipts', 'users', 'invitations', 'permissions', 'assignments', 'notifications', 'inspections', 'renewals', 'deposits', 'work-orders', 'settings', 'mobile-money', 'efris', 'documents', 'legal', 'audit', 'inquiries', 'privacy-requests', 'disputes', 'preventive-maintenance', 'security', 'more'].map(path => <Route key={path} path={'/' + path} element={user ? <Portal user={user} logout={logout} systemReady={systemReady}/> : <Navigate to="/login" replace/>}/>)}
    {['dashboard', 'payments', 'invoices', 'receipts', 'maintenance', 'lease', 'profile'].map(path => <Route key={'tenant-' + path} path={'/tenant/' + path} element={<Navigate to={path === 'lease' ? '/dashboard' : path === 'profile' ? '/security' : '/' + path} replace/>}/>)}
    {['dashboard', 'rooms', 'maintenance', 'inspections', 'payments', 'profile'].map(path => <Route key={'caretaker-' + path} path={'/caretaker/' + path} element={<Navigate to={path === 'profile' ? '/security' : '/' + path} replace/>}/>)}
    {['users', 'roles', 'permissions', 'integrations', 'efris', 'payments', 'audit-logs', 'legal-pages', 'system-settings'].map(path => <Route key={'admin-' + path} path={'/admin/' + path} element={<Navigate to={path === 'audit-logs' ? '/audit' : path === 'legal-pages' ? '/legal' : path === 'system-settings' ? '/security' :
                    path === 'integrations' ? '/efris' : path === 'roles' || path === 'permissions' ? '/permissions' : '/' + path} replace/>}/>)}
    <Route path="*" element={<NotFoundPage/>}/>
  </Routes></Suspense></>;
}
