import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './lib/api';

const money = x => 'UGX ' + Number(x || 0).toLocaleString('en-UG');
const errorText = x => x instanceof Error ? x.message : 'Bank reconciliation action failed';

export default function BankReconciliationPage({ user }) {
  const [items,setItems] = useState([]);
  const [selected,setSelected] = useState('');
  const [statement,setStatement] = useState(null);
  const [matches,setMatches] = useState([]);
  const [candidates,setCandidates] = useState([]);
  const [lineId,setLineId] = useState('');
  const [eventId,setEventId] = useState('');
  const [allocation,setAllocation] = useState('');
  const [bankLabel,setBankLabel] = useState('');
  const [accountMask,setAccountMask] = useState('');
  const [begin,setBegin] = useState('');
  const [finish,setFinish] = useState('');
  const [opening,setOpening] = useState('');
  const [closing,setClosing] = useState('');
  const [csv,setCsv] = useState('');
  const [reason,setReason] = useState('');
  const [refresh,setRefresh] = useState(0);
  const [loading,setLoading] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');

  useEffect(()=>{
    const controller=new AbortController();
    api('finance/bank-statements',{signal:controller.signal}).then(data=>{
      if (!controller.signal.aborted) {
        const list=data.items || [];
        setItems(list);
        setSelected(old => old && list.some(x=>x.id===old) ? old : list[0]?.id || '');
      }
    }).catch(err=>{if(!controller.signal.aborted)setError(errorText(err));});
    return ()=>controller.abort();
  },[refresh]);
  useEffect(()=>{
    const controller=new AbortController();
    if(!selected){setStatement(null);setMatches([]);return ()=>controller.abort();}
    setLoading(true);
    Promise.all([
      api('finance/bank-statements/'+selected,{signal:controller.signal}),
      api('finance/bank-statements/'+selected+'/matches',{signal:controller.signal})
    ]).then(([report,list])=>{
      if(!controller.signal.aborted){setStatement(report);setMatches(list.items||[]);}
    }).catch(err=>{if(!controller.signal.aborted)setError(errorText(err));})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[selected,refresh]);
  useEffect(()=>{
    const controller=new AbortController();
    if(!selected||!lineId){setCandidates([]);return ()=>controller.abort();}
    api('finance/bank-statements/'+selected+'/candidates/'+lineId,{signal:controller.signal})
      .then(data=>{if(!controller.signal.aborted)setCandidates(data.items||[]);})
      .catch(err=>{if(!controller.signal.aborted)setCandidates([]);});
    return ()=>controller.abort();
  },[selected,lineId,refresh]);

  const exceptions = useMemo(() => statement?.exceptions || [], [statement]);
  const eligibleLine = useMemo(() => exceptions.find(x => x.id === lineId), [exceptions, lineId]);
  const candidate = useMemo(()=>candidates.find(x=>x.id===eventId),[candidates,eventId]);

  const transaction = useCallback(async (path,payload,message)=>{
    setBusy(true);setError('');setNotice('');
    try {
      await api(path,{method:'POST',body:JSON.stringify(payload)});
      setNotice(message);
      setRefresh(x=>x+1);
    } catch(exc) {setError(errorText(exc));}
    finally{setBusy(false);}
  },[]);

  async function importCsv(event){
    event.preventDefault();
    setError('');
    if(!csv){setError('Choose or paste a bank statement CSV first.');return;}
    await transaction('finance/bank-statements',{
      bank_label:bankLabel, account_mask:accountMask,
      start_date:begin, end_date:finish,
      opening_ugx:Number(opening), closing_ugx:Number(closing), csv_text:csv,
    }, 'Statement imported as evidence. A different finance user must approve matches.');
  }
  const pending = matches.filter(x=>x.state==='PROPOSED');
  return <section className="page kats-finance-page">
    <div className="page-head"><div><span className="eyebrow">FINANCE • CASH AND BANK</span><h1>Bank reconciliation</h1>
      <p>Compare independently obtained bank statements against posted ledger activity. A statement import never confirms a payout or authorizes new revenue.</p></div>
      <button type="button" className="outline-button" onClick={()=>setRefresh(x=>x+1)}>Refresh</button>
    </div>
    <section className="kats-finance-workflows">
      <h2>Import a bank statement</h2>
      <p className="note">Required CSV columns: date,reference,description,inflow_ugx,outflow_ugx. Amounts are integer Uganda shillings and must reconcile to the stated opening/closing bank balances. Use the same bank label and masked account identifier on every import for that account. Give accounts with identical endings distinct labels.</p>
      <form onSubmit={importCsv}>
        <div className="kats-finance-controls">
          <label>Bank name <input required maxLength={120} value={bankLabel} onChange={e=>setBankLabel(e.target.value)} placeholder="Bank label"/></label>
          <label>Masked account <input required maxLength={30} placeholder="****1234" value={accountMask} onChange={e=>setAccountMask(e.target.value)}/></label>
          <label>Start date <input type="date" required value={begin} onChange={e=>setBegin(e.target.value)}/></label>
          <label>End date <input type="date" required value={finish} onChange={e=>setFinish(e.target.value)}/></label>
          <label>Opening UGX <input required type="number" step="1" value={opening} onChange={e=>setOpening(e.target.value)}/></label>
          <label>Closing UGX <input required type="number" step="1" value={closing} onChange={e=>setClosing(e.target.value)}/></label>
          <label>Statement CSV <input type="file" accept=".csv,text/csv" onChange={async e=>{
            const file=e.target.files?.[0];
            if(file){if(file.size>1024*1024){setError('CSV exceeds 1 MB');return;}setCsv(await file.text());}
          }}/></label>
        </div>
        <label>Review imported rows<textarea rows={3} required value={csv} onChange={e=>setCsv(e.target.value)}
          placeholder={'date,reference,description,inflow_ugx,outflow_ugx\n2026-01-05,REF-001,Tenant deposit,500000,0'}/></label>
        <button type="submit" disabled={busy} className="button">Import statement evidence</button>
      </form>
    </section>
    <div className="kats-finance-controls">
      <label>Bank statement<select value={selected} onChange={e=>{setSelected(e.target.value);setLineId('');setEventId('');}}>
        {items.length===0 && <option value="">No statements imported</option>}
        {items.map(row=><option value={row.id} key={row.id}>{row.bank_label} {row.account_mask} • {row.start_date} to {row.end_date} • {row.state}</option>)}
      </select></label>
    </div>
    {loading && <p role="status" className="data-loading">Loading bank and GL evidence…</p>}
    {statement && <>
      <p>Opening balance GL account: <code>{statement.statement.book_code}</code></p>
      <div className="stat-grid">
        <div className="stat"><small>Bank opening balance</small><strong>{money(statement.statement.opening_ugx)}</strong></div>
        <div className="stat"><small>Bank closing balance</small><strong>{money(statement.statement.closing_ugx)}</strong></div>
        <div className="stat"><small>Ledger bank closing</small><strong>{money(statement.book_closing_ugx)}</strong></div>
        <div className="stat"><small>Unreconciled difference</small><strong>{money(statement.closing_difference_ugx)}</strong></div>
        <div className="stat"><small>Statement exceptions</small><strong>{exceptions.length}</strong></div>
        <div className="stat"><small>Approval status</small><strong>{statement.statement.state}</strong></div>
      </div>
      <p className="note" role="status">{statement.warning}</p>
      <h2>Unmatched and partially matched transactions</h2>
      <div className="data-table-wrap"><table><thead><tr><th>Date</th><th>Bank reference</th><th>Description</th><th>Statement UGX</th><th>Remaining UGX</th><th>Status</th></tr></thead><tbody>
        {exceptions.map(row=><tr key={row.id}><td>{row.booked_on}</td><th scope="row">{row.reference||'—'}</th><td>{row.description}</td><td>{money(row.signed_ugx)}</td><td>{money(row.unmatched_ugx)}</td><td>{row.status}</td></tr>)}
        {exceptions.length===0 && <tr><td colSpan={6}>No unresolved statement lines.</td></tr>}
      </tbody></table></div>
      {statement.statement.state==='OPEN' && <section className="kats-finance-workflows">
        <h3>Propose a ledger match</h3>
        <p className="note">Bank inflows can match previously verified cash-clearance events. Bank outflows require a real, already-posted bank debit evidence workflow; no payment is initiated here.</p>
        <form className="kats-finance-controls" onSubmit={e=>{
          e.preventDefault();
          if(!eligibleLine||!candidate){setError('Choose a statement row and an eligible ledger source');return;}
          const amount=Number(allocation);
          transaction('finance/bank-statements/'+selected+'/matches',{
            line_id:lineId, gl_event_id:eventId,
            signed_ugx: eligibleLine.signed_ugx>0 ? amount : -amount,
          },'Bank match submitted for a different reviewer.');
        }}>
          <label>Statement line<select value={lineId} required onChange={e=>{setLineId(e.target.value);setEventId('');setAllocation('');}}>
            <option value="">Choose unmatched item</option>{exceptions.map(row=><option key={row.id} value={row.id}>{row.booked_on} • {row.reference} • {money(row.unmatched_ugx)}</option>)}
          </select></label>
          <label>Eligible posted GL event<select value={eventId} required onChange={e=>setEventId(e.target.value)}>
            <option value="">Choose candidate</option>{candidates.map(row=><option key={row.id} value={row.id}>{row.event_key} • {money(row.available_ugx)} • {row.days_apart} day(s) apart</option>)}
          </select></label>
          <label>Allocation (positive UGX)<input type="number" min="1" step="1" required value={allocation} onChange={e=>setAllocation(e.target.value)}/></label>
          <button type="submit" className="outline-button" disabled={busy||!candidate}>Propose matching</button>
        </form>
      </section>}
      <section className="kats-finance-workflows">
        <h3>Independent approval queue</h3>
        <label>Reason and evidence reference for approval <input value={reason} maxLength={500} onChange={e=>setReason(e.target.value)} placeholder="Verified against signed bank statement"/></label>
        <div className="data-table-wrap"><table><thead><tr><th>GL event</th><th>Amount</th><th>State</th><th>Review</th></tr></thead><tbody>
          {matches.map(row=><tr key={row.id}><td>{row.event_id}</td><td>{money(row.signed_ugx)}</td><td>{row.state}</td><td>
            {row.state==='PROPOSED' && row.proposed_by!==user?.id && statement.statement.imported_by!==user?.id ?
            <div className="kats-finance-actions"><button className="outline-button small" type="button" disabled={busy||!reason.trim()} onClick={()=>transaction('finance/bank-matches/'+row.id+'/review',{decision:'APPROVE',reason},'Match approved and bank ledger reviewed.')}>Approve</button>
              <button className="outline-button small" type="button" disabled={busy||!reason.trim()} onClick={()=>transaction('finance/bank-matches/'+row.id+'/review',{decision:'REJECT',reason},'Match rejected.')}>Reject</button></div> :
              <span>{row.state==='PROPOSED'?'Awaiting independent review':'Reviewed'}</span>}</td></tr>)}
          {matches.length===0 && <tr><td colSpan={4}>No matching proposals yet.</td></tr>}
        </tbody></table></div>
      </section>
      <div className="kats-finance-workflows">
        <h3>Close statement</h3>
        <p className="note">All rows must be fully matched, all proposals reviewed, and the GL opening and closing bank balances must match the imported statement exactly. The importer cannot close their own statement.</p>
        <button type="button" className="button" disabled={!statement.can_close||busy||statement.statement.state==='RECONCILED'||statement.statement.imported_by===user?.id||!reason.trim()}
          onClick={()=>transaction('finance/bank-statements/'+selected+'/close',{reason},'Bank statement closed after independent review and zero variance.')}>
          {statement.statement.state==='RECONCILED'?'Statement reconciled':'Close independently reviewed statement'}
        </button>
      </div>
    </>}
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="note">{notice}</p>}
  </section>;
}
