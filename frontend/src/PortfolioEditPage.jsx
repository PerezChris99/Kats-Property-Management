import { useCallback, useEffect, useState } from 'react';
import { api } from './lib/api';
const OPTIONS = {
    properties: [{ name: 'name', label: 'Property name', required: true },
        { name: 'address', label: 'Address', required: true }, { name: 'district', label: 'District', required: true }],
    buildings: [{ name: 'name', label: 'Building name', required: true },
        { name: 'description', label: 'Building description' }],
    floors: [{ name: 'level', label: 'Floor level', type: 'number', required: true },
        { name: 'label', label: 'Floor label', required: true }],
    rooms: [{ name: 'number', label: 'Room number', required: true },
        { name: 'rent_ugx', label: 'Advertised monthly rent UGX', type: 'number', required: true },
        { name: 'deposit_ugx', label: 'Advertised deposit UGX', type: 'number', required: true }]
};
const RESOURCE = ['properties', 'buildings', 'floors', 'rooms'];
const display = (value) => String(value ?? '—');
export function PortfolioEditPage() {
    const [kind, setKind] = useState('properties');
    const [query, setQuery] = useState('');
    const [appliedQuery, setAppliedQuery] = useState('');
    const [items, setItems] = useState([]);
    const [selected, setSelected] = useState('');
    const [values, setValues] = useState({});
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [notice, setNotice] = useState('');
    const load = useCallback(async () => {
        const r = await api(kind + (appliedQuery ? '?q=' + encodeURIComponent(appliedQuery) : ''));
        setItems(r.items || []);
    }, [kind, appliedQuery]);
    useEffect(() => {
        setError('');
        setSelected('');
        setValues({});
        load().catch(reason => setError(reason instanceof Error ? reason.message : 'Failed to load portfolio'));
    }, [load]);
    useEffect(() => {
        const item = items.find(i => display(i.id) === selected);
        if (item)
            setValues(Object.fromEntries(OPTIONS[kind].map(field => [field.name, display(item[field.name] ?? '')])));
    }, [selected, items, kind]);
    async function submit(event) {
        event.preventDefault();
        if (!selected)
            return;
        setBusy(true);
        setError('');
        setNotice('');
        const payload = {};
        for (const field of OPTIONS[kind]) {
            if (values[field.name] !== undefined) {
                payload[field.name] = field.type === 'number' ? Number(values[field.name]) : values[field.name];
            }
        }
        const endpoint = kind === 'rooms' ? 'rooms/' + selected + '/details' : kind + '/' + selected;
        try {
            const r = await api(endpoint, { method: 'PUT', body: JSON.stringify(payload) });
            await load();
            setNotice(display(r.notice || 'Portfolio record updated and permanently audited.'));
        }
        catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Could not update');
        }
        finally {
            setBusy(false);
        }
    }
    return <section className="page">
    <span className="eyebrow">PORTFOLIO MANAGEMENT</span><h1>Edit property information</h1>
    <p>Make reversible changes to property, building, floor and listing details. Room pricing updates affect advertised prices only — existing signed lease rents and deposits remain unchanged.</p>
    {error && <p role="alert" className="error">{error}</p>}{notice && <p role="status">{notice}</p>}
    <div className="resource-form">
      <div className="fields">
        <label>Resource<select value={kind} onChange={e => { setKind(e.target.value); setQuery(''); setAppliedQuery(''); }}>
          {RESOURCE.map(k => <option key={k} value={k}>{k[0].toUpperCase() + k.slice(1)}</option>)}
        </select></label>
        <label>Search records<input placeholder="Search name or number" value={query} maxLength={80} onChange={e => setQuery(e.target.value)}/></label>
      </div><button className="outline-button" type="button" onClick={() => setAppliedQuery(query)}>Search</button>
    </div>
    <form className="resource-form" onSubmit={submit}>
      <h2>Choose a record</h2>
      <label>{kind[0].toUpperCase() + kind.slice(1)}
        <select required value={selected} onChange={e => setSelected(e.target.value)}>
          <option value="">Select existing record</option>
          {items.map(item => <option key={display(item.id)} value={display(item.id)}>
            {display(item.name || item.label || item.number || item.id)}
          </option>)}
        </select>
      </label>
      {selected && <>
        <div className="fields">{OPTIONS[kind].map(field => <label key={field.name}>{field.label}
          <input required={field.required} type={field.type || 'text'} min={field.type === 'number' ? (field.name === 'level' ? '-10' : '0') : undefined} max={field.name === 'level' ? '300' : undefined} value={values[field.name] || ''} onChange={e => setValues({ ...values, [field.name]: e.target.value })}/>
        </label>)}</div>
        <button className="button" disabled={busy}>{busy ? 'Saving…' : 'Save audited changes'}</button>
      </>}
    </form>
  </section>;
}
