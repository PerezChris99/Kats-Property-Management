import { useEffect, useState } from 'react';
import { api } from './lib/api';
import { BarChart, LineChart, AreaChart, formatUGX } from './charts/ChartKit';

/** Existing annual API retained. Uses the same SVG chart toolkit as the
 * authenticated dashboards, avoiding a second charting implementation.
 */
export function AnnualTrendsPage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [revision, setRevision] = useState(0);
  const [collectionStyle, setCollectionStyle] = useState('line');
  const [billingStyle, setBillingStyle] = useState('bar');
  const [expenseStyle, setExpenseStyle] = useState('bar');
  const [monthsToShow, setMonthsToShow] = useState('12');
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
  const allRows = Array.isArray(data?.points) ? data.points : [];
  const rows = monthsToShow === 'all' ? allRows : allRows.slice(-Number(monthsToShow));
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
    <div className="kats-report-toolbar">
      <label>Visible months
        <select value={monthsToShow} onChange={event => setMonthsToShow(event.target.value)}>
          <option value="6">Latest 6 months</option>
          <option value="12">Latest 12 months</option>
          <option value="all">All reported months</option>
        </select>
      </label>
      <button className="outline-button small" type="button" disabled={busy}
        onClick={() => setRevision(i => i + 1)}>Refresh report</button>
    </div>
    {busy && <div className="kats-chart-skeleton" role="status" aria-label="Calculating report"><span/><span/><span/></div>}
    {error && <div className="empty" role="alert"><p>{error}</p>
      <button className="button small" onClick={()=>setRevision(i=>i+1)}>Retry report</button></div>}
    {data && !busy && <><div className="stat-grid">
      <div className="stat"><small>Net invoiced</small><strong>{formatUGX(data.totals.net_invoiced_ugx)}</strong></div>
      <div className="stat"><small>Verified collections</small><strong>{formatUGX(data.totals.verified_collections_ugx)}</strong></div>
      <div className="stat"><small>Approved expenses (incurred)</small><strong>{formatUGX(data.totals.approved_expenses_incurred_ugx)}</strong></div>
    </div>
    <div className="kats-chart-grid">
      <article className="kats-chart-card kats-chart-wide">
        <div className="kats-chart-header"><h2>Collection trend — verified settlements</h2>
          <label>Display
            <select value={collectionStyle} onChange={event => setCollectionStyle(event.target.value)}>
              <option value="line">Line graph</option>
              <option value="area">Area graph</option>
              <option value="bar">Column graph</option>
            </select>
          </label>
        </div>
        {collectionStyle === 'line' && <LineChart title={'Verified collections for '+data.year} points={collected}/>}
        {collectionStyle === 'area' && <AreaChart title={'Verified collections for '+data.year} points={collected}/>}
        {collectionStyle === 'bar' && <BarChart title={'Verified collections for '+data.year} points={collected}/>}
      </article>
      <article className="kats-chart-card">
        <div className="kats-chart-header"><h2>Net invoiced by month</h2>
          <label>Display
            <select value={billingStyle} onChange={event => setBillingStyle(event.target.value)}>
              <option value="bar">Columns</option><option value="line">Line</option>
            </select>
          </label>
        </div>
        {billingStyle === 'bar' ? <BarChart title={'Net invoiced for '+data.year} points={billed}/>
          : <LineChart title={'Net invoiced for '+data.year} points={billed}/>}
      </article>
      <article className="kats-chart-card">
        <div className="kats-chart-header"><h2>Approved expenses by month</h2>
          <label>Display
            <select value={expenseStyle} onChange={event => setExpenseStyle(event.target.value)}>
              <option value="bar">Columns</option><option value="line">Line</option>
            </select>
          </label>
        </div>
        {expenseStyle === 'bar' ? <BarChart title={'Approved expenses for '+data.year} points={expenses}/>
          : <LineChart title={'Approved expenses for '+data.year} points={expenses}/>}
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
