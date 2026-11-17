import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Command, Search, X } from 'lucide-react';
import { api } from './lib/api';
import { PAGE_META, labelFor } from './WorkspaceNavigation';

const PRIORITY = ['dashboard', 'invoices', 'payments', 'maintenance', 'properties',
  'tenants', 'reports', 'trends', 'statements', 'documents', 'security'];
const destination = item => item.type === 'record'
  ? item.path + '?q=' + encodeURIComponent(item.query)
  : '/' + item.page;

/** One permission-aware command palette for desktop, installed PWA and mobile. */
export function QuickActionsPalette({ pages }) {
  const navigate = useNavigate();
  const location = useLocation();
  const trigger = useRef(null);
  const input = useRef(null);
  const panel = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [term, setTerm] = useState('');
  const [remote, setRemote] = useState({ status: 'idle', items: [], error: '' });
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    function shortcut(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen(value => !value);
      }
    }
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, []);
  useEffect(() => {
    if (!open) return undefined;
    const previouslyFocused = document.activeElement;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => input.current?.focus());
    function keys(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(false);
      }
      if (event.key !== 'Tab') return;
      const focusable = [...(panel.current?.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), a[href]'
      ) || [])];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }
    document.addEventListener('keydown', keys);
    return () => {
      document.body.style.overflow = oldOverflow;
      document.removeEventListener('keydown', keys);
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
      else trigger.current?.focus();
    };
  }, [open]);
  useEffect(() => {
    setOpen(false);
    setQuery('');
    setRemote({status:'idle',items:[],error:''});
  }, [location.pathname]);
  useEffect(() => {
    const timer = setTimeout(() => setTerm(query.trim()), 260);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    if (!open || term.length < 2) {
      setRemote({status:'idle',items:[],error:''});
      return undefined;
    }
    const controller = new AbortController();
    setRemote({status:'loading',items:[],error:''});
    api('workspace/search?q=' + encodeURIComponent(term.slice(0, 80)), {
      signal: controller.signal,
    }).then(data => {
      if (!controller.signal.aborted) setRemote({
        status:'ready',
        items: Array.isArray(data?.items) ? data.items : [],
        error:'',
      });
    }).catch(error => {
      if (!controller.signal.aborted) setRemote({
        status:'error',items:[],error:error.message || 'Search unavailable',
      });
    });
    return () => controller.abort();
  }, [open, term]);
  const items = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const allowed = [...new Set(pages)];
    const order = (page) => {
      const index = PRIORITY.indexOf(page);
      return index >= 0 ? index : PRIORITY.length + allowed.indexOf(page);
    };
    const routes = allowed.filter(page => !needle
      ? PRIORITY.includes(page)
      : labelFor(page).toLowerCase().includes(needle) ||
        page.replaceAll('-', ' ').includes(needle))
      .sort((a,b) => order(a) - order(b)).slice(0, needle ? 10 : 6)
      .map(page => ({id:'page:'+page,type:'page',page,label:labelFor(page)}));
    const records = needle.length >= 2 ? remote.items.filter(item =>
      typeof item?.path === 'string' && item.path.startsWith('/') &&
      allowed.includes(item.path.slice(1)) && typeof item?.label === 'string'
    ).slice(0,18).map(item => ({
      id:'record:'+item.kind+':'+item.value, type:'record',
      path:item.path, query, label:item.label,
      detail:item.detail || item.kind,
    })) : [];
    return [...routes, ...records];
  }, [pages, query, remote.items]);
  useEffect(() => { setSelected(0); }, [query, remote.items]);
  const choose = item => {
    if (!item) return;
    setOpen(false);
    navigate(destination(item));
  };
  function keyDown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setSelected(value => (value + 1) % Math.max(items.length,1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setSelected(value => (value + Math.max(items.length,1)-1) % Math.max(items.length,1));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      choose(items[selected] || items[0]);
    }
  }

  return <>
    <button ref={trigger} type="button" className="kats-command-trigger"
      aria-haspopup="dialog" aria-expanded={open}
      onClick={() => setOpen(true)} aria-label="Search pages, records and quick actions">
      <Search size={17} aria-hidden="true"/>
      <span>Search or jump to…</span>
      <kbd>Ctrl / ⌘ K</kbd>
    </button>
    {open && <div className="kats-command-backdrop"
      onMouseDown={event => {if (event.target === event.currentTarget) setOpen(false);}}>
      <section ref={panel} role="dialog" aria-modal="true"
        aria-label="Quick actions and authorized workspace search"
        className="kats-command-dialog">
        <div className="kats-command-head">
          <div><Command size={18} aria-hidden="true"/><strong>Quick actions</strong></div>
          <button className="kats-command-close" type="button"
            aria-label="Close quick actions" onClick={() => setOpen(false)}>
            <X size={19} aria-hidden="true"/></button>
        </div>
        <div className="kats-command-input">
          <Search size={20} aria-hidden="true"/>
          <input ref={input} type="search" maxLength={80}
            placeholder="Find a page, invoice, tenant or task…"
            aria-label="Search authorized pages and records"
            value={query} onChange={event => setQuery(event.target.value)}
            onKeyDown={keyDown}/>
          <kbd>ESC</kbd>
        </div>
        <div className="kats-command-results" aria-live="polite">
          <p className="kats-command-category">
            {query ? 'Matches and authorized records' : 'Suggested destinations'}
          </p>
          {items.length > 0 ? <ul>
            {items.map((item,index) => {
              const Icon = PAGE_META[item.page]?.icon || (item.type === 'record' ? Search : ArrowRight);
              return <li key={item.id}>
                <button type="button"
                  className={index === selected ? 'is-selected' : ''}
                  onMouseEnter={() => setSelected(index)}
                  onClick={() => choose(item)}>
                  <Icon size={18} aria-hidden="true"/>
                  <span><strong>{item.label}</strong>
                    {item.detail && <small>{item.detail}</small>}</span>
                  <ArrowRight size={16} aria-hidden="true"/>
                </button>
              </li>;
            })}
          </ul> : <p className="kats-command-empty">
            {remote.status === 'loading' ? 'Searching authorized records…'
              : 'No matching destinations. Try a different term.'}
          </p>}
          {remote.status === 'error' && <p className="kats-command-error" role="alert">
            Records unavailable: {remote.error}. Navigation remains available.
          </p>}
        </div>
        <footer className="kats-command-foot">↑ ↓ to navigate · Enter to open · Esc to close
          <span>Results follow your account permissions</span></footer>
      </section>
    </div>}
  </>;
}
