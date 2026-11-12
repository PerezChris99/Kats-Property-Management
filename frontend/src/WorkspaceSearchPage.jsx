import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from './lib/api';

/** Permission-scoped search; never caches results between user sessions. */
export default function WorkspaceSearchPage() {
  const location = useLocation();
  const [query,setQuery] = useState(() => new URLSearchParams(location.search).get('q') || '');
  const [term,setTerm] = useState('');
  const [state,setState] = useState({status:'idle',data:null,error:''});
  useEffect(() => {
    const timer = setTimeout(() => setTerm(query.trim()),300);
    return () => clearTimeout(timer);
  },[query]);
  useEffect(() => {
    if(term.length < 2) {
      setState({status:'idle',data:null,error:''});
      return;
    }
    const controller = new AbortController();
    setState({status:'loading',data:null,error:''});
    api('workspace/search?q='+encodeURIComponent(term),{signal:controller.signal})
      .then(data => { if(!controller.signal.aborted) setState({status:'ready',data,error:''}); })
      .catch(error => { if(!controller.signal.aborted) setState({
        status:'error',data:null,error:error instanceof Error?error.message:'Search unavailable'
      }); });
    return () => controller.abort();
  },[term]);
  return <section className="page">
    <div className="page-head"><div><span className="eyebrow">WORKSPACE</span>
      <h1>Find records</h1><p>Search only information authorized for your account.</p></div></div>
    <label className="kats-record-search-label">Search properties, tenants, invoices and work
      <input type="search" value={query} onChange={event=>setQuery(event.target.value)}
        minLength={2} maxLength={80} autoFocus placeholder="Enter at least two characters"
        aria-describedby="kats-record-search-note"/>
    </label>
    <p id="kats-record-search-note" className="note">Search results are intentionally limited and never include records outside your permissions.</p>
    {state.status==='idle' && <p className="empty" role="status">Enter at least two characters to start searching.</p>}
    {state.status==='loading' && <p className="data-loading" role="status">Searching authorized records…</p>}
    {state.status==='error' && <p className="error" role="alert">{state.error}</p>}
    {state.status==='ready' && <div aria-live="polite">
      {!state.data.items.length ? <div className="empty"><h2>No matching records</h2><p>Try a different name, invoice number or maintenance title.</p></div> :
        <ul className="kats-search-results">
          {state.data.items.map(item=><li key={item.kind+':'+item.value}>
            <Link to={item.path+'?q='+encodeURIComponent(term)}>
              <span className="kats-search-type">{item.kind.replaceAll('_',' ')}</span>
              <strong>{item.label}</strong>
              <small>{item.detail}</small>
            </Link>
          </li>)}
        </ul>}
    </div>}
  </section>;
}
