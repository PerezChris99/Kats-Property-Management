import { useEffect, useState } from 'react';
import { api } from './lib/api';

const editableRoles = new Set(['OWNER','MANAGER','SUPER_ADMIN']);

export default function AssetsPage({ user }) {
  const writable = editableRoles.has(user.role);
  const [page,setPage]=useState(1);
  const [query,setQuery]=useState('');
  const [term,setTerm]=useState('');
  const [refresh,setRefresh]=useState(0);
  const [data,setData]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);
  const [showForm,setShowForm]=useState(false);
  const [properties,setProperties]=useState([]);
  const [rooms,setRooms]=useState([]);
  const [values,setValues]=useState({
    property_id:'',room_id:'',name:'',category:'',serial_reference:'',
    next_service_on:'',description:''
  });

  useEffect(()=>{
    const timeout=setTimeout(()=>{setPage(1);setTerm(query.trim());},300);
    return ()=>clearTimeout(timeout);
  },[query]);

  useEffect(()=>{
    const controller=new AbortController();
    setLoading(true);setError('');
    const search=term.length>=2?'&q='+encodeURIComponent(term):'';
    api('operations/assets?page='+page+'&page_size=25'+search,{signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted)setData(result);})
      .catch(err=>{if(!controller.signal.aborted)setError(err.message||'Could not load assets');})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[page,term,refresh]);

  useEffect(()=>{
    if(!writable||!showForm)return;
    let active=true;
    api('properties?page_size=100').then(result=>{
      if(active)setProperties(result.items||[]);
    }).catch(()=>{if(active)setError('Could not load properties for the asset form');});
    return ()=>{active=false;};
  },[writable,showForm]);

  useEffect(()=>{
    if(!showForm||!values.property_id)return;
    let active=true;
    setRooms([]);
    api('rooms?property_id='+encodeURIComponent(values.property_id)+'&page_size=100')
      .then(result=>{if(active)setRooms(result.items||[]);})
      .catch(()=>{if(active)setError('Could not load unit references');});
    return ()=>{active=false;};
  },[values.property_id,showForm]);

  async function create(event) {
    event.preventDefault();setBusy(true);setError('');
    try {
      const payload={
        ...values, room_id:values.room_id||null,
        serial_reference:values.serial_reference||null,
        next_service_on:values.next_service_on||null
      };
      await api('operations/assets',{method:'POST',body:JSON.stringify(payload)});
      setShowForm(false);
      setValues({property_id:'',room_id:'',name:'',category:'',serial_reference:'',next_service_on:'',description:''});
      setPage(1);setRefresh(n=>n+1);
    } catch(e) {setError(e.message||'Asset could not be created');}
    finally {setBusy(false);}
  }

  async function changeStatus(asset) {
    const status=window.prompt(
      'New status (IN_SERVICE, NEEDS_SERVICE, OUT_OF_SERVICE, RETIRED)',asset.status);
    if(!status||status===asset.status)return;
    const reason=window.prompt('Reason for this asset status change');
    if(!reason?.trim())return;
    setBusy(true);setError('');
    try {
      await api('operations/assets/'+asset.id,{
        method:'PATCH',body:JSON.stringify({status,reason})
      });
      setRefresh(n=>n+1);
    } catch(e) {setError(e.message||'Status update failed');}
    finally {setBusy(false);}
  }
  return <section className="page">
    <div className="page-head"><div>
      <span className="eyebrow">PROPERTY OPERATIONS</span>
      <h1>Equipment and assets</h1>
      <p>Private register of equipment, condition and upcoming servicing across the owner's properties.</p>
    </div>{writable && <button type="button" className="button" onClick={()=>setShowForm(v=>!v)}>
      {showForm?'Close form':'Register asset'}</button>}</div>
    {error && <p role="alert" className="error">{error}
      <button type="button" className="outline-button small" onClick={()=>setRefresh(n=>n+1)}>Retry</button></p>}
    {showForm&&writable&&<form className="resource-form" onSubmit={create}>
      <h2>Register equipment</h2><div className="fields">
        <label>Property<select required value={values.property_id}
          onChange={e=>setValues({...values,property_id:e.target.value,room_id:''})}>
          <option value="">Choose property</option>{properties.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
        </select></label>
        <label>Unit (optional)<select value={values.room_id}
          onChange={e=>setValues({...values,room_id:e.target.value})}>
          <option value="">Shared / building equipment</option>
          {rooms.map(room=><option key={room.id} value={room.id}>{room.number}</option>)}
        </select></label>
        <label>Name<input required maxLength={160} value={values.name}
          onChange={e=>setValues({...values,name:e.target.value})}/></label>
        <label>Category<input required maxLength={50} placeholder="E.g. PLUMBING"
          value={values.category} onChange={e=>setValues({...values,category:e.target.value})}/></label>
        <label>Serial reference<input maxLength={120} value={values.serial_reference}
          onChange={e=>setValues({...values,serial_reference:e.target.value})}/></label>
        <label>Next service date<input type="date" value={values.next_service_on}
          onChange={e=>setValues({...values,next_service_on:e.target.value})}/></label>
        <label>Description<input maxLength={1000} value={values.description}
          onChange={e=>setValues({...values,description:e.target.value})}/></label>
      </div><button className="button" disabled={busy}>{busy?'Saving…':'Save equipment'}</button>
    </form>}
    <div className="record-toolbar"><label className="record-filter">Find equipment
      <input type="search" value={query} onChange={e=>setQuery(e.target.value)}
        placeholder="Search name or category (2+ letters)"/></label>
      <span aria-live="polite">{data?.total??'—'} registered</span>
    </div>
    {loading?<p className="data-loading" role="status">Loading equipment…</p>:
      !data?.items?.length?<div className="empty" role="status">
        <h2>No matching assets</h2><p>Equipment will appear here after it is registered.</p></div>:
        <div className="data-table-wrap"><table><thead><tr>
          <th>Equipment</th><th>Category</th><th>Condition</th><th>Next service</th>
          {writable&&<th>Action</th>}
        </tr></thead><tbody>{data.items.map(asset=><tr key={asset.id}>
          <td>{asset.name}</td><td>{asset.category}</td><td>{asset.status.replaceAll('_',' ')}</td>
          <td>{asset.next_service_on||'Not scheduled'}</td>
          {writable&&<td><button type="button" className="outline-button small" disabled={busy}
            onClick={()=>changeStatus(asset)}>Update status</button></td>}
        </tr>)}</tbody></table></div>}
    {data&&data.total>25&&<nav className="pagination-controls" aria-label="Equipment pages">
      <button type="button" className="outline-button small" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Previous</button>
      <span>Page {page} of {Math.ceil(data.total/25)}</span>
      <button type="button" className="outline-button small" disabled={page*25>=data.total} onClick={()=>setPage(p=>p+1)}>Next</button>
    </nav>}
    {user.role==='CARETAKER'&&<p className="note">Only equipment assigned to your rooms is shown.</p>}
  </section>;
}
