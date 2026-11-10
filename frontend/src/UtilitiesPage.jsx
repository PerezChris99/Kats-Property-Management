import {useCallback, useEffect, useState} from 'react'
import {api} from './lib/api'

const money = n => 'UGX ' + Number(n || 0).toLocaleString('en-UG')
const errorText = e => e instanceof Error ? e.message : 'Request failed'
const milli = raw => {
  const value = String(raw).trim()
  if (!/^\d+(?:\.\d{1,3})?$/.test(value)) throw new Error('Enter meter units with at most 3 decimals')
  const [whole, fraction = ''] = value.split('.')
  const result = Number(whole) * 1000 + Number(fraction.padEnd(3,'0'))
  if (!Number.isSafeInteger(result)) throw new Error('Meter reading exceeds safe numeric range')
  return result
}
const units = value => (Number(value || 0) / 1000).toLocaleString('en-UG', {maximumFractionDigits:3})
const mayManage = role => ['OWNER','MANAGER','SUPER_ADMIN'].includes(role)
const mayRead = role => mayManage(role) || role === 'CARETAKER'

export default function UtilitiesPage({role}) {
  const [meters,setMeters] = useState([])
  const [rooms,setRooms] = useState([])
  const [invoices,setInvoices] = useState([])
  const [chosen,setChosen] = useState('')
  const [readings,setReadings] = useState([])
  const [create,setCreate] = useState({room_id:'',kind:'WATER',tariff_ugx_per_unit:'',baseline:'0'})
  const [reading,setReading] = useState({observed_on:'',current:'0'})
  const [bill,setBill] = useState({reading_id:'',invoice_id:''})
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [message,setMessage] = useState('')

  const refresh=useCallback(async () => {
    const result=await api('utilities/meters?page_size=100')
    setMeters(result.items || [])
  },[])
  useEffect(() => {
    refresh().catch(e => setError(errorText(e)))
    if (mayManage(role)) api('rooms?page_size=100').then(r => setRooms(r.items || [])).catch(() => {})
    if (['OWNER','ACCOUNTANT','SUPER_ADMIN'].includes(role)) api('invoices?page_size=100')
      .then(r => setInvoices((r.items || []).filter(i => i.status === 'ISSUED' && !Number(i.paid_ugx) && !Number(i.credit_ugx))))
      .catch(() => {})
  },[refresh,role])
  useEffect(() => {
    if (!chosen) {setReadings([]);return}
    api('utilities/meters/' + encodeURIComponent(chosen) + '/readings?page_size=100')
      .then(r => setReadings(r.items || []))
      .catch(e => setError(errorText(e)))
  },[chosen])

  const submit=async (event,action) => {
    event.preventDefault()
    setBusy(true);setError('');setMessage('')
    try {
      if (action === 'meter') {
        await api('utilities/meters',{method:'POST',body:JSON.stringify({
          room_id:create.room_id,kind:create.kind,
          tariff_ugx_per_unit:Number(create.tariff_ugx_per_unit),
          baseline_milli_units:milli(create.baseline)
        })})
        setMessage('Utility meter registered. Rate should match the applicable tenancy terms.')
        await refresh()
      } else if (action === 'reading') {
        await api('utilities/meters/' + encodeURIComponent(chosen) + '/readings',
          {method:'POST',body:JSON.stringify({
            observed_on:reading.observed_on,current_milli_units:milli(reading.current),
            idempotency_key:crypto.randomUUID()
          })})
        setMessage('Reading recorded. No invoice has been charged yet.')
        const r=await api('utilities/meters/' + encodeURIComponent(chosen) + '/readings?page_size=100')
        setReadings(r.items || [])
      } else {
        await api('utilities/readings/' + encodeURIComponent(bill.reading_id) + '/apply',
          {method:'POST',body:JSON.stringify({invoice_id:bill.invoice_id})})
        setMessage('Reviewed utility charge added once to the unpaid invoice.')
        const r=await api('utilities/meters/' + encodeURIComponent(chosen) + '/readings?page_size=100')
        setReadings(r.items || [])
      }
    } catch (e) {setError(errorText(e))}
    finally {setBusy(false)}
  }
  const selectedMeter=meters.find(m => m.id === chosen)
  return <section className="page">
    <span className="eyebrow">APARTMENT OPERATIONS</span>
    <h1>Water and electricity</h1>
    <p>Auditable meter history. Readings do not become charges until independently reviewed against an unpaid invoice. Numbers are in kWh or m³.</p>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {mayManage(role) && <form className="resource-form" onSubmit={e => submit(e,'meter')}>
      <h2>Register utility meter</h2><div className="fields">
        <label>Room<select required value={create.room_id} onChange={e=>setCreate({...create,room_id:e.target.value})}>
          <option value="">Select room</option>{rooms.map(r=><option key={r.id} value={r.id}>{r.number}</option>)}
        </select></label>
        <label>Utility<select value={create.kind} onChange={e=>setCreate({...create,kind:e.target.value})}><option>WATER</option><option>ELECTRICITY</option></select></label>
        <label>Tariff UGX per unit<input type="number" min="1" required value={create.tariff_ugx_per_unit} onChange={e=>setCreate({...create,tariff_ugx_per_unit:e.target.value})}/></label>
        <label>Starting meter units<input type="number" min="0" step="0.001" required value={create.baseline} onChange={e=>setCreate({...create,baseline:e.target.value})}/></label>
      </div><button disabled={busy} className="button">{busy?'Saving…':'Register meter'}</button>
    </form>}
    <h2>Meter history</h2>
    <label>Meter<select value={chosen} onChange={e=>setChosen(e.target.value)}>
      <option value="">Select registered meter</option>
      {meters.map(m=><option key={m.id} value={m.id}>{m.kind} · {m.room_id} · {money(m.tariff_ugx_per_unit)}/unit</option>)}
    </select></label>
    {selectedMeter && <p>Approved tariff: {money(selectedMeter.tariff_ugx_per_unit)} per unit. Baseline: {units(selectedMeter.baseline_milli_units)}.</p>}
    {mayRead(role) && chosen && <form className="resource-form" onSubmit={e=>submit(e,'reading')}>
      <h2>Record meter reading</h2><div className="fields">
        <label>Reading date<input type="date" required value={reading.observed_on} onChange={e=>setReading({...reading,observed_on:e.target.value})}/></label>
        <label>Current meter units<input type="number" step="0.001" min="0" required value={reading.current} onChange={e=>setReading({...reading,current:e.target.value})}/></label>
      </div><button disabled={busy} className="button">{busy?'Recording…':'Record reading'}</button>
    </form>}
    {chosen && <div className="data-table-wrap"><table><thead><tr><th>Date</th><th>Previous</th><th>Current</th><th>Used</th><th>Charge</th><th>State</th></tr></thead>
      <tbody>{readings.map(r=><tr key={r.id}><td>{r.observed_on}</td><td>{units(r.previous_milli_units)}</td>
      <td>{units(r.current_milli_units)}</td><td>{units(r.used_milli_units)}</td><td>{money(r.charge_ugx)}</td>
      <td>{r.invoice_line_id?'Billed':'Awaiting review'}</td></tr>)}</tbody></table>
      {!readings.length && <p>No meter readings recorded.</p>}
    </div>}
    {['OWNER','ACCOUNTANT','SUPER_ADMIN'].includes(role) && chosen && <form className="resource-form" onSubmit={e=>submit(e,'bill')}>
      <h2>Approve a utility charge</h2><p>Requires a different reviewer from the staff member who recorded the reading.</p>
      <div className="fields">
        <label>Unbilled reading<select required value={bill.reading_id} onChange={e=>setBill({...bill,reading_id:e.target.value})}>
          <option value="">Choose reading</option>{readings.filter(r=>!r.invoice_line_id && Number(r.charge_ugx)>0).map(r=><option key={r.id} value={r.id}>{r.observed_on} · {money(r.charge_ugx)}</option>)}
        </select></label>
        <label>Unpaid covering invoice<select required value={bill.invoice_id} onChange={e=>setBill({...bill,invoice_id:e.target.value})}>
          <option value="">Choose invoice</option>{invoices.map(i=><option key={i.id} value={i.id}>{i.invoice_number} · {i.period_start} to {i.period_end}</option>)}
        </select></label>
      </div><button disabled={busy} className="button">{busy?'Applying…':'Approve and add charge'}</button>
    </form>}
  </section>
}
