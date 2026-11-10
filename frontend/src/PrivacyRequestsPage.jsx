import {useCallback,useEffect,useState} from 'react'
import {api} from './lib/api'

const KINDS=[
  {value:'ACCESS',label:'Access my personal data'},
  {value:'RECTIFY',label:'Correct personal data'},
  {value:'ERASURE',label:'Request deletion / erasure review'},
  {value:'RESTRICT',label:'Restrict processing'},
  {value:'OBJECT',label:'Object to processing'}
]
const formatError=e => e instanceof Error?e.message:'Request failed'

export default function PrivacyRequestsPage({role}) {
  const reviewer=['OWNER','SUPER_ADMIN'].includes(role)
  const [summary,setSummary]=useState(null)
  const [records,setRecords]=useState([])
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [kind,setKind]=useState('ACCESS')
  const [details,setDetails]=useState('')
  const [busy,setBusy]=useState(false)
  const [decision,setDecision]=useState({})
  const load=useCallback(async () => {
    const [personal,cases]=await Promise.all([
      api('privacy/my-data'),api('privacy/requests?page_size=100')
    ])
    setSummary(personal);setRecords(cases.items||[])
  },[])
  useEffect(() => {load().catch(e=>setError(formatError(e)))},[load])
  async function submit(event){
    event.preventDefault();setError('');setNotice('');setBusy(true)
    try{
      await api('privacy/requests',{method:'POST',body:JSON.stringify({kind,details})})
      setDetails('')
      setNotice('Request submitted for review. The business must assess applicable rights, statutory retention and identity verification.')
      await load()
    }catch(e){setError(formatError(e))}
    finally{setBusy(false)}
  }
  async function review(event,row){
    event.preventDefault();setBusy(true);setError('');setNotice('')
    try{
      const input=decision[row.id]||{}
      const result=await api('privacy/requests/'+encodeURIComponent(row.id)+'/review',{
        method:'POST',
        body:JSON.stringify({
          status:input.status||'IN_REVIEW',
          decision_notes:input.decision_notes||'',
          retention_exceptions_reviewed:Boolean(input.retention_exceptions_reviewed)
        })
      })
      setNotice('Request '+result.request.id+' updated. This records a review decision; it does not automatically export, alter or delete personal data.')
      await load()
    }catch(e){setError(formatError(e))}
    finally{setBusy(false)}
  }
  const update=(id,key,value)=>setDecision(current=>({
    ...current,[id]:{...current[id],[key]:value}
  }))
  return <section className="page">
    <span className="eyebrow">UGANDA DATA PROTECTION</span>
    <h1>Privacy and personal data requests</h1>
    <p>Request access, corrections, restrictions, objections or a deletion review. Existing legal, rental and financial retention duties may apply.</p>
    {error&&<p role="alert">{error}</p>}
    {notice&&<p role="status">{notice}</p>}
    <div className="module-card">
      <h2>Personal data summary</h2>
      {summary?<>
        <p><strong>Account:</strong> {summary.account?.full_name} · {summary.account?.email}</p>
        {summary.tenant&&<p><strong>Rental profile:</strong> {summary.tenant.full_name} · {summary.tenant.phone}</p>}
        {summary.outstanding_ugx!==undefined&&<p><strong>Recorded open invoice balance:</strong> UGX {Number(summary.outstanding_ugx).toLocaleString('en-UG')}</p>}
        <p>{summary.notice}</p>
      </>:<p>Loading account summary…</p>}
    </div>
    <form className="resource-form" onSubmit={submit}>
      <h2>Submit a data request</h2>
      <label>Request type
        <select value={kind} onChange={e=>setKind(e.target.value)}>{KINDS.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select>
      </label>
      <label>What should be reviewed?
        <textarea value={details} rows={4} maxLength={2000} minLength={1} required
          onChange={e=>setDetails(e.target.value)} placeholder="Describe the information and your requested outcome without including passwords or identity-document numbers."/>
      </label>
      <button className="button" disabled={busy}>{busy?'Submitting…':'Submit request'}</button>
    </form>
    <h2>{reviewer?'Data request review queue':'My requests'}</h2>
    {records.length===0?<p>No requests recorded.</p>:
    <div className="module-list">{records.map(row=><article className="module-card" key={row.id}>
      <h3>{KINDS.find(x=>x.value===row.kind)?.label||row.kind}</h3>
      <p><strong>Status:</strong> {row.status} · <strong>Created:</strong> {row.created_at}</p>
      {reviewer&&<p><strong>Requesting account ID:</strong> {row.requester_user_id}</p>}
      <p>{row.details}</p>
      {row.decision_notes&&<p><strong>Review:</strong> {row.decision_notes}</p>}
      {reviewer&&!['COMPLETED','DECLINED'].includes(row.status)&&
        <form className="resource-form" onSubmit={e=>review(e,row)}>
          <label>Decision
            <select value={decision[row.id]?.status||'IN_REVIEW'}
              onChange={e=>update(row.id,'status',e.target.value)}>
              <option value="IN_REVIEW">In review</option><option value="COMPLETED">Completed</option><option value="DECLINED">Declined</option>
            </select>
          </label>
          <label>Decision and supporting reference
            <textarea required rows={3} maxLength={2000} value={decision[row.id]?.decision_notes||''}
              onChange={e=>update(row.id,'decision_notes',e.target.value)}/>
          </label>
          {row.kind==='ERASURE'&&
            <label className="check-row">
              <input type="checkbox" checked={Boolean(decision[row.id]?.retention_exceptions_reviewed)}
                onChange={e=>update(row.id,'retention_exceptions_reviewed',e.target.checked)}/>
              I have reviewed tax, financial, tenancy and audit retention exceptions before claiming erasure is complete.
            </label>}
          <button className="outline-button" disabled={busy}>Record review decision</button>
        </form>}
    </article>)}</div>}
  </section>
}
