import { useState } from 'react';
import {
  ResponsiveContainer, PieChart as RechartsPieChart, Pie, Cell,
  BarChart as RechartsBarChart, Bar,
  LineChart as RechartsLineChart, Line,
  RadarChart as RechartsRadarChart, Radar,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';

/** One charting library: Recharts 3.10.x, loaded only in account analytics routes.
 * Server-provided aggregates are the ONLY source of production chart values.
 * The chart container sets an explicit height to prevent ResizeObserver loops.
 */
const PALETTE = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#8559A5', '#6D6574'];
const safe = value => Math.max(0, Number(value) || 0);
export const formatUGX = value => 'UGX ' + Number(value || 0).toLocaleString('en-UG');
const formatted = (value, unit) =>
  unit === 'UGX' ? formatUGX(value) : Number(value || 0).toLocaleString('en-UG') +
    (unit === 'percent' ? '%' : '');
const tip = (unit) => value => formatted(value, unit);
const axisNumber = value => {
  const number = Number(value) || 0;
  if (Math.abs(number) >= 1000000) return (number / 1000000).toFixed(1) + 'm';
  if (Math.abs(number) >= 1000) return Math.round(number / 1000) + 'k';
  return number.toLocaleString('en-UG');
};
const prepared = points => points.map(point => ({
  ...point, value: safe(point.value),
  ...(point.secondary === undefined ? {} : { secondary: safe(point.secondary) }),
}));

function ChartFrame({ title, className = '', children }) {
  return <div className={'kats-recharts-frame ' + className}
    role="group" aria-label={title} aria-description="Values are available in an exact-data table.">
    <ResponsiveContainer width="100%" height="100%" minWidth={0}
      initialDimension={{width: 580, height: 240}}>
      {children}
    </ResponsiveContainer>
  </div>;
}

export function DonutChart({ points, unit = 'rooms', title = 'Distribution' }) {
  if (!points.length || !points.some(point => safe(point.value) > 0))
    return <p className="kats-chart-empty" role="status">No recorded values for this period.</p>;
  const values = prepared(points);
  return <div className="kats-chart-donut-layout">
    <ChartFrame title={title} className="kats-donut-frame">
      <RechartsPieChart className="kats-chart-donut" accessibilityLayer>
        <Tooltip formatter={tip(unit)} />
        <Pie data={values} dataKey="value" nameKey="name" innerRadius="57%"
          outerRadius="85%" paddingAngle={1} isAnimationActive={false}>
          {values.map((item, index) =>
            <Cell key={item.name + index} fill={PALETTE[index % PALETTE.length]} />)}
        </Pie>
      </RechartsPieChart>
    </ChartFrame>
    <ul className="kats-chart-legend" aria-label={title + ' exact values'}>
      {values.map((point, index) => <li key={point.name + index}>
        <span className="kats-chart-swatch" aria-hidden="true"
          style={{ backgroundColor: PALETTE[index % PALETTE.length] }}/>
        <span className="kats-chart-name">{point.name}</span>
        <strong>{formatted(point.value, unit)}</strong>
      </li>)}
    </ul>
  </div>;
}

export function BarChart({ points, unit = 'UGX', title = 'Monthly values' }) {
  if (!points.length) return <p className="kats-chart-empty" role="status">No recorded values for this period.</p>;
  const values = prepared(points);
  return <ChartFrame title={title}>
    <RechartsBarChart data={values} className="kats-chart-svg" accessibilityLayer
      margin={{top: 10, right: 12, left: 4, bottom: 18}}>
      <CartesianGrid stroke="#dbe5eb" strokeDasharray="3 5" vertical={false}/>
      <XAxis dataKey="name" tick={{fontSize: 11}} angle={values.length > 7 ? -27 : 0}
        textAnchor={values.length > 7 ? 'end' : 'middle'} interval="preserveStartEnd"
        tickFormatter={value => String(value).length > 14 ? String(value).slice(0, 13) + '…' : value}/>
      <YAxis tick={{fontSize: 11}} width={46} tickFormatter={axisNumber}/>
      <Tooltip formatter={tip(unit)}/>
      <Legend verticalAlign="top" height={30}/>
      <Bar name={unit === 'UGX' ? 'Amount (UGX)' : 'Count'}
        dataKey="value" fill={PALETTE[0]} maxBarSize={52}
        isAnimationActive={false}/>
    </RechartsBarChart>
  </ChartFrame>;
}

export function LineChart({ points, unit = 'UGX', title = 'Monthly trend', secondary = false }) {
  if (!points.length) return <p className="kats-chart-empty" role="status">No recorded values for this period.</p>;
  return <ChartFrame title={title}>
    <RechartsLineChart data={prepared(points)} className="kats-chart-svg"
      accessibilityLayer margin={{top: 8, right: 14, left: 6, bottom: 12}}>
      <CartesianGrid stroke="#dbe5eb" strokeDasharray="3 5"/>
      <XAxis dataKey="name" tick={{fontSize: 11}} interval="preserveStartEnd"/>
      <YAxis tick={{fontSize: 11}} width={48} tickFormatter={axisNumber}/>
      <Tooltip formatter={tip(unit)}/>
      <Legend verticalAlign="top" height={30}/>
      <Line dataKey="value" name={secondary ? 'Verified collections' : 'Value'}
        type="monotone" stroke={PALETTE[0]} strokeWidth={2.5} dot={{r: 3.5}}
        isAnimationActive={false}/>
      {secondary && <Line dataKey="secondary" name="Net invoiced" type="monotone"
        stroke={PALETTE[1]} strokeWidth={2.5} strokeDasharray="5 4"
        dot={{r: 3}} isAnimationActive={false}/>}
    </RechartsLineChart>
  </ChartFrame>;
}

/** An UpSet-style intersection chart instead of a misleading area-proportional
 * Venn. Recharts renders every plotted mark; the matrix exposes memberships.
 */
export function VennChart({ data }) {
  const current = safe(data.current), maintenance = safe(data.maintenance);
  const both = safe(data.both), total = safe(data.total);
  if (!total) return <p className="kats-chart-empty" role="status">No active tenancy records.</p>;
  const intersections = [
    {name: 'Current rent only', value: Math.max(0, current - both), rent: true, maintenance: false},
    {name: 'Both', value: both, rent: true, maintenance: true},
    {name: 'Maintenance only', value: Math.max(0, maintenance - both), rent: false, maintenance: true},
    {name: 'Neither', value: Math.max(0, total - current - maintenance + both), rent: false, maintenance: false},
  ];
  return <div className="kats-upset-layout">
    <ChartFrame title="Rent-current and maintenance intersections">
      <RechartsBarChart data={intersections} className="kats-chart-venn"
        layout="vertical" accessibilityLayer
        margin={{top: 12, right: 18, left: 18, bottom: 6}}>
        <CartesianGrid stroke="#dbe5eb" strokeDasharray="3 5" horizontal={false}/>
        <XAxis type="number" allowDecimals={false} tick={{fontSize: 11}}/>
        <YAxis type="category" dataKey="name" width={110}
          tick={{fontSize: 10}}/>
        <Tooltip formatter={tip('tenants')}/>
        <Legend verticalAlign="top" height={27}/>
        <Bar dataKey="value" name="Active tenants" fill={PALETTE[0]}
          maxBarSize={30} isAnimationActive={false}/>
      </RechartsBarChart>
    </ChartFrame>
    <div className="data-table-wrap">
      <table className="kats-upset-table">
        <caption>Exact set membership (UpSet)</caption>
        <thead><tr><th>Intersection</th><th>Current rent</th><th>Open maintenance</th><th>Tenants</th></tr></thead>
        <tbody>{intersections.map(item => <tr key={item.name}>
          <th scope="row">{item.name}</th>
          <td>{item.rent ? 'Yes' : 'No'}</td>
          <td>{item.maintenance ? 'Yes' : 'No'}</td>
          <td>{item.value}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p className="caption">Memberships count distinct active-lease tenants; groups are exact, not area approximations.</p>
  </div>;
}

export function RadarChart({ points }) {
  const [selected, setSelected] = useState('');
  if (!points.length) return <p className="kats-chart-empty" role="status">No property metrics available yet.</p>;
  const point = points.find(row => (row.id || row.name) === selected) || points[0];
  const axes = [
    {name: 'Occupancy', value: Math.min(100, safe(point.occupancy))},
    {name: 'Collection', value: Math.min(100, safe(point.collection))},
    {name: 'Ticket resolution', value: Math.min(100, safe(point.maintenance))},
  ];
  return <div className="kats-radar-layout">
    <ChartFrame title={'Property score for ' + point.name}>
      <RechartsRadarChart data={axes} className="kats-chart-radar"
        accessibilityLayer outerRadius="68%">
        <PolarGrid stroke="#d5e2e9"/>
        <PolarAngleAxis dataKey="name" tick={{fontSize: 11}}/>
        <PolarRadiusAxis domain={[0, 100]} tick={{fontSize: 10}}/>
        <Tooltip formatter={tip('percent')}/>
        <Legend verticalAlign="top" height={25}/>
        <Radar dataKey="value" name="Recorded rate" stroke={PALETTE[0]}
          fill={PALETTE[0]} fillOpacity={0.2} isAnimationActive={false}/>
      </RechartsRadarChart>
    </ChartFrame>
    <div className="kats-radar-metrics">
      <label>Property
        <select value={point.id || point.name}
          onChange={event => setSelected(event.target.value)}>
          {points.map(row => <option key={row.id || row.name}
            value={row.id || row.name}>{row.name}</option>)}
        </select>
      </label>
      {axes.map(axis => <div key={axis.name}><span>{axis.name}</span><strong>{axis.value}%</strong></div>)}
      <small>No observations are represented as 0%, not inferred performance.</small>
    </div>
  </div>;
}
