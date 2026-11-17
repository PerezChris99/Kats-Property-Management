import { useState } from 'react';
import {
  ResponsiveContainer, PieChart as RechartsPieChart, Pie, Cell,
  BarChart as RechartsBarChart, Bar,
  LineChart as RechartsLineChart, Line,
  AreaChart as RechartsAreaChart, Area,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend,
} from 'recharts';

/**
 * Responsive chart primitives used by OWNER/MANAGER/ACCOUNTANT and TENANT.
 * Values come solely from authenticated SQL-backed analytics endpoints.
 * Do not turn missing measurements into invented growth or financial data.
 */
const PALETTE = ['#1277A8', '#D8A42E', '#168777', '#976FC1', '#CA654C', '#52768F', '#78845A'];
const number = value => Number.isFinite(Number(value)) ? Number(value) : 0;
const positive = value => Math.max(0, number(value));
export const formatUGX = value => 'UGX ' + number(value).toLocaleString('en-UG');
const formatValue = (value, unit) => unit === 'UGX'
  ? formatUGX(value)
  : number(value).toLocaleString('en-UG') + (unit === 'percent' ? '%' : '');
const compact = value => {
  const amount = number(value);
  const abs = Math.abs(amount);
  if (abs >= 1_000_000_000) return (amount / 1_000_000_000).toFixed(1) + 'b';
  if (abs >= 1_000_000) return (amount / 1_000_000).toFixed(1) + 'm';
  if (abs >= 1_000) return (amount / 1_000).toFixed(1) + 'k';
  return amount.toLocaleString('en-UG');
};
const normalise = points => points.map(item => ({
  ...item,
  value: number(item.value),
  ...(item.secondary === undefined ? {} : { secondary: number(item.secondary) }),
}));
const shortLabel = value => {
  const label = String(value ?? '');
  return label.length > 14 ? label.slice(0, 13) + '…' : label;
};
const tooltip = unit => (value, name) => [formatValue(value, unit), name];

function EmptyChart({ label = 'No recorded values for this period.' }) {
  return <div className="kats-chart-empty" role="status">{label}</div>;
}

/** The container, not the SVG, owns sizing; never apply a max-height to Recharts SVG. */
function ChartFrame({ title, className = '', children }) {
  return <div className={'kats-recharts-frame ' + className} role="group"
    aria-label={title} aria-description="The exact values are available in a data table.">
    <ResponsiveContainer width="100%" height="100%" minWidth={0}
      initialDimension={{ width: 560, height: 300 }}>
      {children}
    </ResponsiveContainer>
  </div>;
}
function ChartAxes({ unit, vertical = false, points = [] }) {
  if (vertical) return <>
    <CartesianGrid stroke="#e3eaf0" strokeDasharray="3 5" horizontal={false}/>
    <XAxis type="number" tickFormatter={compact} tick={{ fontSize: 11 }}
      allowDecimals={unit === 'UGX' || unit === 'percent'}/>
    <YAxis type="category" dataKey="name" width={112} tick={{ fontSize: 11 }}
      tickFormatter={shortLabel} interval={0}/>
  </>;
  return <>
    <CartesianGrid stroke="#e3eaf0" strokeDasharray="3 5" vertical={false}/>
    <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false}
      interval={points.length > 10 ? 'preserveStartEnd' : 0}
      minTickGap={8} tickFormatter={shortLabel}/>
    <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} tickLine={false}
      axisLine={false} width={55}
      allowDecimals={unit === 'UGX' || unit === 'percent'}/>
  </>;
}

function DistributionChart({ points, unit, title, donut }) {
  if (!points?.length || !points.some(row => positive(row.value) > 0))
    return <EmptyChart/>;
  const values = points.map(item => ({ ...item, value: positive(item.value) }));
  const total = values.reduce((sum, item) => sum + item.value, 0);
  return <div className="kats-chart-donut-layout">
    <ChartFrame title={title} className="kats-donut-frame">
      <RechartsPieChart accessibilityLayer>
        <Tooltip formatter={tooltip(unit)}/>
        <Pie data={values} dataKey="value" nameKey="name"
          innerRadius={donut ? '53%' : 0} outerRadius="80%"
          paddingAngle={values.length > 1 ? 2 : 0}
          stroke="#fff" strokeWidth={2} isAnimationActive={false}>
          {values.map((item, i) => <Cell key={item.name + i}
            fill={PALETTE[i % PALETTE.length]}/>)}
        </Pie>
      </RechartsPieChart>
    </ChartFrame>
    <ul className="kats-chart-legend" aria-label={title + ' recorded values'}>
      {values.map((item, i) => <li key={item.name + i}>
        <span className="kats-chart-swatch" aria-hidden="true"
          style={{ backgroundColor: PALETTE[i % PALETTE.length] }}/>
        <span className="kats-chart-name">{item.name}
          <small> ({(item.value * 100 / total).toFixed(1)}%)</small></span>
        <strong>{formatValue(item.value, unit)}</strong>
      </li>)}
    </ul>
  </div>;
}
export function DonutChart({ points, unit = 'rooms', title = 'Distribution' }) {
  return <DistributionChart points={points} unit={unit} title={title} donut/>;
}
export function PieChart({ points, unit = 'rooms', title = 'Distribution' }) {
  return <DistributionChart points={points} unit={unit} title={title} donut={false}/>;
}

