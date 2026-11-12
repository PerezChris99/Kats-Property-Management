import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { DonutChart, BarChart, LineChart, VennChart, RadarChart, formatUGX } from './ChartKit';

function PointsTable({ points, unit, kind }) {
  if (kind === 'venn' || kind === 'radar' || !points?.length) return null;
  return <details className="kats-chart-details"><summary>View exact data</summary>
    <div className="data-table-wrap"><table>
      <thead><tr><th>Category / period</th><th>{unit === 'UGX' ? 'Amount (UGX)' : 'Count'}</th>
        {kind === 'monthly-line' && <th>Net invoiced (UGX)</th>}</tr></thead>
      <tbody>{points.map((point,i)=><tr key={point.name+'-'+i}><td>{point.name}</td>
        <td>{unit === 'UGX' ? formatUGX(point.value) : Number(point.value).toLocaleString('en-UG')}</td>
        {kind === 'monthly-line' && <td>{formatUGX(point.secondary)}</td>}</tr>)}</tbody>
    </table></div>
  </details>;
}
export function ChartPanel({ title, endpoint, kind, className = '' }) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({status:'loading',data:null,error:''});
  useEffect(() => {
    const controller = new AbortController();
    setState({status:'loading',data:null,error:''});
    api(endpoint,{signal:controller.signal})
      .then(data => {
        if (!controller.signal.aborted) setState({status:'ready',data,error:''});
      })
      .catch(error=>{
        if (!controller.signal.aborted) setState({
          status:'error',data:null,error:error instanceof Error ? error.message : 'Analytics could not be loaded'
        });
      });
    return () => controller.abort();
  },[endpoint,revision]);
  const data=state.data,points=data?.points||[];
  const empty = (kind === 'venn' ? !data?.total : !points.length);
  return <article className={'kats-chart-card '+className} aria-label={title}>
    <header className="kats-chart-header"><h3>{title}</h3>
      {state.status === 'error' && <button className="button small" onClick={()=>setRevision(v=>v+1)}>Retry</button>}
    </header>
    {state.status === 'loading' && <div className="kats-chart-skeleton" role="status" aria-label={'Loading '+title}>
      <span/><span/><span/>
    </div>}
    {state.status === 'error' && <div className="kats-chart-feedback" role="alert">
      <p>{state.error}</p><p>Other dashboard information remains available.</p>
    </div>}
    {state.status === 'ready' && (empty ?
      <div className="kats-chart-feedback kats-chart-zero" role="status">
        No records available for this chart yet.
      </div> :
      <div className="kats-chart-content">
        {kind === 'donut' && <DonutChart points={points} unit={data.unit} title={title}/>}
        {kind === 'bar' && <BarChart points={points} unit={data.unit} title={title}/>}
        {(kind === 'line' || kind === 'monthly-line') &&
          <LineChart points={points} unit={data.unit} title={title}
            secondary={kind === 'monthly-line'}/>}
        {kind === 'venn' && <VennChart data={data}/>}
        {kind === 'radar' && <RadarChart points={points}/>}
        <PointsTable points={points} unit={data.unit} kind={kind}/>
        {data.method && <p className="kats-chart-method">{data.method}</p>}
      </div>)}
  </article>;
}
export function LandlordAnalytics() {
  return <section className="kats-analytics" aria-label="Live portfolio analytics">
    <div className="kats-analytics-heading"><h2>Portfolio analytics</h2>
      <p>Live operational data from aggregated database queries.</p></div>
    <div className="kats-chart-grid">
      <ChartPanel title="Portfolio occupancy" endpoint="analytics/landlord/occupancy" kind="donut"/>
      <ChartPanel title="Collections by property" endpoint="analytics/landlord/collections-by-property" kind="bar"/>
      <ChartPanel title="Invoicing and verified collections" endpoint="analytics/landlord/monthly" kind="monthly-line" className="kats-chart-wide"/>
      <ChartPanel title="Current rent and maintenance overlap" endpoint="analytics/landlord/tenant-overlap" kind="venn"/>
      <ChartPanel title="Property performance (polar radar)" endpoint="analytics/landlord/property-scores" kind="radar"/>
    </div>
  </section>;
}
export function TenantAnalytics() {
  return <section className="kats-analytics" aria-label="Live rental analytics">
    <div className="kats-analytics-heading"><h2>My rental activity</h2>
      <p>Only invoices and payments connected to your signed-in rental profile.</p></div>
    <div className="kats-chart-grid">
      <ChartPanel title="Invoice payment status" endpoint="analytics/tenant/payment-status" kind="donut"/>
      <ChartPanel title="Payments applied by rent period" endpoint="analytics/tenant/applied-payments" kind="bar"/>
      <ChartPanel title="Cumulative outstanding balance" endpoint="analytics/tenant/balance-trend" kind="line" className="kats-chart-wide"/>
    </div>
  </section>;
}
