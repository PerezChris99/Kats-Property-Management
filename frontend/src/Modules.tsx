import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from './lib/api'

type Item=Record<string,unknown>
type Identity={id:string;full_name:string;role:string}
const err=(e:unknown)=>e instanceof Error?e.message:'An unexpected error occurred'
const txt=(v:unknown)=>String(v??'—')
const money=(v:unknown)=>'UGX '+Number(v||0).toLocaleString('en-UG')
function Notice({error}:{error:string}) {return error?<p role="alert" className="error">{error}</p>:null}
function Empty({children}:{children:string}) {return <p className="empty">{children}</p>}
async function getRows(path:string) {const res=await api(path);return (res.items||[]) as Item[]}

export function NotificationsPage() {
  const [rows,setRows]=useState<Item[]>([]);const [error,setError]=useState('')
  const load=useCallback(()=>getRows('notifications').then(setRows).catch(e=>setError(err(e))),[])
  useEffect(()=>{void load()},[load])
  async function read(id:string) {
    try{await api('notifications/'+id+'/read',{method:'POST'});await load()}
    catch(e){setError(err(e))}
  }
  return <section className="page"><span className="eyebrow">IN-APP UPDATES</span><h1>Notifications</h1><Notice error={error}/>
    {!rows.length?<Empty>No notifications yet.</Empty>:<div className="module-list">{rows.map(row=><article key={txt(row.id)} className="module-card"><h2>{txt(row.title)}</h2><p>{txt(row.body)}</p><small>{txt(row.created_at)}</small>
      {!row.read_at&&<button className="outline-button" onClick={()=>read(txt(row.id))}>Mark as read</button>}
    </article>)}</div>}</section>
}

export function InspectionsPage({user}:{user:Identity}) {
  const [rows,setRows]=useState<Item[]>([]),[leases,setLeases]=useState<Item[]>([])
  const [values,setValues]=useState({lease_id:'',kind:'MOVE_IN',observed_on:'',condition_notes:'',damage_estimate_ugx:'0'})
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false)
  const load=useCallback(()=>getRows('inspections').then(setRows).catch(e=>setError(err(e))),[])
  useEffect(()=>{void load();if(user.role!=='TENANT')getRows(user.role==='CARETAKER'?'caretaker/leases':'leases').then(setLeases).catch(()=>{})},[load,user.role])
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');setNotice('')
    try{await api('inspections',{method:'POST',body:JSON.stringify({...values,damage_estimate_ugx:Number(values.damage_estimate_ugx)})});setNotice('Inspection recorded');await load()}
    catch(e){setError(err(e))}finally{setBusy(false)}
  }
  return <section className="page"><span className="eyebrow">PROPERTY LIFECYCLE</span><h1>Inspections</h1><p>Move-out inspections must be recorded before closing a lease. Photos require configured private storage.</p><Notice error={error}/>{notice&&<p role="status">{notice}</p>}
    {user.role!=='TENANT'&&<form className="resource-form" onSubmit={submit}><h2>Record inspection</h2><div className="fields"><label>Lease<select required value={values.lease_id} onChange={e=>setValues({...values,lease_id:e.target.value})}><option value="">Choose lease</option>{leases.map(l=><option key={txt(l.id)} value={txt(l.id)}>{txt(l.room_id)} · {txt(l.tenant_id)}</option>)}</select></label>
      <label>Inspection type<select value={values.kind} onChange={e=>setValues({...values,kind:e.target.value})}><option>MOVE_IN</option><option>MOVE_OUT</option><option>ROUTINE</option></select></label>
      <label>Observed on<input required type="date" value={values.observed_on} onChange={e=>setValues({...values,observed_on:e.target.value})}/></label>
      <label>Estimated damages (UGX)<input type="number" min="0" value={values.damage_estimate_ugx} onChange={e=>setValues({...values,damage_estimate_ugx:e.target.value})}/></label></div>
      <label>Condition / checklist<textarea required rows={4} value={values.condition_notes} onChange={e=>setValues({...values,condition_notes:e.target.value})}/></label><button className="button" disabled={busy}>{busy?'Saving…':'Record inspection'}</button></form>}
    <h2>History</h2>{!rows.length?<Empty>No inspections recorded.</Empty>:<div className="module-list">{rows.map(i=><article className="module-card" key={txt(i.id)}><strong>{txt(i.kind)} · {txt(i.observed_on)}</strong><p>{txt(i.condition_notes)}</p><small>Damage estimate: {money(i.damage_estimate_ugx)}</small></article>)}</div>}</section>
}