export function BarChart({ points, unit = 'UGX', title = 'Values', horizontal = false }) {
  if (!points?.length) return <EmptyChart/>;
  const values = normalise(points);
  return <ChartFrame title={title}>
    <RechartsBarChart data={values} layout={horizontal ? 'vertical' : 'horizontal'}
      accessibilityLayer margin={horizontal
        ? { top: 8, right: 20, bottom: 12, left: 6 }
        : { top: 8, right: 15, bottom: 12, left: 0 }}>
      <ChartAxes points={values} unit={unit} vertical={horizontal}/>
      <Tooltip formatter={tooltip(unit)} cursor={{ fill: '#eef5f9' }}/>
      <Legend verticalAlign="top" height={32}/>
      <Bar name={unit === 'UGX' ? 'Recorded amount' : unit === 'percent' ? 'Rate' : 'Recorded count'}
        dataKey="value" fill={PALETTE[0]} maxBarSize={56} radius={horizontal ? [0, 5, 5, 0] : [5, 5, 0, 0]}
        isAnimationActive={false}/>
    </RechartsBarChart>
  </ChartFrame>;
}

/** Two genuine independent accounting series displayed side by side, never stacked. */
export function ComparisonBarChart({ points, unit = 'UGX', title = 'Collection and invoicing' }) {
  if (!points?.length) return <EmptyChart/>;
  const values = normalise(points);
  return <ChartFrame title={title}>
    <RechartsBarChart data={values} accessibilityLayer
      margin={{ top: 12, right: 18, bottom: 14, left: 0 }}>
      <ChartAxes points={values} unit={unit}/>
      <Tooltip formatter={tooltip(unit)} cursor={{ fill: '#eef5f9' }}/>
      <Legend verticalAlign="top" height={32}/>
      <Bar name="Verified collections" dataKey="value" fill={PALETTE[0]}
        maxBarSize={32} radius={[4, 4, 0, 0]} isAnimationActive={false}/>
      <Bar name="Net invoiced" dataKey="secondary" fill={PALETTE[1]}
        maxBarSize={32} radius={[4, 4, 0, 0]} isAnimationActive={false}/>
    </RechartsBarChart>
  </ChartFrame>;
}

export function LineChart({ points, unit = 'UGX', title = 'Trend', secondary = false }) {
  if (!points?.length) return <EmptyChart/>;
  const values = normalise(points);
  return <ChartFrame title={title}>
    <RechartsLineChart data={values} accessibilityLayer
      margin={{ top: 12, right: 20, bottom: 14, left: 0 }}>
      <ChartAxes points={values} unit={unit}/>
      <Tooltip formatter={tooltip(unit)}/>
      <Legend verticalAlign="top" height={32}/>
      <Line type="linear" dataKey="value" name={secondary ? 'Verified collections' : 'Recorded value'}
        stroke={PALETTE[0]} strokeWidth={3} strokeLinecap="round"
        dot={{ r: 3.5, strokeWidth: 1.5 }} activeDot={{ r: 6 }}
        connectNulls={false} isAnimationActive={false}/>
      {secondary && <Line type="linear" dataKey="secondary" name="Net invoiced"
        stroke={PALETTE[1]} strokeWidth={2.5} strokeDasharray="6 4"
        dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls={false}
        isAnimationActive={false}/>}
    </RechartsLineChart>
  </ChartFrame>;
}

