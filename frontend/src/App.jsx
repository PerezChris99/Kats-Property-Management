import { api } from './lib/api';
import { WorkspaceNavigation } from './WorkspaceNavigation';
import { Suspense, lazy, useCallback, useEffect, useState } from 'react';
const ProrationPage = lazy(() => import('./ProrationPage').then(m => ({ default: m.ProrationPage })));
const UtilitiesPage = lazy(() => import('./UtilitiesPage').then(m => ({ default: m.UtilitiesPage })));
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
const PublicLegalPage = lazy(() => import('./Modules').then(m => ({ default: m.PublicLegalPage })));
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
const ContactPage = lazy(() => import('./Modules').then(m => ({ default: m.ContactPage })));
const ContactInboxPage = lazy(() => import('./Modules').then(m => ({ default: m.ContactInboxPage })));
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Building2, CreditCard, LayoutDashboard, ShieldCheck, Wrench } from 'lucide-react';
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
function Header({ user, logout }) {
    return <header className="site-header"><Link to="/" className="brand"><Building2 size={24} aria-hidden="true"/> Kats <small>Property Management</small></Link>
  <nav aria-label="Main navigation">{user ? <><Link to="/dashboard">Workspace</Link><button className="link-button" onClick={logout}>Sign out</button></> : <><Link to="/features">Features</Link><Link to="/contact">Contact</Link><Link className="button small" to="/login">Sign in</Link></>}</nav></header>;
}
function Footer() { return <footer><span>© {new Date().getFullYear()} Kats Properties. All rights reserved. Proprietary software.</span><nav aria-label="Legal"><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><Link to="/cookies">Cookies</Link><Link to="/contact">Support</Link></nav></footer>; }
function Landing({ user, logout }) {
    const features = [{ icon: Building2, title: 'Property oversight', body: 'Know which units are occupied and what rent is due.' },
        { icon: CreditCard, title: 'Verified collections', body: 'Review cash and bank records before counting them as collected.' },
        { icon: Wrench, title: 'Maintenance tracking', body: 'Keep requests visible and actionable.' },
        { icon: ShieldCheck, title: 'Fiscal readiness', body: 'Prepare records for applicable EFRIS requirements.' }];
    return <><Header user={user} logout={logout}/><main><section className="hero"><div><span className="eyebrow">BUILT FOR UGANDAN RENTALS</span><h1>Manage your rentals, collect rent, and stay compliant.</h1><p>One organized view of rooms, tenants, rent, arrears, maintenance and property expenses.</p><div className="actions"><Link className="button" to={user ? '/dashboard' : '/contact'}>Get started</Link><Link className="button outline" to="/features">Explore features</Link></div></div>
  <div className="mock"><div className="mock-top"><LayoutDashboard size={20}/> Rental portfolio</div><div className="mock-number"><small>Monthly collections</small><strong>UGX —</strong><span>Live totals are available after sign-in</span></div><div className="mock-duo"><div><small>Occupancy</small><strong>—</strong></div><div><small>Arrears</small><strong>—</strong></div></div><div className="mock-caption">No fabricated balances</div></div></section>
  <section className="section"><span className="eyebrow">A SINGLE SOURCE OF TRUTH</span><h2>Leave scattered notebooks, Excel sheets and payment screenshots behind.</h2><p>From vacant rooms to unpaid invoices, bring the important facts into the same secure workflow.</p></section>
  <section className="section"><h2>Tools for the work that matters.</h2><div className="features">{features.map(f => <article className="feature" key={f.title}><f.icon size={24}/><h3>{f.title}</h3><p>{f.body}</p></article>)}</div></section>
  <section className="section process"><h2>How it works</h2><ol><li>Add properties and rooms</li><li>Register tenants and leases</li><li>Issue invoices and confirm collections</li><li>Track maintenance and property expenses</li><li>Review business performance</li></ol></section>
  <section className="section highlight"><h2>One rental business. One clear picture.</h2><p>Designed for practical Ugandan rental workflows, with UGX-native accounting records and mobile-first navigation.</p><Link className="button" to="/contact">Get in touch</Link></section></main><Footer /></>;
}
function TextPage({ title, body, user, logout }) {
    return <><Header user={user} logout={logout}/><main className="section simple"><h1>{title}</h1><p>{body}</p></main><Footer /></>;
}
function Login({ onSuccess }) {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    async function submit(event) {
        event.preventDefault();
        setBusy(true);
        setError('');
        try {
            const payload = await api('auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
            onSuccess(payload.user);
            navigate('/dashboard');
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Unable to sign in');
        }
        finally {
            setBusy(false);
        }
    }
    return <div className="auth-layout"><div className="auth-card"><Link to="/" className="brand"><Building2 /> Kats</Link><h1>Sign in</h1><p>Secure access for authorized users.</p><form onSubmit={submit}><label>Email<input type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required/></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required/></label>{error && <p role="alert" className="error">{error}</p>}<button className="button full" disabled={busy}>{busy ? 'Signing in…' : 'Continue'}</button></form><Link to="/forgot-password" className="back">Forgot your password?</Link> <Link to="/" className="back">Back to website</Link></div></div>;
}
function ResourcePage({ resource, user }) {
    const [rows, setRows] = useState([]);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [total, setTotal] = useState(null);
    const [filter, setFilter] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [editing, setEditing] = useState(false);
    const [values, setValues] = useState({});
    const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
    const [busy, setBusy] = useState(false);
    const [references, setReferences] = useState({});
    const canWrite = resource.writable?.includes(user.role) ?? false;
    const search = filter.trim().toLowerCase();
    const visibleRows = search ? rows.filter(row => Object.values(row).some(value => String(value ?? '').toLowerCase().includes(search))) : rows;
    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const join = resource.path.includes('?') ? '&' : '?';
            const payload = await api(resource.path + join + 'page=' + page + '&page_size=' + pageSize + '&include_total=0');
            setRows(payload.items || []);
            setTotal(typeof payload.total === 'number' ? payload.total : null);
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Could not load');
        }
        finally {
            setLoading(false);
        }
    }, [resource.path, page, pageSize]);
    useEffect(() => { void load(); }, [load]);
    useEffect(() => { setPage(1); setFilter(''); }, [resource.path]);
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
    {error && <p role="alert" className="error">{error}</p>}
    {editing && canWrite && <form className="resource-form" onSubmit={submit}><h2>New record</h2><div className="fields">{resource.fields.filter(field => field.name !== 'idempotency_key').map(field => <label key={field.name}>{field.label}{field.options ? <select value={values[field.name] || ''} onChange={e => setValues({ ...values, [field.name]: e.target.value })} required={field.required}><option value="">Select</option>{field.options.map(option => <option key={option}>{option}</option>)}</select> : references[field.name]?.length ? <select value={values[field.name] || ''} onChange={e => setValues({ ...values, [field.name]: e.target.value })} required={field.required}><option value="">Select a record</option>{references[field.name].map(row => <option key={String(row.id)} value={String(row.id)}>{String(row.name || row.number || row.full_name || row.invoice_number || row.email || row.title || row.id)}</option>)}</select> : <input required={field.required} type={field.type || 'text'} min={field.type === 'number' ? (field.name === 'level' ? '-10' : '0') : undefined} value={values[field.name] || ''} onChange={e => setValues({ ...values, [field.name]: e.target.value })}/>}</label>)}</div><button className="button" disabled={busy}>{busy ? 'Saving…' : 'Save record'}</button></form>}
    {!loading && rows.length > 0 && <div className="record-toolbar">
      <label className="record-filter">Filter loaded records
        <input type="search" placeholder="Search this table" value={filter} onChange={event => setFilter(event.target.value)}/></label>
      <span aria-live="polite">{visibleRows.length} of {rows.length} loaded</span>
    </div>}
    {loading ? <p role="status" className="data-loading">Loading records…</p> : rows.length === 0 ? <div className="empty"><h2>No records yet</h2><p>Authorized records will appear here after they are created.</p></div> : visibleRows.length === 0 ? <div className="empty"><h2>No matching records</h2><p>Clear the filter to see the loaded records.</p><button type="button" className="outline-button" onClick={() => setFilter('')}>Clear filter</button></div> : <div className="data-table-wrap"><table><thead><tr>{resource.columns.map(col => <th key={col}>{col.replaceAll('_', ' ')}</th>)}{resource.path === 'payments' && canWrite && <th>Review</th>}{(resource.path === 'payments' && ['OWNER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role) || resource.path === 'invoices' && ['OWNER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role) || resource.path === 'caretaker/rooms' || resource.path === 'caretaker/assignments' || resource.path === 'admin/users') && <th>Actions</th>}</tr></thead><tbody>{visibleRows.map((item, i) => <tr key={String(item.id || i)}>{resource.columns.map(col => <td key={col}><DataCell column={col} value={item[col]}/></td>)}{resource.path === 'payments' && canWrite && <td>{item.status === 'PENDING_REVIEW' ? <button className="outline-button" disabled={busy} onClick={() => approve(String(item.id))}>Approve*</button> : <span>—</span>}</td>}
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
    {resource.path === 'payments' && <p className="note">*Approval requires another staff member to verify source evidence. Approval credits the invoice; authorized owners or accountants can post an auditable accounting reversal. Reversal never automatically refunds cash.</p>}
    <p className="note">Access is enforced by the server. Search filters this page only; use Previous / Next to browse more records.</p></section>;
}
function Dashboard({ user }) {
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState('');
    useEffect(() => { api('dashboard').then(setSummary).catch(err => setError(String(err))); }, []);
    return <section className="page"><span className="eyebrow">PORTFOLIO OVERVIEW</span><h1>Welcome, {user.full_name.split(' ')[0]}</h1><p>Current recorded balances, not estimates of unverified payments.</p>{error && <p role="alert" className="error">{error}</p>}{!summary ? <p>Loading dashboard…</p> : <div className="stat-grid">
  {[['Expected', summary.expected_ugx, true], ['Collected', summary.collected_ugx, true], ['Outstanding', summary.outstanding_ugx, true], ['Occupied rooms', summary.occupied_rooms, false], ['Vacant / other rooms', summary.vacant_rooms, false], ['Open maintenance', summary.open_maintenance, false]].map(([label, value, currency]) => <div className="stat" key={String(label)}><small>{label}</small><strong>{currency ? 'UGX ' : ''}{Number(value).toLocaleString('en-UG')}</strong></div>)}</div>}
  <div className="quick"><h2>Common actions</h2><Link to="/properties">Properties</Link><Link to="/rooms">Rooms</Link><Link to="/invoices">Invoices</Link><Link to="/payments">Payments</Link></div></section>;
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
    useEffect(() => { Promise.all([api('tenant/dashboard'), api('tenant/lease')]).then(([s, l]) => { setSummary(s); setLease(l.lease); }).catch(err => setError(String(err))); }, []);
    return <section className="page"><span className="eyebrow">TENANT PORTAL</span><h1>My rental account</h1><p>Your current lease and recorded rent activity.</p>
    {error && <p role="alert" className="error">{error}</p>}
    {summary ? <div className="stat-grid"><div className="stat"><small>Invoiced</small><strong>UGX {summary.total_ugx.toLocaleString('en-UG')}</strong></div><div className="stat"><small>Paid</small><strong>UGX {summary.paid_ugx.toLocaleString('en-UG')}</strong></div><div className="stat"><small>Outstanding</small><strong>UGX {summary.outstanding_ugx.toLocaleString('en-UG')}</strong></div></div> : <p>Loading rent summary…</p>}
    <div className="quick"><h2>My lease</h2>{lease ? <p>Room reference: {lease.room_id}. Rent: UGX {Number(lease.rent_ugx).toLocaleString('en-UG')}. Ends: {lease.end_date}.</p> : <p>No active lease is currently linked to your account.</p>}<Link to="/invoices">Invoices</Link><Link to="/payments">Payments</Link><Link to="/maintenance">Maintenance</Link></div>
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
function Portal({ user, logout }) {
    const location = useLocation();
    const page = location.pathname.slice(1);
    const canOperate = roles.includes(user.role);
    const nav = canOperate ? ['dashboard', 'properties', 'buildings', 'floors', 'rooms', 'room-placement', 'portfolio-editor', 'tenants', 'leases', 'proration', 'invoices', 'payments', 'utilities', 'maintenance', 'expenses', 'expense-approvals', 'reports', 'trends', 'statements', 'receipts', 'mobile-money', 'efris', 'inspections', 'renewals', 'deposits', 'work-orders', 'documents', 'notifications', 'security', ...(user.role === 'OWNER' || user.role === 'SUPER_ADMIN' ? ['settings'] : []), ...(user.role === 'OWNER' || user.role === 'SUPER_ADMIN' ? ['users', 'invitations', 'permissions', 'legal', 'audit', 'inquiries'] : []), ...(user.role === 'OWNER' || user.role === 'SUPER_ADMIN' || user.role === 'MANAGER' ? ['assignments'] : [])] : user.role === 'CARETAKER' ? ['dashboard', 'rooms', 'payments', 'utilities', 'maintenance', 'work-orders', 'inspections', 'documents', 'notifications', 'security', 'receipts'] : ['dashboard', 'invoices', 'payments', 'utilities', 'statements', 'receipts', 'deposits', 'maintenance', 'inspections', 'documents', 'mobile-money', 'notifications', 'security'];
    const viewResource = user.role === 'CARETAKER' ? CARETAKER_RESOURCES[page] : RESOURCES[page];
    const pageTitle = page.replaceAll('-', ' ').replace(/^./, c => c.toUpperCase());
    return <div className="portal">
    <WorkspaceNavigation pages={nav} active={page} user={user} onLogout={logout}/>
    <div className="portal-main">
      <header className="portal-bar">
        <div className="portal-location">
          <span>Workspace <span aria-hidden="true">/</span> {pageTitle}</span>
          <strong>{pageTitle}</strong>
        </div>
        <div className="portal-identity" title={user.full_name}>
          <span className="identity-avatar" aria-hidden="true">{user.full_name.trim().charAt(0).toUpperCase()}</span>
          <span><strong>{user.full_name}</strong><small>{user.role.replaceAll('_', ' ')}</small></span>
        </div>
      </header>
      <main className="portal-content" key={page}><Suspense fallback={<p className="data-loading" role="status">Opening workspace…</p>}>{page === 'more' ? <section className="page"><span className="eyebrow">YOUR WORKSPACE</span><h1>More</h1><div className="quick">{nav.map(key => <Link key={key} to={'/' + key}>{key[0].toUpperCase() + key.slice(1)}</Link>)}</div><button className="button" onClick={logout}>Sign out</button></section> : page === 'statements' && nav.includes(page) ? (user.role === 'TENANT' ? <TenantStatementSelfPage /> : <TenantStatementsPage />) :
            page === 'receipts' && nav.includes(page) ? <ReceiptsPage /> :
                page === 'utilities' && nav.includes(page) ? <UtilitiesPage role={user.role}/> :
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
                                                            page === 'renewals' && nav.includes(page) ? <RenewalsPage /> : page === 'deposits' && nav.includes(page) ? <DepositsPage user={user}/> :
                                                                page === 'work-orders' && nav.includes(page) ? <WorkOrdersPage user={user}/> :
                                                                    page === 'settings' && nav.includes(page) ? <SettingsAdminPage /> : page === 'security' && nav.includes(page) ? <SecurityPage onSignedOut={logout}/> :
                                                                        page === 'reports' && canOperate ? <ReportsPage /> : page === 'dashboard' ? (canOperate ? <Dashboard user={user}/> : user.role === 'TENANT' ? <TenantHome /> : user.role === 'CARETAKER' ? <CaretakerHome /> : <div className="page"><h1>Workspace</h1><p>Your role does not yet have an assigned operational portal.</p></div>) : viewResource && nav.includes(page) ? <ResourcePage resource={viewResource} user={user}/> : <div className="page"><h1>Access restricted</h1><p>This area is not available to your account.</p></div>}</Suspense></main>
    </div>
  </div>;
}
export default function App() {
    const [user, setUser] = useState(null);
    const [ready, setReady] = useState(false);
    const [online, setOnline] = useState(navigator.onLine);
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
    <Route path="/" element={<Landing user={user} logout={logout}/>}/>
    <Route path="/login" element={user ? <Navigate to="/dashboard" replace/> : <Login onSuccess={setUser}/>}/>
    <Route path="/forgot-password" element={<ForgotPasswordPage />}/>
    <Route path="/reset-password" element={<CompleteAccountLinkPage kind="reset"/>}/>
    <Route path="/account/activate" element={<CompleteAccountLinkPage kind="invitation"/>}/>
    <Route path="/features" element={<TextPage title="Features" body="Manage units, leases, invoices, verified manual payments, maintenance and expenses. MTN/Airtel and EFRIS require provider verification." user={user} logout={logout}/>}/>
    <Route path="/contact" element={<ContactPage />}/>
    {['privacy', 'terms', 'cookies', 'refund'].map(slug => <Route key={slug} path={'/' + slug} element={<PublicLegalPage slug={slug}/>}/>)}
    {['dashboard', 'properties', 'buildings', 'floors', 'rooms', 'room-placement', 'portfolio-editor', 'tenants', 'leases', 'proration', 'invoices', 'payments', 'utilities', 'maintenance', 'expenses', 'expense-approvals', 'reports', 'trends', 'statements', 'receipts', 'users', 'invitations', 'permissions', 'assignments', 'notifications', 'inspections', 'renewals', 'deposits', 'work-orders', 'settings', 'mobile-money', 'efris', 'documents', 'legal', 'audit', 'inquiries', 'security', 'more'].map(path => <Route key={path} path={'/' + path} element={user ? <Portal user={user} logout={logout}/> : <Navigate to="/login" replace/>}/>)}
    {['dashboard', 'payments', 'invoices', 'receipts', 'maintenance', 'lease', 'profile'].map(path => <Route key={'tenant-' + path} path={'/tenant/' + path} element={<Navigate to={path === 'lease' ? '/dashboard' : path === 'profile' ? '/security' : '/' + path} replace/>}/>)}
    {['dashboard', 'rooms', 'maintenance', 'inspections', 'payments', 'profile'].map(path => <Route key={'caretaker-' + path} path={'/caretaker/' + path} element={<Navigate to={path === 'profile' ? '/security' : '/' + path} replace/>}/>)}
    {['users', 'roles', 'permissions', 'integrations', 'efris', 'payments', 'audit-logs', 'legal-pages', 'system-settings'].map(path => <Route key={'admin-' + path} path={'/admin/' + path} element={<Navigate to={path === 'audit-logs' ? '/audit' : path === 'legal-pages' ? '/legal' : path === 'system-settings' ? '/security' :
                    path === 'integrations' ? '/efris' : path === 'roles' || path === 'permissions' ? '/permissions' : '/' + path} replace/>}/>)}
    <Route path="/how-it-works" element={<TextPage title="How it works" body="Create properties and rooms, onboard tenants and leases, issue rent invoices, verify collections, track maintenance and review reports." user={user} logout={logout}/>}/>
    <Route path="/pricing" element={<TextPage title="Pricing" body="Contact the property owner for deployment and service pricing." user={user} logout={logout}/>}/>
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes></Suspense></>;
}