export function MobileMoneyPage() {
  const [invoices,setInvoices]=useState<Item[]>([]),[payment,setPayment]=useState<Item|null>(null)
  const [reference,setReference]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
  const [form,setForm]=useState({invoice_id:'',amount_ugx:'',msisdn:'',provider:'MTN_MOMO'})
  const [command,setCommand]=useState(()=>crypto.randomUUID())
  useEffect(()=>{getRows('invoices').then(setInvoices).catch(e=>setError(err(e)))},[])
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');setMessage('')
    try{const res=await api('payments/mobile/initiate',{method:'POST',body:JSON.stringify({...form,amount_ugx:Number(form.amount_ugx),idempotency_key:command})})
      setPayment(res.payment);setReference(txt(res.provider_reference));setMessage(txt(res.notice)||'Pending provider response')}
    catch(e){setError(err(e))}finally{setBusy(false)}
  }
  async function verify(){if(!payment)return;setBusy(true);setError('')
    try{const res=await api('payments/mobile/'+payment.id+'/verify',{method:'POST'})
      setMessage('Verification: '+txt(res.result.state)+'. '+(res.result.credited?'Invoice credited.':'No funds applied to invoice.'))
      const update=await api('payments/mobile/'+payment.id);setPayment(update.payment)
    }catch(e){setError(err(e))}finally{setBusy(false)}
  }
  return <section className="page"><span className="eyebrow">RENT COLLECTION</span><h1>Mobile money</h1><p>MTN MoMo and Airtel Money are enabled only after provider onboarding. A payment prompt is never proof of settlement.</p><Notice error={error}/>{message&&<p role="status" className="module-card">{message}</p>}
  <form className="resource-form" onSubmit={submit}><h2>Request payment</h2><div className="fields">
  <label>Invoice<select required value={form.invoice_id} onChange={e=>setForm({...form,invoice_id:e.target.value})}><option value="">Select invoice</option>{invoices.filter(i=>!['PAID','VOID','CREDITED'].includes(txt(i.status))).map(i=><option key={txt(i.id)} value={txt(i.id)}>{txt(i.invoice_number)} · {money(Number(i.total_ugx)-Number(i.paid_ugx)-Number(i.credit_ugx||0))} outstanding</option>)}</select></label>
  <label>Network<select value={form.provider} onChange={e=>setForm({...form,provider:e.target.value})}><option value="MTN_MOMO">MTN MoMo</option><option value="AIRTEL_MONEY">Airtel Money</option></select></label>
  <label>Amount UGX<input required type="number" min="1" value={form.amount_ugx} onChange={e=>setForm({...form,amount_ugx:e.target.value})}/></label>
  <label>Phone (256...)<input required inputMode="tel" pattern="256[37][0-9]{8}" value={form.msisdn} onChange={e=>setForm({...form,msisdn:e.target.value})}/></label></div>
  <button className="button" disabled={busy}>{busy?'Contacting provider…':'Send payment prompt'}</button>
  </form>{payment&&<div className="module-card"><h2>Transaction status</h2><p>State: <strong>{txt(payment.status)}</strong></p><p>Provider reference: {reference||'—'}</p>
   <button className="button" disabled={busy} onClick={verify}>{busy?'Checking…':'Verify with provider'}</button>
   <button className="outline-button" onClick={()=>{setPayment(null);setCommand(crypto.randomUUID());setMessage('')}}>New payment request</button></div>}</section>
}

