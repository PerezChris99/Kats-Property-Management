import {useCallback,useEffect,useState} from 'react'
import {api} from './lib/api'

const KINDS=['RENT','DEPOSIT','REPAIR','SERVICE','NOTICE','OTHER']
const ROLES=['OWNER','MANAGER','SUPER_ADMIN']
const showError=e=>e instanceof Error?e.message:'Request failed'

export default function DisputesPage({role}) {
  const reviewer=ROLES.includes(role)
  const [leases,setLeases]=useState([])
  const [cases,setCases]=useState([])
  const [events,setEvents]=useState([])
  const [selected,setSelected]=useState('')
  const [form,setForm]=useState({lease_id:'',kind:'RENT',title:'',description:''})
  const [comment,setComment]=useState('')
  const [decision,setDecision]=useState({status:'IN_REVIEW',reason:''})
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [message,setMessage]=useState('')
  const load=useCallback(async()=>{
    const [a,b]=await Promise.all([api('disputes?page_size=100'),api('disputes/eligible-leases?page_size=100')])
    setCases(a.items||[]);setLeases(b.items||[])
  },[])
  useEffect(()=>{load().catch(e=>setError(showError(e)))},[load])
  useEffect(()=>{
    if(!selected){setEvents([]);return}
    api('disputes/'+encodeURIComponent(selected)+'/events?page_size=100')
      .then(r=>setEvents(r.items||[])).catch(e=>setError(showError(e)))
  },[selected])
  async function perform(event,kind){
    event.preventDefault();setBusy(true);setError('');setMessage('')
    try{
      if(kind==='open'){
        const r=await api('disputes',{method:'POST',body:JSON.stringify(form)})
        setMessage('Dispute opened. This is an internal record, not a court filing or statutory notice.')
        setForm({lease_id:'',kind:'RENT',title:'',description:''})
        setSelected(r.dispute.id)
      }else{
        const url='disputes/'+encodeURIComponent(selected)+(kind==='comment'?'/comments':'/decision')
        await api(url,{method:'POST',body:JSON.stringify(
          kind==='comment'?{comment}:{status:decision.status,reason:decision.reason}
        )})
        setMessage(kind==='comment'?'Written case comment added.':'Internal decision recorded, without triggering any refund or legal action.')
        setComment('');setDecision({status:'IN_REVIEW',reason:''})
      }
      await load()
      if(selected||kind==='open'){
        const id=kind==='open'?null:selected
        if(id) {
          const r=await api('disputes/'+encodeURIComponent(id)+'/events?page_size=100')
          setEvents(r.items||[])
        }
      }
    }catch(e){setError(showError(e))}
    finally{setBusy(false)}
  }
  const item=cases.find(c=>c.id===selected)
  return <section className="page">
    <span className="eyebrow">TENANCY ACCOUNTABILITY</span>
    <h1>Rental disputes</h1>
    <p>Document rent, deposit, repairs, service and tenancy-notice concerns, with an auditable response history. Formal notice delivery and legal remedies remain separate.</p>
    {error&&<p role="alert">{error}</p>}
    {message&&<p role="status">{message}</p>}
    <form className="resource-form" onSubmit={e=>perform(e,'open')}>
      <h2>Open a case</h2>
      <div className="fields">
        <label>Lease
          <select required value={form.lease_id} onChange={e=>setForm({...form,lease_id:e.target.value})}>
            <option value="">Select tenancy</option>
            {leases.map(l=><option key={l.id} value={l.id}>{l.room_id} · {l.start_date} · {l.status}</option>)}
          </select>
        </label>
        <label>Category
          <select value={form.kind} onChange={e=>setForm({...form,kind:e.target.value})}>
            {KINDS.map(k=><option key={k}>{k}</option>)}
          </select>
        </label>
        <label>Case title
          <input required maxLength={160} value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/>
        </label>
      </div>
      <label>Written complaint
        <textarea required rows={4} maxLength={3000} value={form.description}
          onChange={e=>setForm({...form,description:e.target.value})}/>
      </label>
      <button className="button" disabled={busy}>{busy?'Recording…':'Open dispute'}</button>
    </form>
    <h2>Cases</h2>
    <label>View case
      <select value={selected} onChange={e=>setSelected(e.target.value)}>
        <option value="">Choose a case</option>
        {cases.map(c=><option key={c.id} value={c.id}>{c.status} · {c.kind} · {c.title}</option>)}
      </select>
    </label>
    {!cases.length&&<p>No rental disputes recorded.</p>}
    {item&&<article className="module-card">
      <h3>{item.title}</h3><p>{item.description}</p>
      <p><strong>Status:</strong> {item.status} · <strong>Created:</strong> {item.created_at}</p>
      <h3>Case history</h3>
      {!events.length?<p>Loading case history…</p>:
      <div className="module-list">{events.map(e=><div key={e.id}>
        <strong>{e.event} · {e.created_at}</strong>
        <p>{e.comment}</p>
        {e.previous_status&&<small>{e.previous_status} → {e.new_status}</small>}
      </div>)}</div>}
      {!['RESOLVED','DECLINED'].includes(item.status)&&
        <form className="resource-form" onSubmit={e=>perform(e,'comment')}>
          <h3>Add response</h3>
          <label>Comment<textarea rows={3} required maxLength={3000}
            value={comment} onChange={e=>setComment(e.target.value)}/></label>
          <button className="outline-button" disabled={busy}>{busy?'Saving…':'Add response'}</button>
        </form>}
      {reviewer&&<form className="resource-form" onSubmit={e=>perform(e,'decision')}>
        <h3>Landlord / manager decision</h3>
        <label>Status
          <select value={decision.status} onChange={e=>setDecision({...decision,status:e.target.value})}>
            <option value="IN_REVIEW">Under review</option>
            <option value="RESOLVED">Resolved</option>
            <option value="DECLINED">Declined</option>
            {['RESOLVED','DECLINED'].includes(item.status)&&<option value="OPEN">Reopen case</option>}
          </select>
        </label>
        <label>Documented reason
          <textarea required rows={3} maxLength={3000} value={decision.reason}
            onChange={e=>setDecision({...decision,reason:e.target.value})}/>
        </label>
        <button className="outline-button" disabled={busy}>{busy?'Saving…':'Record decision'}</button>
      </form>}
    </article>}
  </section>
}
