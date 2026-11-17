import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import {
  DonutChart, PieChart, BarChart, LineChart, AreaChart, ComparisonBarChart,
  VennChart, PropertyPerformanceChart, formatUGX,
} from './ChartKit';
import { MetricTile, SectionHeading, DataStatus } from '../components/WorkspacePrimitives';
import { PeriodDashboard, financialChartData } from './PresentationControls';

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

const DRILL_METRIC = {
  'analytics/landlord/occupancy': 'occupancy',
  'analytics/landlord/collections-by-property': 'property_collections',
  'analytics/landlord/monthly': 'verified_collections',
  'analytics/landlord/tenant-overlap': 'overlap',
  'analytics/landlord/property-scores': 'property_rooms',
  'analytics/tenant/payment-status': 'payment_status',
  'analytics/tenant/applied-payments': 'applied_payments',
  'analytics/tenant/payment-history': 'verified_collections',
  'analytics/tenant/balance-trend': 'open_invoices',
};
const VENN_GROUPS = ['Current rent only', 'Both', 'Maintenance only', 'Neither'];
const RECORD_ROUTES = new Set(['rooms', 'tenants', 'invoices', 'payments', 'expenses']);
const readableTime = iso => {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null
    : date.toLocaleString('en-UG', { dateStyle: 'medium', timeStyle: 'short' });
};


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