export function FiscalPage() {
  const [rows,setRows]=useState<Item[]>([]),[invoices,setInvoices]=useState<Item[]>([])
  const [invoiceId,setInvoiceId]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('')
  const load=useCallback(()=>getRows('efris').then(setRows).catch(e=>setError(err(e))),[])
  useEffect(()=>{void load();getRows('invoices').then(setInvoices).catch(()=>{})},[load])
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('')
    try{const result=await api('efris/queue',{method:'POST',body:JSON.stringify({invoice_id:invoiceId})});setNotice(txt(result.notice||'Submission already queued'));await load()}
    catch(e){setError(err(e))}finally{setBusy(false)}
  }
  return <section className="page"><span className="eyebrow">UGANDA REVENUE AUTHORITY</span><h1>EFRIS fiscalization</h1><p>Submission records are not fiscal documents until URA accepts them and assigns a fiscal document number.</p>
    <Notice error={error}/>{notice&&<p role="status">{notice}</p>}
    <form className="resource-form" onSubmit={submit}><h2>Queue eligible invoice</h2><label>Invoice<select required value={invoiceId} onChange={e=>setInvoiceId(e.target.value)}><option value="">Select invoice</option>{invoices.filter(i=>i.status!=='VOID').map(i=><option value={txt(i.id)} key={txt(i.id)}>{txt(i.invoice_number)}</option>)}</select></label><button className="button" disabled={busy}>{busy?'Queueing…':'Queue fiscalization'}</button></form>
    <h2>Submission history</h2>{!rows.length?<Empty>No fiscalization records.</Empty>:<div className="module-list">{rows.map(row=><article className="module-card" key={txt(row.id)}><h3>{txt(row.document_type)} · {txt(row.state)}</h3><p>Invoice: {txt(row.invoice_id)}</p><small>URA fiscal document: {txt(row.fiscal_document_number)}</small></article>)}</div>}
  </section>
}

export function LegalAdminPage() {
  const [rows,setRows]=useState<Item[]>([]),[error,setError]=useState(''),[message,setMessage]=useState('')
  const [busy,setBusy]=useState(false)
  const [values,setValues]=useState({slug:'privacy',title:'Privacy Policy',content:''})
  const load=useCallback(()=>getRows('admin/legal-pages').then(setRows).catch(e=>setError(err(e))),[])
  useEffect(()=>{void load()},[load])
  async function create(e:FormEvent){e.preventDefault();setBusy(true);setError('')
    try{await api('admin/legal-pages',{method:'POST',body:JSON.stringify(values)});setMessage('Version saved as draft. Publish after legal review.');await load()}
    catch(e){setError(err(e))}finally{setBusy(false)}
  }
  async function publish(id:string){if(!window.confirm('Publish this reviewed legal version publicly?'))return
    try{await api('admin/legal-pages/'+id+'/publish',{method:'POST'});await load()}
    catch(e){setError(err(e))}
  }
  return <section className="page"><span className="eyebrow">CONTENT GOVERNANCE</span><h1>Legal pages</h1><p>Drafts are private until explicitly published. All legal copy requires client and legal approval.</p><Notice error={error}/>{message&&<p role="status">{message}</p>}
    <form className="resource-form" onSubmit={create}><h2>Create legal version</h2><div className="fields">
      <label>Page<select value={values.slug} onChange={e=>setValues({...values,slug:e.target.value})}><option value="privacy">Privacy</option><option value="terms">Terms</option><option value="cookies">Cookies</option><option value="refund">Refunds</option></select></label>
      <label>Title<input required value={values.title} onChange={e=>setValues({...values,title:e.target.value})}/></label></div>
      <label>Full reviewed policy<textarea rows={12} required minLength={20} value={values.content} onChange={e=>setValues({...values,content:e.target.value})}/></label>
      <button className="button" disabled={busy}>{busy?'Saving…':'Save new draft'}</button></form>
    <h2>Versions</h2>{!rows.length?<Empty>No legal drafts yet.</Empty>:<div className="module-list">{rows.map(p=><article key={txt(p.id)} className="module-card"><strong>{txt(p.slug)} · v{txt(p.version)}</strong><p>{txt(p.title)} · {p.published?'Published':'Draft'}</p>{!p.published&&<button className="outline-button" onClick={()=>publish(txt(p.id))}>Publish reviewed version</button>}</article>)}</div>}
  </section>
}

export function PublicLegalPage({slug}:{slug:string}) {
  const [page,setPage]=useState<Item|null>(null),[error,setError]=useState('')
  useEffect(()=>{setPage(null);api('public/legal/'+slug).then(x=>setPage(x.page)).catch(()=>setError('The legal page has not been published yet.'))},[slug])
  return <main className="section simple"><Link to="/">Back to Kats</Link><h1>{txt(page?.title||slug.toUpperCase())}</h1>{error?<p role="status">{error}</p>:!page?<p>Loading policy…</p>:<article className="legal-copy">{txt(page.content)}</article>}</main>
}

