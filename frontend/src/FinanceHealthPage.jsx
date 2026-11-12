import { useCallback, useEffect, useState } from 'react';
import { api } from './lib/api';

const money = number => 'UGX ' + Number(number || 0).toLocaleString('en-UG');

/** An audit tool. It never modifies invoices, payments, or ledgers. */
export default function FinanceHealthPage() {
  const [page, setPage] = useState(1);
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState({status:'loading', data:null, error:''});
  const refresh = useCallback(() => setRetry(n => n + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setState({status:'loading',data:null,error:''});
    api('finance/reconciliation?page='+page+'&page_size=25',{signal:controller.signal})
      .then(data => { if (!controller.signal.aborted) setState({status:'ready',data,error:''}); })
      .catch(error => { if (!controller.signal.aborted) setState({
        status:'error',data:null,error:error instanceof Error ? error.message : 'Unable to load reconciliation'
      }); });
    return () => controller.abort();
  }, [page,retry]);
  const data=state.data;
  return <section className="page">
    <div className="page-head">
      <div><span className="eyebrow">FINANCE CONTROL</span><h1>Reconciliation exceptions</h1>
        <p>Verified internal payment records versus invoice-applied balances. No changes are made here.</p></div>
      <button className="outline-button" type="button" onClick={refresh}>Refresh</button>
    </div>
    {state.status==='loading' && <div className="data-loading" role="status">Checking verified payments and invoice balances…</div>}
    {state.status==='error' && <div className="error" role="alert">{state.error} <button className="outline-button small" onClick={refresh}>Retry</button></div>}
    {state.status==='ready' && <>
      <div className="stat-grid"><div className="stat"><small>Unresolved internal discrepancies</small><strong>{data.total_exceptions.toLocaleString('en-UG')}</strong></div></div>
      {data.total_exceptions===0 ? <div className="empty" role="status">
        <h2>No internal reconciliation exceptions</h2>
        <p>Recorded verified payment totals match invoice-applied amounts. Bank reconciliation is still required.</p>
      </div> : <div className="data-table-wrap"><table>
        <thead><tr><th>Invoice</th><th>Applied</th><th>Verified</th><th>Difference</th><th>Status</th></tr></thead>
        <tbody>{data.items.map(item=><tr key={item.invoice_id}>
          <td>{item.invoice_number}</td><td>{money(item.applied_ugx)}</td>
          <td>{money(item.verified_ugx)}</td><td>{money(item.difference_ugx)}</td>
          <td>{item.invoice_status}</td>
        </tr>)}</tbody>
      </table></div>}
      <nav className="pagination-controls" aria-label="Reconciliation pages">
        <button className="outline-button small" type="button" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Previous</button>
        <span>Page {page} of {Math.max(1,Math.ceil(data.total_exceptions/25))}</span>
        <button className="outline-button small" type="button" disabled={page*25>=data.total_exceptions} onClick={()=>setPage(p=>p+1)}>Next</button>
      </nav>
      <p className="note">{data.method}</p><p className="note">{data.action}</p>
    </>}
  </section>;
}
