import { useEffect, useMemo, useState } from 'react';
import { api } from './lib/api';

const ugx = value => 'UGX ' + Number(value || 0).toLocaleString('en-UG');
const reportModes = [
  ['trial-balance', 'Trial balance'],
  ['balance-sheet', 'Balance sheet'],
  ['income-statement', 'Income statement'],
  ['detail', 'Journal detail']
];
function numeric(value) { return Number(value || 0).toLocaleString('en-UG'); }
function ErrorText({ message }) { return message ? <p className="error" role="alert">{message}</p> : null; }

export default function GeneralLedgerPage({ user }) {
  const [mode, setMode] = useState('trial-balance');
  const [through, setThrough] = useState('');
  const [from, setFrom] = useState('');
  const [account, setAccount] = useState('');
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [state, setState] = useState({loading:true, report:null, error:''});
  const [batchRows, setBatchRows] = useState([]);
  const [csv, setCsv] = useState('');
  const [effectiveOn, setEffectiveOn] = useState('');
  const [note, setNote] = useState('');
  const [period, setPeriod] = useState('');
  const [closeReason, setCloseReason] = useState('');
  const [action, setAction] = useState({busy:false,error:'',message:''});

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (through) params.set('through', through);
    if (from && ['income-statement','detail'].includes(mode)) params.set('from', from);
    if (mode === 'detail') {
      params.set('page', String(page)); params.set('page_size', '25');
      if (account) params.set('account_code', account);
    }
    return params.toString();
  }, [through, from, mode, account, page]);

  useEffect(() => {
    const abort = new AbortController();
    setState({loading:true,report:null,error:''});
    const url = 'finance/gl/' + mode + (query ? '?' + query : '');
    api(url,{signal:abort.signal})
      .then(report => { if (!abort.signal.aborted) setState({loading:false, report, error:''}); })
      .catch(error => { if (!abort.signal.aborted) setState({loading:false, report:null, error:error.message || 'Ledger unavailable'}); });
    return () => abort.abort();
  }, [mode, query, refresh]);

  useEffect(() => {
    const abort = new AbortController();
    api('finance/gl/opening-batches',{signal:abort.signal})
      .then(data => { if (!abort.signal.aborted) setBatchRows(data.items || []); })
      .catch(() => {});
    return () => abort.abort();
  }, [refresh]);

  async function submit(endpoint, payload, success) {
    setAction({busy:true,error:'',message:''});
    try {
      await api(endpoint, {method:'POST', body:JSON.stringify(payload)});
      setAction({busy:false,error:'',message:success});
      setRefresh(value=>value+1);
    } catch (error) {
      setAction({busy:false,error:error.message || 'Financial action declined',message:''});
    }
  }

  const report = state.report;
  return <section className="page kats-finance-page">
    <div className="page-head">
      <div>
        <span className="eyebrow">ACCOUNTING • UGANDA SHILLINGS</span>
        <h1>General ledger</h1>
        <p>Balanced, append-only accounting events. Historical balances remain incomplete until an accountant independently approves the opening trial balance.</p>
      </div>
      <button className="outline-button" type="button" onClick={()=>setRefresh(n=>n+1)}>Refresh</button>
    </div>
    <div className="kats-finance-mode" role="group" aria-label="General ledger report">
      {reportModes.map(([key,label])=><button type="button" key={key} aria-pressed={mode===key}
        className={mode===key ? 'button small' : 'outline-button small'}
        onClick={()=>{setMode(key);setPage(1);}}>{label}</button>)}
    </div>
    <div className="kats-finance-controls">
      <label>From date <input type="date" value={from} disabled={!['income-statement','detail'].includes(mode)} onChange={e=>setFrom(e.target.value)}/></label>
      <label>Through date <input type="date" value={through} onChange={e=>setThrough(e.target.value)}/></label>
      {mode==='detail' && <label>Account code <input type="text" maxLength={40} placeholder="All accounts" value={account} onChange={e=>{setAccount(e.target.value.toUpperCase());setPage(1);}}/></label>}
    </div>
    {state.loading && <p role="status" className="data-loading">Reading posted ledger events…</p>}
    <ErrorText message={state.error}/>
    {report && <>
      {report.coverage && <p className="note">Coverage: new posted GL events only. Original historical records are not silently reconstructed or duplicated.</p>}
      {report.warning && <p className="note" role="status">{report.warning}</p>}
      {mode==='trial-balance' && <>
        <div className="stat-grid">
          <div className="stat"><small>Total debit</small><strong>{ugx(report.debit_ugx)}</strong></div>
          <div className="stat"><small>Total credit</small><strong>{ugx(report.credit_ugx)}</strong></div>
          <div className="stat"><small>Difference</small><strong>{ugx(report.difference_ugx)}</strong></div>
          <div className="stat"><small>Ledger integrity</small><strong>{report.balanced?'Balanced':'Mismatch — investigate'}</strong></div>
        </div>
        <div className="data-table-wrap"><table><thead><tr><th>Account</th><th>Classification</th><th>Debits (UGX)</th><th>Credits (UGX)</th><th>Net debit</th></tr></thead><tbody>
        {(report.accounts || []).map(row=><tr key={row.code}><th scope="row">{row.code.replaceAll('_',' ')}</th><td>{row.kind}</td><td>{numeric(row.debit_ugx)}</td><td>{numeric(row.credit_ugx)}</td><td>{numeric(row.net_debit_ugx)}</td></tr>)}
        </tbody></table></div>
      </>}
      {mode==='balance-sheet' && <div className="stat-grid">
        {[['Assets',report.assets_ugx],['Liabilities',report.liabilities_ugx],['Equity',report.equity_ugx],['Unclosed profit',report.unclosed_profit_ugx],['Balance difference',report.difference_ugx]].map(([name,value])=>
          <div className="stat" key={name}><small>{name}</small><strong>{ugx(value)}</strong></div>)}
        <div className="stat"><small>Assets = liabilities + equity</small><strong>{report.balanced?'Balanced':'Mismatch — investigate'}</strong></div>
      </div>}
      {mode==='income-statement' && <>
        <div className="stat-grid"><div className="stat"><small>Revenue</small><strong>{ugx(report.total_revenue_ugx)}</strong></div><div className="stat"><small>Expenses</small><strong>{ugx(report.total_expense_ugx)}</strong></div><div className="stat"><small>Net income</small><strong>{ugx(report.net_income_ugx)}</strong></div></div>
        <div className="data-table-wrap"><table><thead><tr><th>Classification</th><th>Account</th><th>Amount (UGX)</th></tr></thead><tbody>
          {['revenues','expenses'].flatMap(category=>(report[category] || []).map(row=><tr key={category+row.code}><td>{category==='revenues'?'Revenue':'Expense'}</td><th scope="row">{row.name}</th><td>{numeric(row.amount_ugx)}</td></tr>))}
        </tbody></table></div>
      </>}
      {mode==='detail' && <>
        <div className="data-table-wrap"><table><thead><tr><th>Date</th><th>Source</th><th>Account</th><th>Debit</th><th>Credit</th></tr></thead><tbody>
        {(report.items || []).map((row,index)=><tr key={row.event_key+row.account_code+index}><td>{row.posted_on}</td><td>{row.event_kind} — {row.event_key}</td><td>{row.account_code}</td><td>{numeric(row.debit_ugx)}</td><td>{numeric(row.credit_ugx)}</td></tr>)}
        </tbody></table></div>
        <div className="pagination-controls"><button type="button" className="outline-button" disabled={page===1} onClick={()=>setPage(x=>Math.max(1,x-1))}>Previous</button><span>Page {page} • {report.total || 0} lines</span><button type="button" className="outline-button" disabled={page*25 >= (report.total||0)} onClick={()=>setPage(x=>x+1)}>Next</button></div>
      </>}
    </>}
    <section className="kats-finance-workflows" aria-labelledby="opening-title">
      <h2 id="opening-title">Historical opening balances</h2>
      <p className="note">Two-person approval is mandatory. A CSV import is only a proposal until reviewed; never upload an unapproved or unbalanced historical trial balance.</p>
      <form onSubmit={e=>{e.preventDefault();submit('finance/gl/opening-batches',{effective_on:effectiveOn,note,csv_text:csv},'Opening balance proposal submitted for independent review.');}}>
        <div className="kats-finance-controls">
          <label>Effective date <input type="date" required value={effectiveOn} onChange={e=>setEffectiveOn(e.target.value)}/></label>
          <label>Reason / evidence reference <input required maxLength={500} value={note} onChange={e=>setNote(e.target.value)}/></label>
          <label>CSV file <input type="file" accept=".csv,text/csv" onChange={async e=>{ const file=e.target.files?.[0];if(file){if(file.size>60000){setAction({busy:false,error:'CSV file exceeds 60 KB',message:''});return;}setCsv(await file.text());}}}/></label>
        </div>
        <label>Review CSV before submission<textarea required rows={4} maxLength={60000} spellCheck={false} placeholder={'account_code,debit_ugx,credit_ugx\nBANK,100000,0\nOWNER_EQUITY,0,100000'} value={csv} onChange={e=>setCsv(e.target.value)}/></label>
        <button type="submit" className="button" disabled={action.busy}>Submit for approval</button>
      </form>
      <h3>Opening batches</h3>
      <div className="data-table-wrap"><table><thead><tr><th>Effective date</th><th>Reason</th><th>Status</th><th>Review</th></tr></thead><tbody>
        {batchRows.map(batch=><tr key={batch.id}><td>{batch.effective_on}</td><td>{batch.note}</td><td>{batch.status}</td><td>{batch.status==='PENDING' && batch.submitted_by!==user?.id ? <div className="kats-finance-actions">
          <button disabled={action.busy} className="outline-button small" onClick={()=>{const reason=window.prompt('Reason for approving this signed-off opening trial balance');if(reason)submit('finance/gl/opening-batches/'+batch.id+'/review',{decision:'APPROVE',reason},'Opening entry posted.');}}>Approve</button>
          <button disabled={action.busy} className="outline-button small" onClick={()=>{const reason=window.prompt('Reason for rejecting this import');if(reason)submit('finance/gl/opening-batches/'+batch.id+'/review',{decision:'REJECT',reason},'Opening entry rejected.');}}>Reject</button>
        </div>:<span>{batch.status==='PENDING'?'Awaiting another reviewer':'Reviewed'}</span>}</td></tr>)}
        {batchRows.length===0&&<tr><td colSpan={4}>No opening-balance proposals.</td></tr>}
      </tbody></table></div>
    </section>
    <section className="kats-finance-workflows" aria-labelledby="period-close-title">
      <h2 id="period-close-title">Close a financial period</h2>
      <p className="note">Close only after reconciling accounts, payment evidence and approved opening balances. Closed periods reject future backdated postings.</p>
      <form className="kats-finance-controls" onSubmit={e=>{e.preventDefault();submit('finance/gl/periods/'+period+'/close',{reason:closeReason},'Financial period closed.');}}>
        <label>Accounting period <input type="month" required value={period} onChange={e=>setPeriod(e.target.value)}/></label>
        <label>Review reference <input required maxLength={500} value={closeReason} onChange={e=>setCloseReason(e.target.value)}/></label>
        <button type="submit" className="outline-button" disabled={action.busy}>Close reviewed period</button>
      </form>
    </section>
    <ErrorText message={action.error}/>
    {action.message && <p className="note" role="status">{action.message}</p>}
  </section>;
}