export function DocumentsPage() {
  const [rows,setRows]=useState<Item[]>([]),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
  const [file,setFile]=useState<File|null>(null),[category,setCategory]=useState('LEASE'),[lease,setLease]=useState(''),[leases,setLeases]=useState<Item[]>([])
  const load=useCallback(()=>getRows('documents').then(setRows).catch(e=>setError(err(e))),[])
  useEffect(()=>{void load();getRows('leases').then(setLeases).catch(()=>{})},[load])
  async function upload(e:FormEvent){e.preventDefault();if(!file)return;setBusy(true);setError('');setMessage('')
    try{const p=await api('documents/presign',{method:'POST',body:JSON.stringify({
      filename:file.name,mime_type:file.type,size_bytes:file.size,category,lease_id:lease||undefined
    })})
      const fields=new FormData()
      Object.entries(p.upload.fields as Record<string,string>).forEach(([key,val])=>fields.append(key,val))
      fields.append('file',file)
      const response=await fetch(p.upload.url,{method:'POST',body:fields,credentials:'omit'})
      if(!response.ok)throw new Error('Object storage rejected the upload')
      await api('documents/'+p.document.id+'/complete',{method:'POST'})
      setMessage('Document uploaded and verified privately');setFile(null);await load()
    }catch(e){setError(err(e))}finally{setBusy(false)}
  }
  async function download(id:string){try{const r=await api('documents/'+id+'/download');window.open(r.url,'_blank','noopener,noreferrer')}
    catch(e){setError(err(e))}
  }
  return <section className="page"><span className="eyebrow">PRIVATE STORAGE</span><h1>Documents</h1><p>PDF/JPG/PNG/WebP, maximum 8 MB. Signed uploads and downloads require configured private object storage.</p><Notice error={error}/>{message&&<p role="status">{message}</p>}
    <form className="resource-form" onSubmit={upload}><h2>Upload secure document</h2><div className="fields">
      <label>Category<select value={category} onChange={e=>setCategory(e.target.value)}><option>LEASE</option><option>ID</option><option>RECEIPT</option><option>INSPECTION</option><option>PAYMENT_PROOF</option><option>ROOM_PHOTO</option></select></label>
      <label>Lease (when applicable)<select value={lease} onChange={e=>setLease(e.target.value)}><option value="">Not linked</option>{leases.map(l=><option value={txt(l.id)} key={txt(l.id)}>{txt(l.room_id)}</option>)}</select></label>
      <label>Choose file<input required type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
      </div><button className="button" disabled={busy||!file}>{busy?'Uploading…':'Upload privately'}</button></form>
    <h2>Saved documents</h2>{!rows.length?<Empty>No private files available.</Empty>:<div className="module-list">{rows.map(r=><article className="module-card" key={txt(r.id)}><strong>{txt(r.filename)}</strong><p>{txt(r.category)} · {txt(r.status)}</p>{r.status==='UPLOADED'&&<button className="outline-button" onClick={()=>download(txt(r.id))}>Open securely</button>}</article>)}</div>}
  </section>
}

export function SecurityPage({onSignedOut}:{onSignedOut:()=>void}) {
  const [values,setValues]=useState({current_password:'',new_password:'',confirm:''})
  const [error,setError]=useState(''),[busy,setBusy]=useState(false)
  async function change(e:FormEvent){e.preventDefault();setError('')
    if(values.new_password!==values.confirm){setError('New passwords do not match');return}
    setBusy(true)
    try{await api('auth/change-password',{method:'POST',body:JSON.stringify({
      current_password:values.current_password,new_password:values.new_password
    })});onSignedOut()}
    catch(e){setError(err(e))}finally{setBusy(false)}
  }
  return <section className="page"><h1>Account security</h1><p>Changing your password signs out every active session, including other devices.</p><Notice error={error}/>
    <form className="resource-form" onSubmit={change}><label>Current password<input type="password" autoComplete="current-password" required value={values.current_password} onChange={e=>setValues({...values,current_password:e.target.value})}/></label>
      <label>New password<input type="password" autoComplete="new-password" required minLength={12} value={values.new_password} onChange={e=>setValues({...values,new_password:e.target.value})}/></label>
      <label>Confirm new password<input type="password" autoComplete="new-password" required minLength={12} value={values.confirm} onChange={e=>setValues({...values,confirm:e.target.value})}/></label>
      <button className="button" disabled={busy}>{busy?'Updating…':'Update password and sign out'}</button></form></section>
}

