import { useEffect, useState } from 'react';
import { api } from './lib/api';
import { BarChart, LineChart, formatUGX } from './charts/ChartKit';

/** Existing annual API retained. Uses the same SVG chart toolkit as the
 * authenticated dashboards, avoiding a second charting implementation.
 */
export function AnnualTrendsPage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller=new AbortController();
    setBusy(true);setError('');setData(null);
    api('reports/annual-trends?year='+year,{signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted)setData(result);})
      .catch(reason=>{if(!controller.signal.aborted)
        setError(reason instanceof Error?reason.message:'Unable to load annual trends');})
      .finally(()=>{if(!controller.signal.aborted)setBusy(false);});
    return ()=>controller.abort();
  },[year,revision]);
  const rows=data?.points||[];
  const collected=rows.map(p=>({name:p.label,value:p.verified_collections_ugx}));
  const billed=rows.map(p=>({name:p.label,value:p.net_invoiced_ugx}));
  const expenses=rows.map(p=>({name:p.label,value:p.approved_expenses_incurred_ugx}));
  return <section className="page">
    <span className="eyebrow">FINANCIAL PERFORMANCE</span>
    <h1>Annual performance trends</h1>
    <p>Verified collections, net invoiced rent, and approved expenses are separate accounting measures, not a cashflow statement.</p>
    <label className="kats-report-year">Reporting year
      <input type="number" min="2000" max="2099" step="1" value={year}
        onChange={event=>setYear(Number(event.target.value))}/>
    </label>
    {busy && <div className="kats-chart-skeleton" role="status" aria-label="Calculating report"><span/><span/><span/></div>}
    {error && <div className="empty" role="alert"><p>{error}</p>
      <button className="button small" onClick={()=>setRevision(i=>i+1)}>Retry report</button></div>}
    {data && !busy && <><div className="stat-grid">
      <div className="stat"><small>Net invoiced</small><strong>{formatUGX(data.totals.net_invoiced_ugx)}</strong></div>
      <div className="stat"><small>Verified collections</small><strong>{formatUGX(data.totals.verified_collections_ugx)}</strong></div>
      <div className="stat"><small>Approved expenses (incurred)</small><strong>{formatUGX(data.totals.approved_expenses_incurred_ugx)}</strong></div>
    </div>
    <div className="kats-chart-grid">
      <article className="kats-chart-card kats-chart-wide"><h2>Collection trend</h2>
        <LineChart title={'Verified collections for '+data.year} points={collected}/>
      </article>
      <article className="kats-chart-card"><h2>Net invoiced by month</h2>
        <BarChart title={'Net invoiced for '+data.year} points={billed}/>
      </article>
      <article className="kats-chart-card"><h2>Approved expenses by month</h2>
        <BarChart title={'Approved expenses for '+data.year} points={expenses}/>
      </article>
    </div>
    <h2>Monthly values</h2><div className="data-table-wrap"><table>
      <thead><tr><th>Month</th><th>Net invoiced</th><th>Verified collections</th><th>Approved incurred costs</th></tr></thead>
      <tbody>{rows.map(p=><tr key={p.month}><td>{p.month}</td>
        <td>{formatUGX(p.net_invoiced_ugx)}</td>
        <td>{formatUGX(p.verified_collections_ugx)}</td>
        <td>{formatUGX(p.approved_expenses_incurred_ugx)}</td></tr>)}</tbody>
    </table></div>
    {data.legacy_verified_without_settlement_date_ugx>0 && <p role="status">
      Historical reconciled payments without a trustworthy settlement timestamp:
      {formatUGX(data.legacy_verified_without_settlement_date_ugx)} (excluded from monthly charts).
    </p>}
    <p className="caption">{data.methodology}</p>
    </>}
  </section>;
}
