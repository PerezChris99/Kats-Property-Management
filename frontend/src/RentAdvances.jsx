import { useCallback, useEffect, useState } from 'react';
import { api } from './lib/api';

const money = amount => 'UGX ' + Number(amount).toLocaleString('en-UG');

export default function RentAdvances({ user }) {
    const staff = ['OWNER', 'MANAGER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role);
    const [rows, setRows] = useState([]);
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [leases, setLeases] = useState([]);
    const [invoices, setInvoices] = useState([]);
    const [page, setPage] = useState(1);
    const [pages, setPages] = useState(0);
    const [selected, setSelected] = useState('');
    const [command, setCommand] = useState(() => crypto.randomUUID());
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [reload, setReload] = useState(0);
    const refresh = useCallback(() => setReload(value => value + 1), []);
    useEffect(() => {
        const controller = new AbortController();
        api('rent-advances?page=' + page, { signal: controller.signal }).then(data => {
            setRows(data.items); setPages(data.pages);
        }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
        return () => controller.abort();
    }, [page, reload]);

    const leaseId = rows.find(row => row.id === selected)?.lease_id;
    useEffect(() => {
        if (!open || !staff) return;
        const controller = new AbortController();
        const timer = setTimeout(() => {
            api('rent-advances/options?q=' + encodeURIComponent(query), {signal: controller.signal})
                .then(data => setLeases(data.items)).catch(e => { if (!controller.signal.aborted) setError(e.message); });
        }, 200);
        return () => { clearTimeout(timer); controller.abort(); };
    }, [open, staff, query]);
    useEffect(() => {
        if (!leaseId || !staff) return;
        const controller = new AbortController();
        api('rent-advances/options?lease_id=' + encodeURIComponent(leaseId), {signal: controller.signal})
            .then(data => setInvoices(data.items)).catch(e => { if (!controller.signal.aborted) setError(e.message); });
        return () => controller.abort();
    }, [leaseId, staff]);
    async function post(path, payload, form) {
        setBusy(true); setError('');
        try {
            await api('rent-advances' + path, {method: 'POST', body: JSON.stringify(payload)});
            form?.reset();
            setSelected('');
            setCommand(crypto.randomUUID());
            refresh();
        } catch (e) { setError(e.message); }
        finally { setBusy(false); }
    }
    function submit(event, path) {
        event.preventDefault();
        const form = event.currentTarget;
        const data = Object.fromEntries(new FormData(form));
        data.amount_ugx = Number(data.amount_ugx);
        data.idempotency_key = command;
        void post(path, data, form);
    }
    return <details className="module-card" onToggle={e => setOpen(e.currentTarget.open)}><summary>Advance rent and unapplied balances</summary>
        {error && <p role="alert">{error}</p>}
        {staff && <form className="resource-form" onSubmit={e => submit(e, '')}>
            <label>Find tenant <input value={query} onChange={e => setQuery(e.target.value)} /></label>
            <label>Lease <select name="lease_id" required><option value="">Choose lease</option>
                {leases.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
            <label>Amount in UGX <input type="number" min="1" step="1" name="amount_ugx" required /></label>
            <label>Received by <select name="method"><option value="CASH">Cash</option><option value="BANK_TRANSFER">Bank transfer</option></select></label>
            <label>Cash voucher or bank reference <input name="reference" required maxLength={160} /></label>
            <button disabled={busy}>Record advance</button>
        </form>}
        {rows.map(row => <article className="module-card" key={row.id}>
            <h3>{row.tenant} · {money(row.amount_ugx)}</h3>
            <p>{row.method} · {row.reference} · {row.status}</p>
            <p>Unapplied balance {money(row.available_ugx)}</p>
            <a href={'/api/v1/rent-advances/' + row.id + '/receipt.pdf'}>Download advance receipt</a>
            {staff && row.status === 'PENDING' && row.created_by !== user.id &&
                <button disabled={busy} onClick={() => post('/' + row.id + '/approve', {})}>Approve receipt</button>}
            {staff && row.available_ugx > 0 && <button onClick={() => { if (selected !== row.id) setInvoices([]); setSelected(row.id); }}>Apply to invoice</button>}
            {selected === row.id && <form onSubmit={e => submit(e, '/' + row.id + '/apply')}>
                <label>Open invoice <select name="invoice_id" required><option value="">Choose invoice</option>
                    {invoices.map(item => <option key={item.id} value={item.id}>{item.label} · {money(item.balance)}</option>)}
                </select></label>
                <label>Amount in UGX <input name="amount_ugx" type="number" min="1" max={row.available_ugx} required /></label>
                <button disabled={busy}>Apply credit</button>
            </form>}
            {['OWNER', 'ACCOUNTANT', 'SUPER_ADMIN'].includes(user.role) && row.status !== 'REVERSED' &&
                <button disabled={busy} onClick={() => {
                    const reason = window.prompt('Reason for correcting this advance receipt');
                    if (reason?.trim()) void post('/' + row.id + '/reverse', {reason});
                }}>Reverse receipt</button>}
        </article>)}
        {pages > 1 && <nav aria-label="Advance receipts"><button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
            <span> {page} / {pages} </span><button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button></nav>}
    </details>;
}