export function AuditPage() {
  const [rows,setRows]=useState<Item[]>([]),[error,setError]=useState('')
  useEffect(()=>{getRows('audit').then(setRows).catch(e=>setError(err(e)))},[])
  return <section className="page"><span className="eyebrow">ACCOUNTABILITY</span><h1>Audit history</h1><Notice error={error}/>{!rows.length?<Empty>No audit events in the first page.</Empty>:<div className="module-list">{rows.map(r=><article key={txt(r.id)} className="module-card"><strong>{txt(r.action)}</strong><p>{txt(r.target_type)} · {txt(r.target_id)}</p><small>{txt(r.created_at)}</small></article>)}</div>}</section>
}


export function RenewalsPage() {
  const [leases,setLeases]=useState<Item[]>([]),[history,setHistory]=useState<Item[]>([])
  const [selected,setSelected]=useState(''),[date,setDate]=useState(''),[amount,setAmount]=useState(''),[reason,setReason]=useState('')
  const [error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
  const load=useCallback(()=>getRows('leases').then(setLeases).catch(e=>setError(err(e))),[])
  useEffect(()=>{void load()},[load])
  useEffect(()=>{if(selected)getRows('leases/'+selected+'/amendments').then(setHistory).catch(e=>setError(err(e)))},[selected])
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('')
    try{const fields:Record<string,unknown>={new_end_date:date,reason}
      if(amount)fields.new_rent_ugx=Number(amount)
      const res=await api('leases/'+selected+'/renew',{method:'POST',body:JSON.stringify(fields)})
      setMessage('Lease renewed until '+txt(res.lease.end_date)+'. New terms take effect on '+txt(res.amendment.effective_date)+'.')
      await load();setHistory(await getRows('leases/'+selected+'/amendments'))
    }catch(e){setError(err(e))}finally{setBusy(false)}
  }
  return <section className="page"><span className="eyebrow">LEASE HISTORY</span><h1>Renewals and amendments</h1><p>Future rent changes are effective-dated. Previous invoices and historical rent are preserved.</p><Notice error={error}/>{message&&<p role="status">{message}</p>}
    <form className="resource-form" onSubmit={submit}><h2>Renew an active lease</h2><div className="fields">
      <label>Lease<select required value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select active lease</option>{leases.filter(l=>l.status==='ACTIVE').map(l=><option value={txt(l.id)} key={txt(l.id)}>{txt(l.room_id)} · through {txt(l.end_date)}</option>)}</select></label>
      <label>New end date<input required type="date" value={date} onChange={e=>setDate(e.target.value)}/></label>
      <label>New rent (UGX, optional)<input type="number" min="1" value={amount} onChange={e=>setAmount(e.target.value)}/></label>
      <label>Reason<input required value={reason} onChange={e=>setReason(e.target.value)}/></label>
    </div><button className="button" disabled={busy}>{busy?'Renewing…':'Record renewal'}</button></form>
    <h2>Rent history</h2>{history.length===0?<Empty>Select a lease to view previous amendments.</Empty>:<div className="module-list">{history.map(h=><article className="module-card" key={txt(h.id)}><strong>{txt(h.effective_date)} · {money(h.new_rent_ugx)}</strong><p>Through {txt(h.new_end_date)}. {txt(h.reason)}</p></article>)}</div>}
  </section>
}

