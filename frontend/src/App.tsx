import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Building2, CreditCard, LayoutDashboard, Menu, ShieldCheck, Wrench, LogOut } from 'lucide-react'

type User = { id: string; full_name: string; role: string }
type Row = Record<string, string | number | null>
type Field = { name: string; label: string; type?: string; required?: boolean; options?: string[] }
type Resource = { title: string; path: string; fields: Field[]; columns: string[]; writable?: string[] }
const RESOURCES: Record<string, Resource> = {
  properties: {title:'Properties',path:'properties', columns:['name','address','district'], writable:['OWNER','MANAGER','SUPER_ADMIN'],
    fields:[{name:'name',label:'Property name',required:true},{name:'address',label:'Address',required:true},{name:'district',label:'District',required:true}]},
  rooms: {title:'Rooms',path:'rooms',columns:['number','status','rent_ugx','deposit_ugx'],writable:['OWNER','MANAGER','SUPER_ADMIN'],
    fields:[{name:'property_id',label:'Property ID',required:true},{name:'number',label:'Room number',required:true},{name:'rent_ugx',label:'Monthly rent (UGX)',type:'number',required:true},{name:'deposit_ugx',label:'Deposit (UGX)',type:'number'}]},
  tenants: {title:'Tenants',path:'tenants',columns:['full_name','phone','email'],writable:['OWNER','MANAGER','SUPER_ADMIN'],
    fields:[{name:'full_name',label:'Full name',required:true},{name:'phone',label:'Phone',required:true},{name:'email',label:'Email',type:'email'}]},
  leases: {title:'Leases',path:'leases',columns:['room_id','tenant_id','start_date','end_date','rent_ugx','status'],writable:['OWNER','MANAGER','SUPER_ADMIN'],
    fields:[{name:'room_id',label:'Room ID',required:true},{name:'tenant_id',label:'Tenant ID',required:true},{name:'start_date',label:'Start date',type:'date',required:true},{name:'end_date',label:'End date',type:'date',required:true},{name:'rent_ugx',label:'Rent (UGX)',type:'number',required:true},{name:'deposit_ugx',label:'Deposit (UGX)',type:'number'}]},
  invoices: {title:'Rent invoices',path:'invoices',columns:['invoice_number','due_date','total_ugx','paid_ugx','status'],writable:['OWNER','MANAGER','ACCOUNTANT','SUPER_ADMIN'],
    fields:[{name:'lease_id',label:'Lease ID',required:true},{name:'period_start',label:'Period starts',type:'date',required:true},{name:'period_end',label:'Period ends',type:'date',required:true},{name:'due_date',label:'Payment due',type:'date',required:true},{name:'total_ugx',label:'Amount (UGX)',type:'number',required:true}]},
  payments: {title:'Payments',path:'payments',columns:['invoice_id','method','amount_ugx','status'],writable:['OWNER','MANAGER','ACCOUNTANT','SUPER_ADMIN'],
    fields:[{name:'invoice_id',label:'Invoice ID',required:true},{name:'method',label:'Method',required:true,options:['CASH','BANK_TRANSFER']},{name:'amount_ugx',label:'Amount (UGX)',type:'number',required:true},{name:'reference',label:'Bank transaction reference'},{name:'idempotency_key',label:'Unique command reference',required:true}]},
  maintenance: {title:'Maintenance',path:'maintenance',columns:['title','room_id','priority','status'],writable:['OWNER','MANAGER','ACCOUNTANT','SUPER_ADMIN','TENANT'],
    fields:[{name:'room_id',label:'Room ID',required:true},{name:'title',label:'Issue',required:true},{name:'description',label:'Description',required:true},{name:'priority',label:'Priority',options:['LOW','MEDIUM','HIGH','URGENT']}]},
  expenses: {title:'Expenses',path:'expenses',columns:['property_id','category','amount_ugx','incurred_on'],writable:['OWNER','MANAGER','ACCOUNTANT','SUPER_ADMIN'],
    fields:[{name:'property_id',label:'Property ID',required:true},{name:'category',label:'Category',required:true},{name:'description',label:'Description',required:true},{name:'amount_ugx',label:'Amount (UGX)',type:'number',required:true},{name:'incurred_on',label:'Date',type:'date',required:true}]}
}
const roles = ['OWNER','MANAGER','ACCOUNTANT','SUPER_ADMIN']
const formats = (key: string, value: string | number | null) => key.endsWith('_ugx') && typeof value === 'number' ? 'UGX ' + value.toLocaleString('en-UG') : String(value ?? '—')
function csrfToken() {return document.cookie.split('; ').find(c => c.startsWith('csrf_access_token='))?.split('=')[1] ?? ''}
async function api(path: string, opts: RequestInit = {}) {
  const headers = new Headers(opts.headers)
  if (opts.body) headers.set('Content-Type', 'application/json')
  if (opts.method && opts.method !== 'GET') headers.set('X-CSRF-TOKEN', csrfToken())
  const response = await fetch('/api/v1/' + path, {...opts, headers, credentials:'same-origin', cache:'no-store'})
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.error?.message || 'Request failed (' + response.status + ')')
  return payload
}
function Header({user, logout}: {user:User|null;logout?:()=>void}) {
  return <header className="site-header"><Link to="/" className="brand"><Building2 size={24} aria-hidden="true"/> Kats <small>Property Management</small></Link>
  <nav aria-label="Main navigation">{user ? <><Link to="/dashboard">Workspace</Link><button className="link-button" onClick={logout}>Sign out</button></> : <><Link to="/features">Features</Link><Link to="/contact">Contact</Link><Link className="button small" to="/login">Sign in</Link></>}</nav></header>
}
function Footer() {return <footer><span>© {new Date().getFullYear()} Kats Property Management</span><nav aria-label="Legal"><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><Link to="/cookies">Cookies</Link><Link to="/contact">Support</Link></nav></footer>}
function Landing({user,logout}: {user:User|null;logout:()=>void}) {
  const features = [{icon:Building2,title:'Property oversight',body:'Know which units are occupied and what rent is due.'},
    {icon:CreditCard,title:'Verified collections',body:'Review cash and bank records before counting them as collected.'},
    {icon:Wrench,title:'Maintenance tracking',body:'Keep requests visible and actionable.'},
    {icon:ShieldCheck,title:'Fiscal readiness',body:'Prepare records for applicable EFRIS requirements.'}]
  return <><Header user={user} logout={logout}/><main><section className="hero"><div><span className="eyebrow">BUILT FOR UGANDAN RENTALS</span><h1>Manage your rentals, collect rent, and stay compliant.</h1><p>One organized view of rooms, tenants, rent, arrears, maintenance and property expenses.</p><div className="actions"><Link className="button" to={user?'/dashboard':'/contact'}>Get started</Link><Link className="button outline" to="/features">Explore features</Link></div></div>
  <div className="mock"><div className="mock-top"><LayoutDashboard size={20}/> Rental portfolio</div><div className="mock-number"><small>Monthly collections</small><strong>UGX —</strong><span>Live totals are available after sign-in</span></div><div className="mock-duo"><div><small>Occupancy</small><strong>—</strong></div><div><small>Arrears</small><strong>—</strong></div></div><div className="mock-caption">No fabricated balances</div></div></section>
  <section className="section"><span className="eyebrow">A SINGLE SOURCE OF TRUTH</span><h2>Leave scattered notebooks, Excel sheets and payment screenshots behind.</h2><p>From vacant rooms to unpaid invoices, bring the important facts into the same secure workflow.</p></section>
  <section className="section"><h2>Tools for the work that matters.</h2><div className="features">{features.map(f=><article className="feature" key={f.title}><f.icon size={24}/><h3>{f.title}</h3><p>{f.body}</p></article>)}</div></section>
  <section className="section process"><h2>How it works</h2><ol><li>Add properties and rooms</li><li>Register tenants and leases</li><li>Issue invoices and confirm collections</li><li>Track maintenance and property expenses</li><li>Review business performance</li></ol></section>
  <section className="section highlight"><h2>One rental business. One clear picture.</h2><p>Designed for practical Ugandan rental workflows, with UGX-native accounting records and mobile-first navigation.</p><Link className="button" to="/contact">Get in touch</Link></section></main><Footer/></>
}
function TextPage({title,body,user,logout}: {title:string;body:string;user:User|null;logout:()=>void}) {
  return <><Header user={user} logout={logout}/><main className="section simple"><h1>{title}</h1><p>{body}</p></main><Footer/></>
}
function Login({onSuccess}: {onSuccess:(user:User)=>void}) {
  const navigate = useNavigate()
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  async function submit(event:FormEvent) {
    event.preventDefault();setBusy(true);setError('')
    try {const payload=await api('auth/login',{method:'POST',body:JSON.stringify({email,password})});onSuccess(payload.user);navigate('/dashboard')}
    catch(err) {setError(err instanceof Error?err.message:'Unable to sign in')}
    finally {setBusy(false)}
  }
  return <div className="auth-layout"><div className="auth-card"><Link to="/" className="brand"><Building2/> Kats</Link><h1>Sign in</h1><p>Secure access for authorized users.</p><form onSubmit={submit}><label>Email<input type="email" autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)} required/></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/></label>{error&&<p role="alert" className="error">{error}</p>}<button className="button full" disabled={busy}>{busy?'Signing in…':'Continue'}</button></form><Link to="/" className="back">Back to website</Link></div></div>
}
function ResourcePage({resource,user}: {resource:Resource;user:User}) {
  const [rows,setRows]=useState<Row[]>([])
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  const [editing,setEditing]=useState(false)
  const [values,setValues]=useState<Record<string,string>>({})
  const [busy,setBusy]=useState(false)
  const canWrite=resource.writable?.includes(user.role)??false
  const load=useCallback(async()=>{
    setLoading(true);setError('')
    try {const payload=await api(resource.path);setRows(payload.items||[])}
    catch(err) {setError(err instanceof Error?err.message:'Could not load')}
    finally {setLoading(false)}
  },[resource.path])
  useEffect(()=>{void load()},[load])
  async function submit(event:FormEvent) {
    event.preventDefault();setBusy(true);setError('')
    const body:Record<string,string|number>={}
    for(const field of resource.fields) {
      const value=values[field.name]||''
      if(value || field.required) body[field.name]=field.type==='number'?Number(value):value
    }
    try {await api(resource.path==='payments'?'payments/manual':resource.path,{method:'POST',body:JSON.stringify(body)});setEditing(false);setValues({});await load()}
    catch(err) {setError(err instanceof Error?err.message:'Could not save')}
    finally {setBusy(false)}
  }
  async function approve(id:string) {
    setBusy(true);setError('')
    try {await api('payments/'+id+'/approve',{method:'POST'});await load()}
    catch(err) {setError(err instanceof Error?err.message:'Could not approve')}
    finally {setBusy(false)}
  }
  return <section className="page"><div className="page-head"><div><span className="eyebrow">OPERATIONS</span><h1>{resource.title}</h1></div>{canWrite&&<button className="button" onClick={()=>setEditing(!editing)}>{editing?'Cancel':'Add '+resource.title.toLowerCase()}</button>}</div>
    {error&&<p role="alert" className="error">{error}</p>}
    {editing&&canWrite&&<form className="resource-form" onSubmit={submit}><h2>New record</h2><div className="fields">{resource.fields.map(field=><label key={field.name}>{field.label}{field.options?<select value={values[field.name]||''} onChange={e=>setValues({...values,[field.name]:e.target.value})} required={field.required}><option value="">Select</option>{field.options.map(option=><option key={option}>{option}</option>)}</select>:<input required={field.required} type={field.type||'text'} min={field.type==='number'?'0':undefined} value={values[field.name]||''} onChange={e=>setValues({...values,[field.name]:e.target.value})}/>}</label>)}</div><button className="button" disabled={busy}>{busy?'Saving…':'Save record'}</button></form>}
    {loading?<p role="status">Loading records…</p>:rows.length===0?<div className="empty"><h2>No records yet</h2><p>Authorized records will appear here after they are created.</p></div>:<div className="data-table-wrap"><table><thead><tr>{resource.columns.map(col=><th key={col}>{col.replaceAll('_',' ')}</th>)}{resource.path==='payments'&&canWrite&&<th>Review</th>}</tr></thead><tbody>{rows.map((item,i)=><tr key={String(item.id||i)}>{resource.columns.map(col=><td key={col}>{formats(col,item[col])}</td>)}{resource.path==='payments'&&canWrite&&<td>{item.status==='PENDING_REVIEW'?<button className="outline-button" disabled={busy} onClick={()=>approve(String(item.id))}>Approve*</button>:<span>—</span>}</td>}</tr>)}</tbody></table></div>}
    {resource.path==='payments'&&<p className="note">*Approval requires another staff member to verify source evidence. This action credits the invoice and cannot be undone through this interface.</p>}
    <p className="note">Records are scoped by server-side permissions. Copy IDs from existing records when linking items.</p></section>
}
function Dashboard({user}: {user:User}) {
  const [summary,setSummary]=useState<Record<string,number>|null>(null)
  const [error,setError]=useState('')
  useEffect(()=>{api('dashboard').then(setSummary).catch(err=>setError(String(err)))},[])
  return <section className="page"><span className="eyebrow">PORTFOLIO OVERVIEW</span><h1>Welcome, {user.full_name.split(' ')[0]}</h1><p>Current recorded balances, not estimates of unverified payments.</p>{error&&<p role="alert" className="error">{error}</p>}{!summary?<p>Loading dashboard…</p>:<div className="stat-grid">
  {[['Expected',summary.expected_ugx,true],['Collected',summary.collected_ugx,true],['Outstanding',summary.outstanding_ugx,true],['Occupied rooms',summary.occupied_rooms,false],['Vacant / other rooms',summary.vacant_rooms,false],['Open maintenance',summary.open_maintenance,false]].map(([label,value,currency])=><div className="stat" key={String(label)}><small>{label}</small><strong>{currency?'UGX ':''}{Number(value).toLocaleString('en-UG')}</strong></div>)}</div>}
  <div className="quick"><h2>Common actions</h2><Link to="/properties">Properties</Link><Link to="/rooms">Rooms</Link><Link to="/invoices">Invoices</Link><Link to="/payments">Payments</Link></div></section>
}
function Portal({user,logout}: {user:User;logout:()=>void}) {
  const location=useLocation()
  const page=location.pathname.slice(1)
  const canOperate=roles.includes(user.role)
  const nav = canOperate?['dashboard','properties','rooms','tenants','leases','invoices','payments','maintenance','expenses']:['invoices','payments','maintenance']
  return <div className="portal"><aside className="side"><Link to="/" className="brand">Kats</Link><div className="role">{user.role.replaceAll('_',' ')}</div><nav aria-label="Workspace">{nav.map(key=><Link key={key} className={page===key?'active':''} to={'/'+key}>{key[0].toUpperCase()+key.slice(1)}</Link>)}</nav><button className="link-button logout" onClick={logout}><LogOut size={16}/> Sign out</button></aside>
  <div className="portal-main"><header className="portal-bar"><span>Kats Property Management</span><span>{user.full_name}</span></header><main>{page==='dashboard'&&canOperate?<Dashboard user={user}/>:RESOURCES[page]&&nav.includes(page)?<ResourcePage resource={RESOURCES[page]} user={user}/>:<div className="page"><h1>Access restricted</h1><p>This area is not available to your account.</p></div>}</main></div><nav className="mobile-nav" aria-label="Mobile workspace navigation">{(canOperate?['dashboard','rooms','payments','maintenance']:['invoices','payments','maintenance']).map((key,i)=>{const Icon=[LayoutDashboard,Building2,CreditCard,Wrench][i];return <Link key={key} to={'/'+key} className={page===key?'active':''}><Icon size={20}/><span>{key[0].toUpperCase()+key.slice(1)}</span></Link>})}<Link to="/more"><Menu size={20}/><span>More</span></Link></nav></div>
}
export default function App() {
  const [user,setUser]=useState<User|null>(null)
  const [ready,setReady]=useState(false)
  const [online,setOnline]=useState(navigator.onLine)
  const navigate=useNavigate()
  useEffect(()=>{api('auth/me').then(p=>setUser(p.user)).catch(()=>{}).finally(()=>setReady(true))},[])
  useEffect(()=>{const update=()=>setOnline(navigator.onLine);window.addEventListener('online',update);window.addEventListener('offline',update);return()=>{window.removeEventListener('online',update);window.removeEventListener('offline',update)}},[])
  function logout(){api('auth/logout',{method:'POST'}).catch(()=>{}).finally(()=>{setUser(null);navigate('/')})}
  if(!ready)return <div className="loading">Loading Kats…</div>
  const legal:Record<string,string>={privacy:'Privacy policy requires client and legal review before launch. This system is not yet deployed for public customer use.',terms:'Terms of service are pending customer approval. Financial and EFRIS services are not yet live.',cookies:'Essential secure session cookies are used for authenticated access. Additional processing will be documented before deployment.'}
  return <>{!online&&<div className="offline" role="status">Offline. Reconnect to view private records.</div>}<Routes>
    <Route path="/" element={<Landing user={user} logout={logout}/>}/>
    <Route path="/login" element={user?<Navigate to="/dashboard" replace/>:<Login onSuccess={setUser}/>}/>
    <Route path="/features" element={<TextPage title="Features" body="Manage units, leases, invoices, verified manual payments, maintenance and expenses. MTN/Airtel and EFRIS require provider verification." user={user} logout={logout}/>}/>
    <Route path="/contact" element={<TextPage title="Contact and support" body="Contact details and demo-booking workflow will be published before launch. No payment is accepted through this page." user={user} logout={logout}/>}/>
    {Object.entries(legal).map(([slug,body])=><Route key={slug} path={'/'+slug} element={<TextPage title={slug[0].toUpperCase()+slug.slice(1)} body={body} user={user} logout={logout}/>}/>)}
    {['dashboard','properties','rooms','tenants','leases','invoices','payments','maintenance','expenses','more'].map(path=><Route key={path} path={'/'+path} element={user?<Portal user={user} logout={logout}/>:<Navigate to="/login" replace/>}/>)}
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes></>
}
