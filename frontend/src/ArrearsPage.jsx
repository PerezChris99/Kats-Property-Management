import { useEffect, useState } from 'react';
import { api } from './lib/api';
import { ChartPanel } from './charts/WorkspaceAnalytics';

const money = amount => 'UGX '+Number(amount||0).toLocaleString('en-UG');

export default function ArrearsPage() {
  const [page,setPage]=useState(1);
  const [revision,setRevision]=useState(0);
  const [state,setState]=useState({loading:true,error:'',data:null});
  useEffect(()=>{
    const controller=new AbortController();
    setState({loading:true,error:'',data:null});
    api('finance/arrears-invoices?page='+page+'&page_size=25',{signal:controller.signal})
      .then(data=>{if(!controller.signal.aborted)setState({loading:false,error:'',data});})
      .catch(error=>{if(!controller.signal.aborted)setState({
        loading:false,error:error instanceof Error?error.message:'Could not load arrears',data:null
      });});
    return ()=>controller.abort();
  },[page,revision]);
  const data=state.data;
  return <section className="page">
    <div className="page-head"><div>
      <span className="eyebrow">RENT CONTROL</span>
      <h1>Overdue rent</h1>
      <p>Unpaid issued invoices, aged from their due dates in Uganda local time.</p>
    </div><button type="button" className="outline-button" onClick={()=>setRevision(n=>n+1)}>Refresh</button></div>
    <div className="kats-chart-grid">
      <ChartPanel title="Outstanding rent by age" endpoint="finance/arrears-aging" kind="bar" className="kats-chart-wide"/>
    </div>
    <h2>Overdue invoices</h2>
    {state.loading && <p role="status" className="data-loading">Loading overdue invoices…</p>}
    {state.error && <p role="alert" className="error">{state.error}
      <button type="button" className="outline-button small" onClick={()=>setRevision(n=>n+1)}>Retry</button></p>}
    {data && (data.items.length ? <>
      <div className="data-table-wrap"><table>
        <thead><tr><th>Invoice</th><th>Tenant</th><th>Due date</th><th>Outstanding</th><th>Status</th></tr></thead>
        <tbody>{data.items.map(row=><tr key={row.invoice_id}>
          <td>{row.invoice_number}</td><td>{row.tenant_name}</td><td>{row.due_date}</td>
          <td>{money(row.outstanding_ugx)}</td><td>{row.status}</td>
        </tr>)}</tbody>
      </table></div>
      <nav className="pagination-controls" aria-label="Overdue invoices pagination">
        <button type="button" className="outline-button small" disabled={page<=1} onClick={()=>setPage(n=>n-1)}>Previous</button>
        <span>Page {page} of {Math.max(1,Math.ceil(data.total/25))}</span>
        <button type="button" className="outline-button small" disabled={page*25>=data.total} onClick={()=>setPage(n=>n+1)}>Next</button>
      </nav>
    </> : <p className="empty" role="status">No overdue unpaid invoices recorded.</p>)}
    <p className="note">This is invoice debt, not proof of bank-settled cash. Check reconciled payment records before any financial action.</p>
  </section>;
}
