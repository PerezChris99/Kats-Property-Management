import { useEffect, useState } from 'react';
import { api } from './lib/api';

const fmt = value => 'UGX ' + Number(value || 0).toLocaleString('en-UG');

export default function JournalControlPage() {
  const [refresh,setRefresh]=useState(0);
  const [state,setState]=useState({status:'loading',data:null,error:''});
  useEffect(()=>{
    const controller=new AbortController();
    setState({status:'loading',data:null,error:''});
    api('finance/journal-control',{signal:controller.signal}).then(data=>{
      if(!controller.signal.aborted) setState({status:'ready',data,error:''});
    }).catch(err=>{
      if(!controller.signal.aborted) setState({status:'error',data:null,error:err.message||'Could not load'});
    });
    return ()=>controller.abort();
  },[refresh]);
  const data=state.data;
  return <section className="page">
    <div className="page-head"><div><span className="eyebrow">ACCOUNTING CONTROLS</span>
      <h1>Receipt journal</h1>
      <p>Balanced entries for newly verified receipts and accounting reversals, not a complete general ledger.</p>
      </div><button type="button" className="outline-button" onClick={()=>setRefresh(n=>n+1)}>Refresh</button></div>
    {state.status==='loading' && <p className="data-loading" role="status">Calculating journal totals…</p>}
    {state.status==='error' && <p role="alert" className="error">{state.error}
      <button className="outline-button small" onClick={()=>setRefresh(n=>n+1)}>Retry</button></p>}
    {state.status==='ready' && <>
      <div className="stat-grid">
        <div className="stat"><small>Total debits</small><strong>{fmt(data.total_debit_ugx)}</strong></div>
        <div className="stat"><small>Total credits</small><strong>{fmt(data.total_credit_ugx)}</strong></div>
        <div className="stat"><small>Journal balance</small><strong>{data.balanced?'Balanced':'Mismatch — investigate'}</strong></div>
        <div className="stat"><small>Historic payments not journaled</small>
          <strong>{Number(data.legacy_reconciled_without_journal)+Number(data.legacy_reversed_without_journal)}</strong></div>
      </div>
      <div className="data-table-wrap"><table>
        <thead><tr><th>Account</th><th>Debit</th><th>Credit</th><th>Net debit</th></tr></thead>
        <tbody>{data.accounts.map(item=><tr key={item.code}><th scope="row">{item.code.replaceAll('_',' ')}</th>
          <td>{fmt(item.debit_ugx)}</td><td>{fmt(item.credit_ugx)}</td><td>{fmt(item.net_debit_ugx)}</td></tr>)}</tbody>
      </table></div>
      <p className="note">{data.warning}</p>
    </>}
  </section>;
}