export function AreaChart({ points, unit = 'UGX', title = 'Trend' }) {
  if (!points?.length) return <EmptyChart/>;
  return <ChartFrame title={title}>
    <RechartsAreaChart data={normalise(points)} accessibilityLayer
      margin={{ top: 12, right: 20, bottom: 14, left: 0 }}>
      <defs><linearGradient id="kats-collection-area" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={PALETTE[0]} stopOpacity={0.32}/>
        <stop offset="100%" stopColor={PALETTE[0]} stopOpacity={0.015}/>
      </linearGradient></defs>
      <ChartAxes points={points} unit={unit}/>
      <Tooltip formatter={tooltip(unit)}/>
      <Legend verticalAlign="top" height={32}/>
      <Area type="linear" dataKey="value" name="Recorded value"
        stroke={PALETTE[0]} strokeWidth={3} fill="url(#kats-collection-area)"
        activeDot={{ r: 6 }} connectNulls={false} isAnimationActive={false}/>
    </RechartsAreaChart>
  </ChartFrame>;
}

/** Comparable rates share the same 0–100% axis; no misleading round radar. */
export function PropertyPerformanceChart({ points, title = 'Property performance' }) {
  const [selected, setSelected] = useState('');
  if (!points?.length) return <EmptyChart label="No property performance data yet."/>;
  const property = points.find(row => String(row.id ?? row.name) === selected) || points[0];
  const values = [
    { name: 'Occupancy', value: Math.min(100, positive(property.occupancy)) },
    { name: 'Rent collection', value: Math.min(100, positive(property.collection)) },
    { name: 'Ticket resolution', value: Math.min(100, positive(property.maintenance)) },
  ];
  return <div className="kats-performance-layout">
    <label className="kats-chart-selector">Property
      <select value={String(property.id ?? property.name)}
        onChange={event => setSelected(event.target.value)}>
        {points.map(row => <option key={row.id ?? row.name}
          value={String(row.id ?? row.name)}>{row.name}</option>)}
      </select>
    </label>
    <ChartFrame title={title + ': ' + property.name}>
      <RechartsBarChart data={values} layout="vertical" accessibilityLayer
        margin={{ top: 6, right: 28, bottom: 9, left: 16 }}>
        <CartesianGrid stroke="#e3eaf0" horizontal={false} strokeDasharray="3 5"/>
        <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]}
          unit="%" tick={{ fontSize: 11 }}/>
        <YAxis type="category" dataKey="name" width={115} tick={{ fontSize: 11 }}/>
        <Tooltip formatter={tooltip('percent')}/>
        <Bar dataKey="value" name="Recorded rate" maxBarSize={35}
          radius={[0, 5, 5, 0]} isAnimationActive={false}>
          {values.map((row, index) => <Cell key={row.name}
            fill={PALETTE[index % PALETTE.length]}/>)}
        </Bar>
      </RechartsBarChart>
    </ChartFrame>
    <div className="kats-performance-values">
      {values.map((row, i) => <span key={row.name}>
        <i className="kats-chart-swatch" style={{ backgroundColor: PALETTE[i] }} aria-hidden="true"/>
        {row.name} <strong>{formatValue(row.value, 'percent')}</strong>
      </span>)}
      <small>Zero observations are reported as 0%; they are not inferred performance.</small>
    </div>
  </div>;
}

/** Exact mutually exclusive groups, rather than an inaccurate overlapping-circle diagram. */
export function VennChart({ data }) {
  const current = positive(data.current), maintenance = positive(data.maintenance);
  const both = positive(data.both), total = positive(data.total);
  if (!total) return <EmptyChart label="No active tenancy records."/>;
  const intersections = [
    { name: 'Current rent only', value: Math.max(0, current - both), rent: true, maintenance: false },
    { name: 'Both', value: both, rent: true, maintenance: true },
    { name: 'Maintenance only', value: Math.max(0, maintenance - both), rent: false, maintenance: true },
    { name: 'Neither', value: Math.max(0, total - current - maintenance + both), rent: false, maintenance: false },
  ];
  return <div className="kats-upset-layout">
    <BarChart points={intersections} unit="tenants" title="Rent and maintenance intersections" horizontal/>
    <div className="data-table-wrap"><table className="kats-upset-table">
      <caption>Exact set membership, by active tenancy</caption>
      <thead><tr><th>Intersection</th><th>Rent current</th><th>Open maintenance</th><th>Tenants</th></tr></thead>
      <tbody>{intersections.map(item => <tr key={item.name}>
        <th scope="row">{item.name}</th>
        <td>{item.rent ? 'Yes' : 'No'}</td>
        <td>{item.maintenance ? 'Yes' : 'No'}</td>
        <td>{item.value.toLocaleString('en-UG')}</td>
      </tr>)}</tbody>
    </table></div>
  </div>;
}
