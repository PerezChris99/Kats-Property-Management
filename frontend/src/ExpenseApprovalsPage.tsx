import {useCallback,useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from './lib/api'

type Expense={id:string;property_id:string;category:string;description:string;amount_ugx:number;
  incurred_on:string;status:string;created_by:string;reviewed_by?:string}
const money=(v:number)=>'UGX '+v.toLocaleString('en-UG')
export function ExpenseApprovalsPage({role}:{role:string}) {
  const [rows,setRows]=useState<Expense[]>([])
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [busy,setBusy]=useState('')
  const canReview=['OWNER','ACCOUNTANT','SUPER_ADMIN'].includes(role)
  const canReverse=['OWNER','SUPER_ADMIN'].includes(role)
  const load=useCallback(async()=>{
    try {const r=await api('expenses');setRows(r.items||[])}
    catch(e){setError(e instanceof Error?e.message:'Unable to load expenses')}
  },[])
  useEffect(()=>{void load()},[load])
  async function act(id:string,action:'APPROVE'|'REJECT'|'REVERSE') {
    const reason=window.prompt('Evidence and reason for '+action.toLowerCase()+' (required)')
    if(!reason?.trim())return
    setBusy(id);setError('');setNotice('')
    try {
      const path=action==='REVERSE'?'expenses/'+id+'/reverse':'expenses/'+id+'/review'
      const data=action==='REVERSE'?{reason}:{decision:action,reason}
      await api(path,{method:'POST',body:JSON.stringify(data)})
      await load()
      setNotice(action==='APPROVE'?'Expense approved for accounting. This is not proof of bank payment.':
        action==='REVERSE'?'Expense reversed in the immutable ledger; no cash was transferred.':
        'Unverified expense was rejected.')
    } catch(e){setError(e instanceof Error?e.message:'Unable to review')}
    finally {setBusy('')}
  }
  return <section className="page">
    <span className="eyebrow">MAKER / CHECKER</span><h1>Expense verification</h1>
    <p>Recorded supplier expenses are excluded from financial totals until another authorized staff member approves them. Reversals are audited, not deletions.</p>
    <Link className="button" to="/expenses">Record a new expense</Link>
    {error&&<p className="error" role="alert">{error}</p>}
    {notice&&<p role="status" className="module-card">{notice}</p>}
    <div className="module-list">{rows.map(row=><article key={row.id} className="module-card">
      <strong>{row.category} · {money(row.amount_ugx)}</strong>
      <p>{row.description}</p>
      <p>Incurred: {row.incurred_on} · Status: <strong>{row.status.replaceAll('_',' ')}</strong></p>
      {canReview&&['PENDING_APPROVAL','REVIEW_REQUIRED'].includes(row.status)&&
        <div className="actions">
          <button className="outline-button" disabled={busy!==''} onClick={()=>act(row.id,'APPROVE')}>
            {busy===row.id?'Processing…':'Verify & approve'}</button>
          <button className="outline-button" disabled={busy!==''} onClick={()=>act(row.id,'REJECT')}>Reject</button>
        </div>}
      {canReverse&&row.status==='APPROVED'&&<button className="outline-button" disabled={busy!==''}
        onClick={()=>act(row.id,'REVERSE')}>Reverse approved expense</button>}
    </article>)}
    {!rows.length&&<p>No expense records in this page.</p>}</div>
  </section>
}
