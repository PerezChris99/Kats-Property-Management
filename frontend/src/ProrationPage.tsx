import {useEffect,useState,type FormEvent} from 'react'
import {Link} from 'react-router-dom'
import {api} from './lib/api'

type Entry={id:string;room_id:string;status:string}
type Segment={from:string;to:string;days:number;monthly_rent_ugx:number;amount_ugx:number}
type Preview={month:string;period_start:string;period_end:string;policy:string;
  days_in_month:number;amount_ugx:number;segments:Segment[];contract_review_required:boolean}
const ugx=(number:number)=>'UGX '+number.toLocaleString('en-UG')
export function ProrationPage({role}:{role:string}) {
  const [leases,setLeases]=useState<Entry[]>([])
  const [lease,setLease]=useState('')
  const [month,setMonth]=useState('')
  const [due,setDue]=useState('')
  const [reason,setReason]=useState('')
  const [approved,setApproved]=useState(false)
  const [preview,setPreview]=useState<Preview|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const finance=['OWNER','ACCOUNTANT','SUPER_ADMIN'].includes(role)
  useEffect(()=>{api('leases').then(r=>setLeases((r.items||[]).filter((l:Entry)=>l.status==='ACTIVE')))
    .catch(e=>setError(e instanceof Error?e.message:'Unable to load leases'))},[])
  useEffect(()=>{setPreview(null);setApproved(false);setNotice('')},[lease,month])
  async function calculate(event:FormEvent) {
    event.preventDefault();setError('');setBusy(true)
    try {
      const r=await api('billing/proration/preview?lease_id='+encodeURIComponent(lease)+
                        '&month='+encodeURIComponent(month))
      setPreview(r.preview)
    } catch(e) {setError(e instanceof Error?e.message:'Unable to calculate')}
    finally {setBusy(false)}
  }
  async function issue() {
    if(!preview||!approved||!finance)return
    setError('');setBusy(true)
    try {
      const r=await api('billing/proration/issue',{method:'POST',body:JSON.stringify({
        lease_id:lease,month,due_date:due,reason,policy:preview.policy,confirm_policy:true
      })})
      setNotice('Invoice '+r.invoice.invoice_number+' issued for '+ugx(r.invoice.total_ugx)+
                '. The finance audit records the confirmed policy and reason.')
      setApproved(false)
    } catch(e) {setError(e instanceof Error?e.message:'Unable to issue invoice')}
    finally {setBusy(false)}
  }
  return <section className="page"><span className="eyebrow">RENT BILLING</span><h1>Proration and rate changes</h1>
    <p>Prorated rent is calculated from actual days in the calendar month and effective-dated rent changes. No invoice is issued until an authorized finance officer confirms the applicable lease terms.</p>
    {error&&<p className="error" role="alert">{error}</p>}
    {notice&&<p role="status" className="module-card">{notice} <Link to="/invoices">View invoices</Link></p>}
    <form className="resource-form" onSubmit={calculate}>
      <div className="fields">
        <label>Active lease<select required value={lease} onChange={e=>setLease(e.target.value)}>
          <option value="">Choose lease</option>{leases.map(l=><option key={l.id} value={l.id}>
            Room {l.room_id} · Lease {l.id}</option>)}
        </select></label>
        <label>Billing month<input required type="month" value={month} onChange={e=>setMonth(e.target.value)}/></label>
      </div><button className="button" disabled={busy}>{busy?'Calculating…':'Preview prorated rent'}</button>
    </form>
    {preview&&<div className="module-card">
      <h2>Reviewed calculation · {ugx(preview.amount_ugx)}</h2>
      <p>Period: {preview.period_start} to {preview.period_end} · {preview.days_in_month} days in month</p>
      <div className="data-table-wrap"><table><thead><tr><th>Rent period</th><th>Days</th><th>Monthly rent</th><th>Prorated amount</th></tr></thead>
      <tbody>{preview.segments.map((s,i)=><tr key={i}><td>{s.from} – {s.to}</td><td>{s.days}</td>
        <td>{ugx(s.monthly_rent_ugx)}</td><td>{ugx(s.amount_ugx)}</td></tr>)}</tbody></table></div>
      <p>Amounts are rounded per effective rent segment to the nearest UGX, half up. Confirm the formula is consistent with the signed lease before issuing.</p>
      {finance&&<div className="resource-form">
        <label>Payment due date<input type="date" required value={due} onChange={e=>setDue(e.target.value)}/></label>
        <label>Reason for policy approval<input required maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label>
        <label className="check-row"><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/>
          I verified that the lease permits calendar-day proration and approve this invoice.</label>
        <button className="button" disabled={busy||!approved||!reason.trim()||!due} onClick={issue}>
          {busy?'Issuing…':'Issue reviewed invoice'}</button>
      </div>}
    </div>}
  </section>
}
