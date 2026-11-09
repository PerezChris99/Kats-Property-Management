import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from './lib/api'

type Row=Record<string,unknown>
const label=(value:unknown)=>String(value??'—')
const message=(reason:unknown)=>reason instanceof Error?reason.message:'Request failed'

export function ForgotPasswordPage() {
  const [email,setEmail]=useState('')
  const [error,setError]=useState('')
  const [sent,setSent]=useState(false)
  const [busy,setBusy]=useState(false)
  async function submit(event:FormEvent){
    event.preventDefault();setBusy(true);setError('')
    try {
      await api('auth/recover',{method:'POST',body:JSON.stringify({email})})
      setSent(true)
    } catch (reason) {setError(message(reason))}
    finally {setBusy(false)}
  }
  return <main className="auth-layout"><section className="auth-card">
    <Link className="brand" to="/">Kats Property Management</Link>
    <h1>Recover your account</h1>
    <p>Enter your account email. If it is registered and active, you'll receive a secure link valid for 30 minutes.</p>
    {error&&<p role="alert" className="error">{error}</p>}
    {sent?<p role="status">If an active account matches, recovery instructions have been requested. Check your email.</p>:
    <form onSubmit={submit}><label>Email<input type="email" autoComplete="email" required maxLength={254}
      value={email} onChange={e=>setEmail(e.target.value)}/></label>
      <button className="button full" disabled={busy}>{busy?'Requesting…':'Send recovery instructions'}</button>
    </form>}
    <Link className="back" to="/login">Return to sign in</Link>
  </section></main>
}

export function CompleteAccountLinkPage({kind}:{kind:'invitation'|'reset'}) {
  const [token]=useState(()=>new URLSearchParams(window.location.hash.slice(1)).get('token')||'')
  const [password,setPassword]=useState('')
  const [confirm,setConfirm]=useState('')
  const [busy,setBusy]=useState(false)
  const [done,setDone]=useState(false)
  const [error,setError]=useState('')
  useEffect(()=>{
    // Remove the secret from the address bar and history after capturing it.
    if(window.location.hash)window.history.replaceState(window.history.state,'',window.location.pathname)
  },[])
  async function submit(event:FormEvent) {
    event.preventDefault();setError('')
    if(password!==confirm){setError('Passwords do not match');return}
    setBusy(true)
    try {
      await api('auth/complete-token',{method:'POST',
        body:JSON.stringify({token,new_password:password})})
      setDone(true);setPassword('');setConfirm('')
    } catch(reason) {setError(message(reason))}
    finally {setBusy(false)}
  }
  return <main className="auth-layout"><section className="auth-card">
    <Link className="brand" to="/">Kats Property Management</Link>
    <h1>{kind==='invitation'?'Activate your account':'Set a new password'}</h1>
    <p>{kind==='invitation'?'Create a private password to accept your invitation.':'Use your one-time recovery link to choose a new password. Other sessions will be signed out.'}</p>
    {error&&<p role="alert" className="error">{error}</p>}
    {done?<p role="status">Your password has been saved. <Link to="/login">Sign in</Link>.</p>:
    !token?<p role="alert">Missing or expired link. Request a new invitation or reset link.</p>:
    <form onSubmit={submit}>
      <label>New password (12+ characters)<input required type="password" autoComplete="new-password"
        minLength={12} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)}/></label>
      <label>Confirm password<input required type="password" autoComplete="new-password"
        minLength={12} maxLength={128} value={confirm} onChange={e=>setConfirm(e.target.value)}/></label>
      <button className="button full" disabled={busy}>{busy?'Saving…':'Set password and activate'}</button>
    </form>}
    <Link className="back" to="/login">Back to sign in</Link>
  </section></main>
}