export function DepositsPage({user}:{user:Identity}) {
  const [rows,setRows]=useState<Item[]>([]),[leases,setLeases]=useState<Item[]>([]),[selected,setSelected]=useState('')
  const [balance,setBalance]=useState<Item|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false)
  const [key,setKey]=useState(()=>crypto.randomUUID())
  const [form,setForm]=useState({kind:'HOLD',amount_ugx:'',reason:'',external_reference:''})
  const isStaff=user.role!=='TENANT' && user.role!=='CARETAKER'
  const canReview=['OWNER','ACCOUNTANT','SUPER_ADMIN'].includes(user.role)
  const load=useCallback(async()=>{
    try{
      if(isStaff){setRows(await getRows('deposits'));setLeases(await getRows('leases'))}
      else {const r=await api('tenant/lease');if(r.lease)setLeases([r.lease])}
    }catch(e){setError(err(e))}
  },[isStaff])
  useEffect(()=>{void load()},[load])
  useEffect(()=>{if(selected)api('deposits/leases/'+selected).then(r=>setBalance(r.balance)).catch(e=>setError(err(e)))},[selected])
  async function create(e:FormEvent){e.preventDefault();setBusy(true);setError('')
    try{await api('deposits/movements',{method:'POST',body:JSON.stringify({
      lease_id:selected,...form,amount_ugx:Number(form.amount_ugx),idempotency_key:key})})
      setNotice('Deposit movement recorded for separate verification. No cash transfer was performed.')
      setKey(crypto.randomUUID());await load()
      const b=await api('deposits/leases/'+selected);setBalance(b.balance)
    }catch(e){setError(err(e))}finally{setBusy(false)}
  }
  async function review(id:string,decision:string){const reason=window.prompt('Evidence/review reason');if(!reason?.trim())return;setError('')
    try{await api('deposits/movements/'+id+'/review',{method:'POST',body:JSON.stringify({decision,reason})});await load();if(selected){const b=await api('deposits/leases/'+selected);setBalance(b.balance)}}
    catch(e){setError(err(e))}
  }
  return <section className="page"><span className="eyebrow">SECURITY DEPOSITS</span><h1>Deposit accounting</h1><p>Held, withheld and refunded movements require separate staff approval and verified real-world evidence. Recording a refund does not send money.</p>
    <Notice error={error}/>{notice&&<p role="status">{notice}</p>}
    <label style={{maxWidth:500}}>Lease<select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select lease</option>{leases.map(l=><option key={txt(l.id)} value={txt(l.id)}>{txt(l.room_id)} · {txt(l.id)}</option>)}</select></label>
    {balance&&<div className="stat-grid">{Object.entries(balance).map(([label,value])=><div className="stat" key={label}><small>{label.replaceAll('_',' ')}</small><strong>{money(value)}</strong></div>)}</div>}
    {isStaff&&<form className="resource-form" onSubmit={create}><h2>Record movement for review</h2><div className="fields">
      <label>Movement<select value={form.kind} onChange={e=>setForm({...form,kind:e.target.value})}><option>HOLD</option><option>REFUND</option><option>WITHHOLD</option></select></label>
      <label>Amount UGX<input required type="number" min="1" value={form.amount_ugx} onChange={e=>setForm({...form,amount_ugx:e.target.value})}/></label>
      <label>External receipt or transfer reference<input value={form.external_reference} onChange={e=>setForm({...form,external_reference:e.target.value})}/></label>
      <label>Reason<input required value={form.reason} onChange={e=>setForm({...form,reason:e.target.value})}/></label>
    </div><button className="button" disabled={busy||!selected}>{busy?'Recording…':'Submit for separate approval'}</button></form>}
    <h2>Deposit movements</h2>{!rows.length?<Empty>No deposit movements in this account.</Empty>:<div className="module-list">{rows.map(d=><article className="module-card" key={txt(d.id)}><strong>{txt(d.kind)} · {money(d.amount_ugx)}</strong><p>{txt(d.status)} · {txt(d.lease_id)}</p>{canReview&&d.status==='PENDING_REVIEW'&&<div className="actions"><button className="outline-button" onClick={()=>review(txt(d.id),'APPROVE')}>Verify & approve</button><button className="outline-button" onClick={()=>review(txt(d.id),'REJECT')}>Reject</button></div>}</article>)}</div>}
  </section>
}