export function ChartPanel({ title, endpoint, kind, className = '', periodView, onPeriodRefresh }) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({ status: 'loading', data: null, error: '' });
  const [selected, setSelected] = useState('');
  const [drillSeries, setDrillSeries] = useState('verified_collections');
  const [details, setDetails] = useState({ status: 'idle', items: [], error: '' });
  const drillRequest = useRef(0);
  const chartRoot = useRef(null);
  const external = periodView !== undefined;
  const options = MODE_OPTIONS[kind] || MODE_OPTIONS.bar;
  const [mode, setMode] = useState(options[0][0]);
  const [range, setRange] = useState('12');
  useEffect(() => {
    if (external) return undefined;
    const controller = new AbortController();
    setState({ status: 'loading', data: null, error: '' });
    api(endpoint,{signal:controller.signal})
      .then(data => {
        if (!validResponse(data, kind)) throw new Error('The analytics response is invalid. Please retry.');
        if (!controller.signal.aborted) setState({ status: 'ready', data, error: '', receivedAt: new Date().toISOString() });
      })
      .catch(error => {
        if (!controller.signal.aborted) setState({
          status: 'error', data: null,
          error: error instanceof Error ? error.message : 'Analytics could not be loaded',
        });
      });
    return () => controller.abort();
  }, [endpoint, revision, kind, external]);

  const active = external
    ? { status: periodView.status, error: periodView.error,
        data: financialChartData(endpoint, periodView.data),
        receivedAt: periodView.data?.generated_at }
    : state;
  const data = active.data;
  const points = data?.points || [];
  const plotted = TIME_SERIES.has(kind) && range !== 'all'
    ? points.slice(-Number(range)) : points;
  const empty = kind === 'venn' ? !data?.total : !points.length;
  const unit = data?.unit || 'UGX';
  const categories = kind === 'venn' ? VENN_GROUPS
    : [...new Set(points.map(row => row.name))];
  const selectedName = categories.includes(selected) ? selected : (categories[0] || '');
  const reportMetric = endpoint === 'analytics/landlord/monthly'
    ? drillSeries : DRILL_METRIC[endpoint];
  const inspect = (point, metricOverride) => {
    const name = point?.name || selectedName;
    if (!name || !reportMetric) return;
    const metric = metricOverride || reportMetric;
    const query = new URLSearchParams({ metric });
    if (/^20\d\d-(0[1-9]|1[0-2])$/.test(name)) query.set('month', name);
    else query.set('category', name);
    const id = ++drillRequest.current;
    setSelected(name);
    setDetails({ status: 'loading', items: [], error: '' });
    api('analytics/drilldown?' + query.toString())
      .then(response => {
        if (id === drillRequest.current) setDetails({
          status: 'ready', items: response.items || [],
          error: '', truncated: response.truncated === true, name,
        });
      })
      .catch(reason => {
        if (id === drillRequest.current) setDetails({
          status: 'error', items: [], error: reason.message || 'Unable to show source records',
        });
      });
  };
  const downloadSvg = () => {
    const source = chartRoot.current?.querySelector('.recharts-wrapper > svg.recharts-surface');
    if (!source) return;
    const svg = source.cloneNode(true);
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', title);
    const file = new Blob([new XMLSerializer().serializeToString(svg)], {
      type: 'image/svg+xml;charset=utf-8',
    });
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'kats-' + title.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.svg';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 100);
  };
  const refresh = () => {
    setDetails({ status: 'idle', items: [], error: '' });
    if (external) onPeriodRefresh?.();
    else setRevision(v=>v+1);
  };

  return <article ref={chartRoot} className={'kats-chart-card ' + className} aria-label={title}>
    <header className="kats-chart-header">
      <div><h3>{title}</h3><span className="kats-chart-subtitle">From live, role-authorized records</span></div>
      <div className="kats-chart-actions">
        {active.status === 'ready' && !empty && <button className="outline-button small"
          type="button" onClick={downloadSvg}>Download SVG</button>}
        <button className="outline-button small" type="button"
          disabled={active.status === 'loading'} onClick={refresh}>Refresh</button>
      </div>
    </header>
    {active.status === 'ready' && !empty && <div className="kats-chart-controls">
      {options.length > 1 && <label>Chart type
        <select value={mode} onChange={event => setMode(event.target.value)}>
          {options.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </label>}
      {TIME_SERIES.has(kind) && !external && points.length > 6 && <label>Period
        <select value={range} onChange={event => setRange(event.target.value)}>
          <option value="6">Latest 6 months</option>
          <option value="12">Latest 12 months</option>
          <option value="all">All returned months</option>
        </select>
      </label>}
    </div>}
    {active.status === 'loading' && <div className="kats-chart-skeleton"
      role="status" aria-label={'Loading ' + title}><span/><span/><span/></div>}
    {active.status === 'error' && <div className="kats-chart-feedback" role="alert">
      <p>{active.error}</p><p>Other dashboard information remains available.</p>
      <button className="outline-button small" type="button"
        onClick={refresh}>Retry chart</button>
    </div>}
    {active.status === 'ready' && (empty
      ? <div className="kats-chart-feedback kats-chart-zero" role="status">
          No source records are available for this chart yet.
        </div>
      : <div className="kats-chart-content">
        {mode === 'donut' && <DonutChart points={plotted} unit={unit} title={title} onSelect={inspect}/>}
        {mode === 'pie' && <PieChart points={plotted} unit={unit} title={title} onSelect={inspect}/>}
        {(mode === 'bar' || mode === 'horizontal') && <BarChart
          points={plotted} unit={unit} title={title} horizontal={mode === 'horizontal'} onSelect={inspect}/>}
        {mode === 'line' && <LineChart points={plotted} unit={unit} title={title}
          secondary={kind === 'monthly-line'} onSelect={inspect}/>}
        {mode === 'area' && <AreaChart points={plotted} unit={unit} title={title} onSelect={inspect}/>}
        {mode === 'compare' && <ComparisonBarChart points={plotted} unit={unit} title={title} onSelect={inspect}/>}
        {mode === 'venn' && <VennChart data={data} onSelect={inspect}/>}
        {mode === 'performance' && <PropertyPerformanceChart points={plotted} title={title} onSelect={inspect}/>}
        <PointsTable points={plotted} unit={unit} kind={kind}/>
        {reportMetric && categories.length > 0 && <div className="kats-drill-controls">
          <label>Explore source records
            <select value={selectedName} onChange={event => setSelected(event.target.value)}>
              {categories.map(name => <option key={name} value={name}>{name}</option>)}
            </select>
          </label>
          {endpoint === 'analytics/landlord/monthly' && <label>Record type
            <select value={drillSeries} onChange={event => setDrillSeries(event.target.value)}>
              <option value="verified_collections">Verified receipts</option>
              <option value="net_invoiced">Net invoices</option>
            </select>
          </label>}
          <button className="outline-button small" type="button"
            onClick={() => inspect({name:selectedName})}>View underlying records</button>
        </div>}
        {details.status === 'loading' && <p role="status">Loading authorized records…</p>}
        {details.status === 'error' && <p role="alert">{details.error}</p>}
        {details.status === 'ready' && <section className="kats-drill-results"
          aria-label={'Source records for ' + details.name}>
          <div className="kats-chart-header">
            <h4>Underlying records · {details.name}</h4>
            <button className="outline-button small" type="button"
              onClick={() => setDetails({status:'idle',items:[],error:''})}>Close</button>
          </div>
          {!details.items.length ? <p>No matching authorized records.</p>
            : <div className="data-table-wrap" role="region" tabIndex={0}
              aria-label="Scrollable chart source records"><table>
                <thead><tr><th>Record</th><th>Details</th><th>Recorded amount</th></tr></thead>
                <tbody>{details.items.map((row, index) => <tr key={row.title + index}>
                  <th scope="row">{RECORD_ROUTES.has(row.resource)
                    ? <Link to={'/' + row.resource + '?q=' + encodeURIComponent(row.query || '')}>{row.title}</Link>
                    : row.title}</th>
                  <td>{row.subtitle}</td>
                  <td>{row.amount_ugx === undefined ? '—' : formatUGX(row.amount_ugx)}</td>
                </tr>)}</tbody>
              </table></div>}
          {details.truncated && <p className="caption">Showing the latest 25 records. Open the source workspace for more.</p>}
        </section>}
        {readableTime(data.generated_at || active.receivedAt) && <p className="kats-chart-timestamp">
          Retrieved: <time dateTime={data.generated_at || active.receivedAt}>
            {readableTime(data.generated_at || active.receivedAt)}</time>
        </p>}
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
    <PeriodDashboard>{(view, refresh) => <>
      <SectionHeading title="Portfolio analytics"
        description="Current occupancy and membership; financial plots share the chosen reporting period."/>
      <div className="kats-chart-grid">
        <ChartPanel title="Portfolio occupancy" endpoint="analytics/landlord/occupancy" kind="donut"/>
        <ChartPanel title="Collections by property (all recorded settlements)"
          endpoint="analytics/landlord/collections-by-property" kind="category-bar"/>
        <ChartPanel title="Invoicing and verified collections"
          endpoint="analytics/landlord/monthly" kind="monthly-line"
          className="kats-chart-wide" periodView={view} onPeriodRefresh={refresh}/>
        <ChartPanel title="Current rent and maintenance overlap"
          endpoint="analytics/landlord/tenant-overlap" kind="venn"/>
        <ChartPanel title="Property performance by metric (all recorded)"
          endpoint="analytics/landlord/property-scores" kind="performance"/>
      </div>
    </>}</PeriodDashboard>
  </section>;
}
export function TenantAnalytics() {
  return <section className="kats-analytics" aria-label="Live rental analytics">
    <SectionHeading title="My rental activity"
      description="Only invoices and verified payments connected to your signed-in rental profile."/>
    <PeriodDashboard>{(view, refresh) => <div className="kats-chart-grid">
      <ChartPanel title="Invoice payment status (current)"
        endpoint="analytics/tenant/payment-status" kind="donut"/>
      <ChartPanel title="Payments applied by rent period"
        endpoint="analytics/tenant/applied-payments" kind="bar"
        periodView={view} onPeriodRefresh={refresh}/>
      <ChartPanel title="Verified payment history"
        endpoint="analytics/tenant/payment-history" kind="line"
        periodView={view} onPeriodRefresh={refresh}/>
      <ChartPanel title="Current outstanding debt by selected billing period"
        endpoint="analytics/tenant/balance-trend" kind="line"
        className="kats-chart-wide" periodView={view} onPeriodRefresh={refresh}/>
    </div>}</PeriodDashboard>
  </section>;
}
