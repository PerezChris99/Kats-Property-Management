import {useCallback,useEffect,useState} from 'react'
import {api} from './lib/api'

const ERROR=e=>e instanceof Error?e.message:'Operation failed'
const manager=role=>['OWNER','MANAGER','SUPER_ADMIN'].includes(role)
const PRIORITIES=['LOW','MEDIUM','HIGH','URGENT']

export default function PreventiveMaintenancePage({role}) {
  const [rooms,setRooms]=useState([])
  const [plans,setPlans]=useState([])
  const [selected,setSelected]=useState('')
  const [occurrences,setOccurrences]=useState([])
  const [plan,setPlan]=useState({
    room_id:'',title:'',instructions:'',priority:'MEDIUM',
    cadence_days:'30',next_due_on:''
  })
  const [reason,setReason]=useState('')
  const [error,setError]=useState('')
  const [message,setMessage]=useState('')
  const [busy,setBusy]=useState(false)
  const load=useCallback(async()=>{
    const result=await api('maintenance/plans?page_size=100')
    setPlans(result.items||[])
  },[])
  useEffect(()=>{
    load().catch(e=>setError(ERROR(e)))
    if(manager(role)){
      api('rooms?page_size=100').then(r=>setRooms(r.items||[]))
        .catch(e=>setError(ERROR(e)))
    }
  },[load,role])
  useEffect(()=>{
    if(!selected){setOccurrences([]);return}
    api('maintenance/plans/'+encodeURIComponent(selected)+'/occurrences?page_size=100')
      .then(r=>setOccurrences(r.items||[])).catch(e=>setError(ERROR(e)))
  },[selected])
  const current=plans.find(x=>x.id===selected)
  async function create(e){
    e.preventDefault();setError('');setMessage('');setBusy(true)
    try{
      const result=await api('maintenance/plans',{method:'POST',body:JSON.stringify({
        ...plan,cadence_days:Number(plan.cadence_days)
      })})
      await load();setSelected(result.plan.id)
      setMessage('Preventive maintenance plan recorded. Celery will open one request at each due date.')
      setPlan({room_id:'',title:'',instructions:'',priority:'MEDIUM',cadence_days:'30',next_due_on:''})
    }catch(e){setError(ERROR(e))}finally{setBusy(false)}
  }
  async function transition(newStatus){
    if(!current || !reason.trim()) {setError('A written reason is required.');return}
    setError('');setMessage('');setBusy(true)
    try{
      await api('maintenance/plans/'+encodeURIComponent(current.id)+'/status',{
        method:'POST',body:JSON.stringify({status:newStatus,reason})
      })
      await load();setReason('')
      setMessage('Maintenance plan status recorded. Generated work orders remain auditable.')
    }catch(e){setError(ERROR(e))}finally{setBusy(false)}
  }
  return <section className="page">
    <span className="eyebrow">PREVENTIVE OPERATIONS</span>
    <h1>Recurring maintenance</h1>
    <p>Schedule inspections and routine work before faults occur. A due plan creates a maintenance request, never automatic contractor authorization or expenditure.</p>
    {error&&<p role="alert">{error}</p>}
    {message&&<p role="status">{message}</p>}
    {manager(role)&&<form className="resource-form" onSubmit={create}>
      <h2>Create maintenance plan</h2>
      <div className="fields">
        <label>Room
          <select required value={plan.room_id} onChange={e=>setPlan({...plan,room_id:e.target.value})}>
            <option value="">Select room</option>{rooms.filter(x=>x.status!=='ARCHIVED').map(x=><option key={x.id} value={x.id}>{x.number} · {x.status}</option>)}
          </select>
        </label>
        <label>Title
          <input required maxLength={120} value={plan.title} onChange={e=>setPlan({...plan,title:e.target.value})}/>
        </label>
        <label>Priority
          <select value={plan.priority} onChange={e=>setPlan({...plan,priority:e.target.value})}>
            {PRIORITIES.map(x=><option key={x}>{x}</option>)}
          </select>
        </label>
        <label>Repeat every (days)
          <input type="number" required min="1" max="366" value={plan.cadence_days}
            onChange={e=>setPlan({...plan,cadence_days:e.target.value})}/>
        </label>
        <label>First due date
          <input type="date" required value={plan.next_due_on}
            onChange={e=>setPlan({...plan,next_due_on:e.target.value})}/>
        </label>
      </div>
      <label>Instructions
        <textarea required rows={4} maxLength={2500} value={plan.instructions}
          onChange={e=>setPlan({...plan,instructions:e.target.value})}/>
      </label>
      <button className="button" disabled={busy}>{busy?'Saving…':'Create maintenance plan'}</button>
    </form>}
    <h2>Scheduled work</h2>
    <label>Plan
      <select value={selected} onChange={e=>setSelected(e.target.value)}>
        <option value="">Select plan</option>{plans.map(x=><option key={x.id} value={x.id}>{x.status} · {x.next_due_on} · {x.title}</option>)}
      </select>
    </label>
    {!plans.length&&<p>No preventive maintenance plans yet.</p>}
    {current&&<article className="module-card">
      <h3>{current.title}</h3>
      <p>{current.instructions}</p>
      <p>Status: <strong>{current.status}</strong> · Due: {current.next_due_on} · Every {current.cadence_days} day(s) · Priority {current.priority}</p>
      {manager(role)&&current.status!=='RETIRED'&&<div className="resource-form">
        <label>Reason for changing plan state
          <textarea rows={2} maxLength={500} value={reason}
            onChange={e=>setReason(e.target.value)}/>
        </label>
        <div className="actions">
          {current.status!=='PAUSED'&&<button type="button" className="outline-button" disabled={busy} onClick={()=>transition('PAUSED')}>Pause</button>}
          {current.status==='PAUSED'&&<button type="button" className="outline-button" disabled={busy} onClick={()=>transition('ACTIVE')}>Resume</button>}
          <button type="button" className="outline-button" disabled={busy} onClick={()=>transition('RETIRED')}>Retire plan</button>
        </div>
      </div>}
      <h3>Generated maintenance requests</h3>
      {occurrences.length===0?<p>None generated yet.</p>:
      <div className="module-list">{occurrences.map(o=><p key={o.id}>{o.scheduled_for} · Request {o.maintenance_request_id}</p>)}</div>}
    </article>}
  </section>
}
