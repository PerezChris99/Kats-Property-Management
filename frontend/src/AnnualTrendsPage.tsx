import {useEffect,useState} from 'react'
import {api} from './lib/api'
type Monthly={month:string;label:string;verified_collections_ugx:number;net_invoiced_ugx:number;
  approved_expenses_incurred_ugx:number}
type Totals={verified_collections_ugx:number;net_invoiced_ugx:number;approved_expenses_incurred_ugx:number}
type Response={year:number;points:Monthly[];totals:Totals;
  legacy_verified_without_settlement_date_ugx:number;methodology:string}
const money=(x:number)=>'UGX '+x.toLocaleString('en-UG')
const H=280,TOP=22,BOTTOM=40,LEFT=28,BAR=16,GROUP=76
const COLORS={verified:'#38BDF8',invoiced:'#0B1B3D',expense:'#E2B93B'}
export function AnnualTrendsPage(){
  const [year,setYear]=useState(new Date().getFullYear())
  const [data,setData]=useState<Response|null>(null)
  const [error,setError]=useState('')
  const [busy,setBusy]=useState(true)
  useEffect(()=>{
    let active=true
    setBusy(true);setError('')
    api('reports/annual-trends?year='+year).then(r=>{if(active)setData(r)})
      .catch(e=>{if(active){setError(e instanceof Error?e.message:'Unable to load trends');setData(null)}})
      .finally(()=>{if(active)setBusy(false)})
    return()=>{active=false}
  },[year])
  const points=data?.points||[]
  const max=Math.max(1,...points.flatMap(p=>[
    p.net_invoiced_ugx,p.verified_collections_ugx,p.approved_expenses_incurred_ugx]))
  const height=(v:number)=>Math.max(0,(H-TOP-BOTTOM)*v/max)
  const y=(v:number)=>H-BOTTOM-height(v)
  return <section className="page">
    <span className="eyebrow">FINANCIAL PERFORMANCE</span><h1>Annual performance trends</h1>
    <p>Dynamic verified collections, net invoiced rent and independently approved expenses. These are separate accounting measures, not a cashflow statement.</p>
    <label style={{maxWidth:220}}>Reporting year<input type="number" min="2000" max="2099" step="1"
      value={year} onChange={e=>setYear(Number(e.target.value))}/></label>
    {busy&&<p role="status">Calculating report…</p>}
    {error&&<p role="alert" className="error">{error}</p>}
    {data&&!busy&&<>
      <div className="stat-grid">
        <div className="stat"><small>Net invoiced</small><strong>{money(data.totals.net_invoiced_ugx)}</strong></div>
        <div className="stat"><small>Verified collections</small><strong>{money(data.totals.verified_collections_ugx)}</strong></div>
        <div className="stat"><small>Approved expenses (incurred)</small><strong>{money(data.totals.approved_expenses_incurred_ugx)}</strong></div>
      </div>
      <div className="module-card"><h2>Monthly financial performance</h2>
        <p><span style={{color:COLORS.invoiced}}>■</span> Net invoiced &nbsp;
          <span style={{color:COLORS.verified}}>■</span> Verified collections &nbsp;
          <span style={{color:COLORS.expense}}>■</span> Approved expenses</p>
        <div style={{overflowX:'auto'}}>
          <svg viewBox="0 0 980 290" width="100%" height="290" role="img" aria-label={'Monthly bar chart for '+data.year}>
            <line x1={LEFT} y1={H-BOTTOM} x2="965" y2={H-BOTTOM} stroke="#94A3B8" strokeWidth="1"/>
            {points.map((p,i)=>{
              const x=LEFT+i*GROUP
              return <g key={p.month}>
                <rect x={x+2} y={y(p.net_invoiced_ugx)} width={BAR} height={height(p.net_invoiced_ugx)} fill={COLORS.invoiced}/>
                <rect x={x+20} y={y(p.verified_collections_ugx)} width={BAR} height={height(p.verified_collections_ugx)} fill={COLORS.verified}/>
                <rect x={x+38} y={y(p.approved_expenses_incurred_ugx)} width={BAR} height={height(p.approved_expenses_incurred_ugx)} fill={COLORS.expense}/>
                <text x={x+26} y={H-13} textAnchor="middle" fill="currentColor" fontSize="14">{p.label}</text>
                <title>{p.label}: invoices {money(p.net_invoiced_ugx)}, collections {money(p.verified_collections_ugx)}, expenses {money(p.approved_expenses_incurred_ugx)}</title>
              </g>
            })}
          </svg>
        </div>
      </div>
      <div className="module-card"><h2>Collection trend</h2><p>The line uses the verified settlement date. Reversed and undated legacy payments are excluded.</p>
        <div style={{overflowX:'auto'}}><svg viewBox="0 0 980 290" width="100%" height="290" role="img"
          aria-label={'Verified collection line chart for '+data.year}>
          <line x1={LEFT} y1={H-BOTTOM} x2="965" y2={H-BOTTOM} stroke="#94A3B8" strokeWidth="1"/>
          <polyline points={points.map((p,i)=>(LEFT+i*GROUP+32)+','+y(p.verified_collections_ugx)).join(' ')}
            fill="none" stroke={COLORS.verified} strokeWidth="3" strokeLinejoin="round"/>
          {points.map((p,i)=><g key={p.month}>
            <circle cx={LEFT+i*GROUP+32} cy={y(p.verified_collections_ugx)} r="5" fill={COLORS.invoiced}/>
            <text x={LEFT+i*GROUP+32} y={H-13} textAnchor="middle" fontSize="14" fill="currentColor">{p.label}</text>
            <title>{p.month}: {money(p.verified_collections_ugx)}</title>
          </g>)}
        </svg></div>
      </div>
      <h2>Monthly values</h2>
      <div className="data-table-wrap"><table><thead><tr><th>Month</th><th>Net invoiced</th><th>Verified collections</th><th>Approved incurred costs</th></tr></thead>
        <tbody>{points.map(p=><tr key={p.month}><td>{p.month}</td><td>{money(p.net_invoiced_ugx)}</td>
          <td>{money(p.verified_collections_ugx)}</td><td>{money(p.approved_expenses_incurred_ugx)}</td></tr>)}</tbody>
      </table></div>
      {data.legacy_verified_without_settlement_date_ugx>0&&
        <p role="status">Historical reconciled payments without a trustworthy settlement timestamp:
          {money(data.legacy_verified_without_settlement_date_ugx)} (excluded from monthly chart).</p>}
      <p className="caption">{data.methodology}</p>
    </>}
  </section>
}