export function InvitationsPage() {
  const [form,setForm]=useState({full_name:'',email:'',role:'TENANT'})
  const [users,setUsers]=useState<Row[]>([])
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [busy,setBusy]=useState(false)
  const load=useCallback(()=>api('admin/users').then(result=>setUsers(result.items||[]))
    .catch(reason=>setError(message(reason))),[])
  useEffect(()=>{void load()},[load])
  async function submit(event:FormEvent) {
    event.preventDefault();setBusy(true);setError('');setNotice('')
    try {
      await api('admin/invitations',{method:'POST',body:JSON.stringify(form)})
      setNotice('Secure invitation sent. The account remains inactive until accepted.')
      setForm({full_name:'',email:'',role:'TENANT'})
      await load()
    } catch(reason) {setError(message(reason))}
    finally {setBusy(false)}
  }
  async function resend(id:string) {
    setBusy(true);setError('');setNotice('')
    try {
      await api('admin/invitations/'+id+'/resend',{method:'POST'})
      setNotice('New one-use invitation sent. The previous link is invalid.')
    } catch(reason) {setError(message(reason))}
    finally {setBusy(false)}
  }
  return <section className="page">
    <span className="eyebrow">SECURE ACCOUNT PROVISIONING</span><h1>Invite a team member or tenant</h1>
    <p>No passwords are shared by administrators. New users activate their account using a short-lived email invitation.</p>
    {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
    <form className="resource-form" onSubmit={submit}>
      <div className="fields">
        <label>Full name<input required maxLength={160} value={form.full_name} onChange={e=>setForm({...form,full_name:e.target.value})}/></label>
        <label>Email<input required type="email" maxLength={254} value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label>
        <label>Role<select value={form.role} onChange={e=>setForm({...form,role:e.target.value})}>
          <option value="TENANT">Tenant</option><option value="CARETAKER">Caretaker</option>
          <option value="ACCOUNTANT">Accountant</option><option value="MANAGER">Manager</option>
        </select></label>
      </div><button className="button" disabled={busy}>{busy?'Sending…':'Send secure invitation'}</button>
    </form>
    <h2>Pending invitations</h2>
    {users.filter(u=>u.is_active===false && ['TENANT','CARETAKER','ACCOUNTANT','MANAGER'].includes(label(u.role))).length===0?
      <p>No inactive invitees in the current result page.</p>:
      <div className="module-list">{users.filter(u=>u.is_active===false &&
       ['TENANT','CARETAKER','ACCOUNTANT','MANAGER'].includes(label(u.role))).map(u=>
        <article className="module-card" key={label(u.id)}>
          <strong>{label(u.full_name)} · {label(u.role)}</strong><p>{label(u.email)}</p>
          <button className="outline-button" disabled={busy} onClick={()=>resend(label(u.id))}>Resend invitation</button>
        </article>)}</div>}
  </section>
}

type PermissionRow={name:string;description:string;granted_roles:string[]}
const ROLES=['SUPER_ADMIN','OWNER','MANAGER','ACCOUNTANT','CARETAKER','TENANT']
export function PermissionMatrixPage({user}:{user:{role:string}}) {
  const [rows,setRows]=useState<PermissionRow[]>([])
  const [selected,setSelected]=useState('MANAGER')
  const [busy,setBusy]=useState('')
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const load=useCallback(()=>api('admin/permissions').then(r=>setRows(r.items||[]))
    .catch(reason=>setError(message(reason))),[])
  useEffect(()=>{void load()},[load])
  async function toggle(permission:PermissionRow){
    const enabled=permission.granted_roles.includes(selected)
    if(!window.confirm((enabled?'Revoke':'Grant')+' '+permission.name+' for '+selected+'?'))return
    setBusy(permission.name);setError('');setNotice('')
    try {
      await api('admin/permissions/'+encodeURIComponent(permission.name)+'/roles/'+selected,{
        method:'PUT',body:JSON.stringify({allowed:!enabled})})
      await load();setNotice('Permission change was audited and is effective immediately.')
    } catch(reason) {setError(message(reason))}
    finally {setBusy('')}
  }
  return <section className="page">
    <span className="eyebrow">ACCESS GOVERNANCE</span><h1>Role permissions</h1>
    <p>The server's original role restrictions remain the maximum authority. A revoked grant removes access immediately. New permissions need administrator seeding after deployment.</p>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
    <label style={{maxWidth:320}}>Show role
      <select value={selected} onChange={e=>setSelected(e.target.value)}>
        {ROLES.map(role=><option key={role} value={role}>{role.replaceAll('_',' ')}</option>)}
      </select></label>
    <div className="data-table-wrap"><table>
      <thead><tr><th>Endpoint permission</th><th>{selected.replaceAll('_',' ')}</th><th>Action</th></tr></thead>
      <tbody>{rows.map(row=>{const on=row.granted_roles.includes(selected);return <tr key={row.name}>
        <td><strong>{row.name}</strong><small style={{display:'block'}}>{row.description}</small></td>
        <td>{on?'Allowed':'Revoked / not granted'}</td>
        <td>{user.role==='SUPER_ADMIN'?<button type="button" disabled={busy!==''}
          className="outline-button" onClick={()=>toggle(row)}>{busy===row.name?'Saving…':on?'Revoke':'Grant'}</button>:
          <span>Read only</span>}</td>
      </tr>})}</tbody>
    </table></div>
  </section>
}

export function RoomPlacementPage() {
  const [rooms,setRooms]=useState<Row[]>([]),[floors,setFloors]=useState<Row[]>([])
  const [chosen,setChosen]=useState<Record<string,string>>({})
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState('')
  const load=useCallback(()=>Promise.all([api('rooms'),api('floors')]).then(([r,f])=>{
    setRooms(r.items||[]);setFloors(f.items||[])
  }).catch(reason=>setError(message(reason))),[])
  useEffect(()=>{void load()},[load])
  async function move(room:Row){
    const floor_id=chosen[label(room.id)]??label(room.floor_id??'')
    const reason=window.prompt('Why is this room being reassigned?')
    if(!reason?.trim())return
    setBusy(label(room.id));setError('');setNotice('')
    try {
      await api('rooms/'+room.id+'/floor',{method:'PUT',body:JSON.stringify({
        floor_id:floor_id||null,reason})})
      await load();setNotice('Room placement changed and recorded in the audit log.')
    }catch(reason){setError(message(reason))}finally{setBusy('')}
  }
  return <section className="page">
    <span className="eyebrow">BUILDING ALLOCATION</span><h1>Room placement</h1>
    <p>Assign rooms to floors belonging to the same property. Existing rooms may remain unassigned.</p>
    {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
    <div className="module-list">{rooms.map(room=><article className="module-card" key={label(room.id)}>
      <strong>Room {label(room.number)}</strong><p>Property: {label(room.property_id)}</p>
      <label>Floor<select value={chosen[label(room.id)]??label(room.floor_id??'')}
        onChange={e=>setChosen({...chosen,[label(room.id)]:e.target.value})}>
        <option value="">Not assigned</option>{floors.map(f=><option key={label(f.id)} value={label(f.id)}>
          {label(f.label)} (level {label(f.level)})
        </option>)}
      </select></label>
      <button className="outline-button" disabled={busy!==''} onClick={()=>move(room)}>
        {busy===label(room.id)?'Saving…':'Update placement'}</button>
    </article>)}</div>
  </section>
}
