import { useEffect, useState } from 'react';
import { api } from './lib/api';
import { Link } from 'react-router-dom';
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
  const [detail, setDetail] = useState({status:'idle',items:[],error:''});
  const inspectMonth = (row, metric) => {
    const labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const index = labels.indexOf(row?.name);
    if (index < 0) return;
    const month = String(year) + '-' + String(index + 1).padStart(2, '0');
    setDetail({status:'loading',items:[],error:'', month,metric});
    const params = new URLSearchParams({month,metric});
    api('analytics/drilldown?' + params.toString())
      .then(response => setDetail({
        status:'ready',items:response.items || [],error:'',
        month, metric,truncated:response.truncated === true,
      }))
      .catch(reason => setDetail({
        status:'error',items:[],error:reason.message || 'Source records unavailable',
      }));
  };
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
  const exportParams = new URLSearchParams({
    months:'12',end_month:String(year) + '-12',
  }).toString();
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
      <a className="outline-button small" target="_blank" rel="noreferrer"
        href={'/api/v1/reports/export/period-summary.pdf?' + exportParams}>Print full-year PDF</a>
      <a className="outline-button small"
        href={'/api/v1/reports/export/period-summary.xlsx?' + exportParams}>Download full-year Excel chart</a>
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
        {collectionStyle === 'line' && <LineChart title={'Verified collections for '+data.year} points={collected} onSelect={point => inspectMonth(point, 'verified_collections')}/>}
        {collectionStyle === 'area' && <AreaChart title={'Verified collections for '+data.year} points={collected} onSelect={point => inspectMonth(point, 'verified_collections')}/>}
        {collectionStyle === 'bar' && <BarChart title={'Verified collections for '+data.year} points={collected} onSelect={point => inspectMonth(point, 'verified_collections')}/>}
      </article>
      <article className="kats-chart-card">
        <div className="kats-chart-header"><h2>Net invoiced by month</h2>
          <label>Display
            <select value={billingStyle} onChange={event => setBillingStyle(event.target.value)}>
              <option value="bar">Columns</option><option value="line">Line</option>
            </select>
          </label>
        </div>
        {billingStyle === 'bar' ? <BarChart title={'Net invoiced for '+data.year} points={billed} onSelect={point => inspectMonth(point, 'net_invoiced')}/>
          : <LineChart title={'Net invoiced for '+data.year} points={billed} onSelect={point => inspectMonth(point, 'net_invoiced')}/>}
      </article>
      <article className="kats-chart-card">
        <div className="kats-chart-header"><h2>Approved expenses by month</h2>
          <label>Display
            <select value={expenseStyle} onChange={event => setExpenseStyle(event.target.value)}>
              <option value="bar">Columns</option><option value="line">Line</option>
            </select>
          </label>
        </div>
        {expenseStyle === 'bar' ? <BarChart title={'Approved expenses for '+data.year} points={expenses} onSelect={point => inspectMonth(point, 'approved_expenses')}/>
          : <LineChart title={'Approved expenses for '+data.year} points={expenses} onSelect={point => inspectMonth(point, 'approved_expenses')}/>}
      </article>
    </div>
    {detail.status !== 'idle' && <section className="kats-drill-results"
      aria-label="Annual report source records">
      <div className="kats-chart-header"><h2>Source records · {detail.month}</h2>
        <button type="button" className="outline-button small"
          onClick={() => setDetail({status:'idle',items:[],error:''})}>Close</button>
      </div>
      {detail.status === 'loading' && <p role="status">Loading authorized records…</p>}
      {detail.status === 'error' && <p role="alert">{detail.error}</p>}
      {detail.status === 'ready' && (!detail.items.length ? <p>No matching source records.</p>
        : <div className="data-table-wrap" role="region" tabIndex={0}
          aria-label="Scrollable annual report source records"><table>
            <thead><tr><th>Source record</th><th>Period / status</th><th>Amount</th></tr></thead>
            <tbody>{detail.items.map((item, index) => <tr key={item.title + index}>
              <th scope="row"><Link to={'/' + item.resource + '?q=' + encodeURIComponent(item.query || '')}>
                {item.title}</Link></th><td>{item.subtitle}</td>
              <td>{item.amount_ugx === undefined ? '—' : formatUGX(item.amount_ugx)}</td>
            </tr>)}</tbody>
          </table></div>)}
      {detail.truncated && <p>Only the latest 25 records are shown here.</p>}
    </section>}
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
    {data.generated_at && <p className="kats-chart-timestamp">
      Report generated: <time dateTime={data.generated_at}>
        {new Date(data.generated_at).toLocaleString('en-UG')}</time>
    </p>}
    <p className="caption">{data.methodology}</p>
    </>}
  </section>;
}
