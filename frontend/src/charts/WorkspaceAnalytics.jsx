import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import {
  DonutChart, PieChart, BarChart, LineChart, AreaChart, ComparisonBarChart,
  VennChart, PropertyPerformanceChart, formatUGX,
} from './ChartKit';
import { MetricTile, SectionHeading, DataStatus } from '../components/WorkspacePrimitives';

const MODE_OPTIONS = {
  donut: [['donut', 'Doughnut'], ['pie', 'Pie']],
  'category-bar': [['horizontal', 'Horizontal bars'], ['bar', 'Columns']],
  bar: [['bar', 'Columns'], ['line', 'Line'], ['area', 'Area']],
  line: [['line', 'Line'], ['area', 'Area'], ['bar', 'Columns']],
  'monthly-line': [['line', 'Lines'], ['compare', 'Grouped columns'], ['area', 'Collections area']],
  venn: [['venn', 'Intersection bars']],
  performance: [['performance', 'Percentage bars']],
};
const TIME_SERIES = new Set(['bar', 'line', 'monthly-line']);

function PointsTable({ points, unit, kind }) {
  if (kind === 'venn' || kind === 'performance' || !points?.length) return null;
  return <details className="kats-chart-details"><summary>View exact data</summary>
    <div className="data-table-wrap"><table>
      <thead><tr><th>Category / period</th>
        <th>{unit === 'UGX' ? 'Recorded amount (UGX)' : 'Recorded count'}</th>
        {kind === 'monthly-line' && <th>Net invoiced (UGX)</th>}</tr></thead>
      <tbody>{points.map((point, i) => <tr key={point.name + '-' + i}>
        <th scope="row">{point.name}</th>
        <td>{unit === 'UGX' ? formatUGX(point.value) : Number(point.value).toLocaleString('en-UG')}</td>
        {kind === 'monthly-line' && <td>{formatUGX(point.secondary)}</td>}
      </tr>)}</tbody>
    </table></div>
  </details>;
}

function validResponse(data, kind) {
  if (!data || typeof data !== 'object') return false;
  if (kind === 'venn') return ['current', 'maintenance', 'both', 'total']
    .every(key => Number.isFinite(Number(data[key])) && Number(data[key]) >= 0);
  if (!Array.isArray(data.points)) return false;
  return data.points.every(point => point && typeof point.name === 'string' &&
    (kind === 'performance'
      ? ['occupancy', 'collection', 'maintenance'].every(key =>
        Number.isFinite(Number(point[key])) && Number(point[key]) >= 0)
      : Number.isFinite(Number(point.value)) &&
        (kind !== 'monthly-line' || Number.isFinite(Number(point.secondary)))));
}

export function ChartPanel({ title, endpoint, kind, className = '' }) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({ status: 'loading', data: null, error: '' });
  const options = MODE_OPTIONS[kind] || MODE_OPTIONS.bar;
  const [mode, setMode] = useState(options[0][0]);
  const [range, setRange] = useState('12');
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading', data: null, error: '' });
    api(endpoint,{signal:controller.signal})
      .then(data => {
        if (!validResponse(data, kind)) throw new Error('The analytics response is invalid. Please retry.');
        if (!controller.signal.aborted) setState({ status: 'ready', data, error: '' });
      })
      .catch(error => {
        if (!controller.signal.aborted) setState({
          status: 'error', data: null,
          error: error instanceof Error ? error.message : 'Analytics could not be loaded',
        });
      });
    return () => controller.abort();
  }, [endpoint, revision, kind]);

  const data = state.data;
  const points = data?.points || [];
  const plotted = TIME_SERIES.has(kind) && range !== 'all'
    ? points.slice(-Number(range)) : points;
  const empty = kind === 'venn' ? !data?.total : !points.length;
  const unit = data?.unit || 'UGX';

  return <article className={'kats-chart-card ' + className} aria-label={title}>
    <header className="kats-chart-header">
      <div><h3>{title}</h3><span className="kats-chart-subtitle">From live, role-authorized records</span></div>
      <button className="outline-button small" type="button"
        disabled={state.status === 'loading'} onClick={() => setRevision(v=>v+1)}>
        Refresh
      </button>
    </header>
    {state.status === 'ready' && !empty && <div className="kats-chart-controls">
      {options.length > 1 && <label>Chart type
        <select value={mode} onChange={event => setMode(event.target.value)}>
          {options.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </label>}
      {TIME_SERIES.has(kind) && points.length > 6 && <label>Period
        <select value={range} onChange={event => setRange(event.target.value)}>
          <option value="6">Latest 6 months</option>
          <option value="12">Latest 12 months</option>
          <option value="all">All returned months</option>
        </select>
      </label>}
    </div>}
    {state.status === 'loading' && <div className="kats-chart-skeleton"
      role="status" aria-label={'Loading ' + title}><span/><span/><span/></div>}
    {state.status === 'error' && <div className="kats-chart-feedback" role="alert">
      <p>{state.error}</p><p>Other dashboard information remains available.</p>
      <button className="outline-button small" type="button"
        onClick={() => setRevision(v=>v+1)}>Retry chart</button>
    </div>}
    {state.status === 'ready' && (empty
      ? <div className="kats-chart-feedback kats-chart-zero" role="status">
          No source records are available for this chart yet.
        </div>
      : <div className="kats-chart-content">
        {mode === 'donut' && <DonutChart points={plotted} unit={unit} title={title}/>}
        {mode === 'pie' && <PieChart points={plotted} unit={unit} title={title}/>}
        {(mode === 'bar' || mode === 'horizontal') && <BarChart
          points={plotted} unit={unit} title={title} horizontal={mode === 'horizontal'}/>}
        {mode === 'line' && <LineChart points={plotted} unit={unit} title={title}
          secondary={kind === 'monthly-line'}/>}
        {mode === 'area' && <AreaChart points={plotted} unit={unit} title={title}/>}
        {mode === 'compare' && <ComparisonBarChart points={plotted} unit={unit} title={title}/>}
        {mode === 'venn' && <VennChart data={data}/>}
        {mode === 'performance' && <PropertyPerformanceChart points={plotted} title={title}/>}
        <PointsTable points={plotted} unit={unit} kind={kind}/>
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
      <ChartPanel title="Collections by property" endpoint="analytics/landlord/collections-by-property" kind="category-bar"/>
      <ChartPanel title="Invoicing and verified collections" endpoint="analytics/landlord/monthly" kind="monthly-line" className="kats-chart-wide"/>
      <ChartPanel title="Current rent and maintenance overlap" endpoint="analytics/landlord/tenant-overlap" kind="venn"/>
      <ChartPanel title="Property performance (polar radar)" endpoint="analytics/landlord/property-scores" kind="performance"/>
    </div>
  </section>;
}
export function TenantAnalytics() {
  return <section className="kats-analytics" aria-label="Live rental analytics">
    <SectionHeading title="My rental activity" description="Only invoices and verified payments connected to your signed-in rental profile."/>
    <div className="kats-chart-grid">
      <ChartPanel title="Invoice payment status" endpoint="analytics/tenant/payment-status" kind="donut"/>
      <ChartPanel title="Payments applied by rent period" endpoint="analytics/tenant/applied-payments" kind="time-bar"/>
      <ChartPanel title="Verified payment history" endpoint="analytics/tenant/payment-history" kind="line"/>
      <ChartPanel title="Cumulative outstanding balance" endpoint="analytics/tenant/balance-trend" kind="line" className="kats-chart-wide"/>
    </div>
  </section>;
}