export function WorkOrdersPage({user}:{user:Identity}) {
  const [maintenance,setMaintenance]=useState<Item[]>([]),[selected,setSelected]=useState(''),[orders,setOrders]=useState<Item[]>([])
  const [scope,setScope]=useState(''),[cost,setCost]=useState('0'),[error,setError]=useState(''),[notice,setNotice]=useState('')
  const [busy,setBusy]=useState(false)
  useEffect(()=>{getRows(user.role==='CARETAKER'?'caretaker/maintenance':'maintenance').then(setMaintenance).catch(e=>setError(err(e)))},[user.role])
  const load=useCallback(()=>selected?getRows('maintenance/'+selected+'/work-orders').then(setOrders).catch(e=>setError(err(e))):Promise.resolve(),[selected])
  useEffect(()=>{void load()},[load])
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('')
    try{await api('maintenance/'+selected+'/work-orders',{method:'POST',body:JSON.stringify({scope,estimated_cost_ugx:Number(cost)})});setNotice('Work order created');await load()}
    catch(e){setError(err(e))}finally{setBusy(false)}
  }
  async function change(id:string,status:string){setBusy(true);setError('')
    try{await api('work-orders/'+id+'/status',{method:'POST',body:JSON.stringify({status})});await load()}
    catch(e){setError(err(e))}finally{setBusy(false)}
  }
  return <section className="page"><h1>Maintenance work orders</h1><Notice error={error}/>{notice&&<p role="status">{notice}</p>}
    <label>Select request<select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select maintenance request</option>{maintenance.map(m=><option key={txt(m.id)} value={txt(m.id)}>{txt(m.title)} · {txt(m.room_id)}</option>)}</select></label>
    {user.role!=='CARETAKER'&&<form className="resource-form" onSubmit={submit}><h2>New work order</h2><label>Work scope<textarea rows={3} required value={scope} onChange={e=>setScope(e.target.value)}/></label><label>Estimated cost UGX<input type="number" min="0" value={cost} onChange={e=>setCost(e.target.value)}/></label><button className="button" disabled={busy||!selected}>Assign work</button></form>}
    <h2>Work order history</h2>{!orders.length?<Empty>No work orders for this request.</Empty>:<div className="module-list">{orders.map(o=><article className="module-card" key={txt(o.id)}><h3>{txt(o.status)}</h3><p>{txt(o.scope)}</p><p>Estimate: {money(o.estimated_cost_ugx)} · Actual: {money(o.actual_cost_ugx)}</p>{user.role!=='CARETAKER'&&o.status!=='COMPLETED'&&<div className="actions"><button className="outline-button" onClick={()=>change(txt(o.id),'IN_PROGRESS')}>In progress</button><button className="outline-button" onClick={()=>change(txt(o.id),'COMPLETED')}>Complete</button></div>}</article>)}</div>}
  </section>
}

export function SettingsAdminPage() {
  const [rows,setRows]=useState<Item[]>([]),[key,setKey]=useState('business_display_name')
  const [value,setValue]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('')
  const load=useCallback(()=>getRows('admin/system-settings').then(setRows).catch(e=>setError(err(e))),[])
  useEffect(()=>{void load()},[load])
  async function submit(e:FormEvent){e.preventDefault();setError('')
    try{await api('admin/system-settings/'+key,{method:'PUT',body:JSON.stringify({
      value:key.endsWith('_days')?Number(value):value
    })});setMessage('Setting saved');await load()}
    catch(e){setError(err(e))}
  }
  return <section className="page"><h1>System configuration</h1><p>Only safe operational settings can be edited here. Provider secrets remain in the server environment, never in this portal.</p><Notice error={error}/>{message&&<p role="status">{message}</p>}
    <form className="resource-form" onSubmit={submit}><div className="fields">
      <label>Setting<select value={key} onChange={e=>setKey(e.target.value)}><option value="business_display_name">Business display name</option><option value="support_email">Support email</option><option value="rent_reminder_days">Rent reminder days</option><option value="default_late_fee_days">Late fee grace days</option></select></label>
      <label>Value<input required value={value} onChange={e=>setValue(e.target.value)}/></label>
    </div><button className="button">Save setting</button></form>
    <h2>Configured values</h2>{!rows.length?<Empty>Default system settings are being used.</Empty>:<div className="module-list">{rows.map(row=><article className="module-card" key={txt(row.key)}><strong>{txt(row.key)}</strong><p>{txt(row.value)}</p></article>)}</div>}
  </section>
}
