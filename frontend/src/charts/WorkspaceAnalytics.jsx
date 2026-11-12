import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { DonutChart, BarChart, LineChart, VennChart, RadarChart, formatUGX } from './ChartKit';
import { MetricTile, SectionHeading, DataStatus } from '../components/WorkspacePrimitives';

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
        if (!data || typeof data !== 'object' ||
            (kind !== 'venn' && !Array.isArray(data.points)) ||
            (kind === 'venn' && !Number.isFinite(Number(data.total)))) {
          throw new Error('The analytics response is invalid. Please retry.');
        }
        if (!controller.signal.aborted) setState({status:'ready',data,error:''});
      })
      .catch(error=>{
        if (!controller.signal.aborted) setState({
          status:'error',data:null,error:error instanceof Error ? error.message : 'Analytics could not be loaded'
        });
      });
    return () => controller.abort();
  },[endpoint,revision,kind]);
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
function PortfolioMetrics() {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({status:'loading', data:null, error:''});
  useEffect(() => {
    const controller = new AbortController();
    setState({status:'loading', data:null, error:''});
    api('analytics/landlord/portfolio', {signal:controller.signal})
      .then(data => {
        if (!Array.isArray(data?.points)) throw new Error('Invalid portfolio response');
        if (!controller.signal.aborted) setState({status:'ready', data, error:''});
      })
      .catch(error => { if (!controller.signal.aborted)
        setState({status:'error', data:null, error:error.message || 'Could not load portfolio'}); });
    return () => controller.abort();
  }, [revision]);
  const points = state.data?.points || [];
  const total = key => points.reduce((sum, point) => sum + Number(point[key] || 0), 0);
  return <section className="kats-portfolio-summary" aria-label="Property overview">
    <SectionHeading title="Portfolio snapshot"
      description="Recorded property and unit totals, refreshed directly from the database."/>
    {state.status === 'loading' && <DataStatus mode="loading" label="Portfolio"/>}
    {state.status === 'error' && <DataStatus mode="error" label="Portfolio"
      error={state.error} onRetry={() => setRevision(value=>value+1)}/>}
    {state.status === 'ready' && (points.length === 0
      ? <DataStatus mode="empty" label="Portfolio"/>
      : <div className="stat-grid">
          <MetricTile label="Properties" value={points.length.toLocaleString('en-UG')}/>
          <MetricTile label="Units" value={total('value').toLocaleString('en-UG')}/>
          <MetricTile label="Occupied" value={total('occupied').toLocaleString('en-UG')}/>
          <MetricTile label="Vacant" value={total('vacant').toLocaleString('en-UG')}/>
        </div>)}
    {state.status === 'ready' && points.length > 0 && <details className="kats-chart-details">
      <summary>Property-by-property unit totals</summary>
      <div className="data-table-wrap"><table>
        <thead><tr><th>Property</th><th>District</th><th>Units</th><th>Occupied</th><th>Vacant</th></tr></thead>
        <tbody>{points.map(point => <tr key={point.id}>
          <td>{point.name}</td><td>{point.district}</td><td>{point.value}</td>
          <td>{point.occupied}</td><td>{point.vacant}</td>
        </tr>)}</tbody>
      </table></div>
    </details>}
  </section>;
}

export function LandlordAnalytics() {
  return <section className="kats-analytics" aria-label="Live portfolio analytics">
    <PortfolioMetrics/>
    <SectionHeading title="Portfolio analytics" description="Live operational data from aggregated database queries."/>
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
    <SectionHeading title="My rental activity" description="Only invoices and verified payments connected to your signed-in rental profile."/>
    <div className="kats-chart-grid">
      <ChartPanel title="Invoice payment status" endpoint="analytics/tenant/payment-status" kind="donut"/>
      <ChartPanel title="Payments applied by rent period" endpoint="analytics/tenant/applied-payments" kind="bar"/>
      <ChartPanel title="Verified payment history" endpoint="analytics/tenant/payment-history" kind="bar"/>
      <ChartPanel title="Cumulative outstanding balance" endpoint="analytics/tenant/balance-trend" kind="line" className="kats-chart-wide"/>
    </div>
  </section>;
}
