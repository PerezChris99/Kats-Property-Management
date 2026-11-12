import { useState } from 'react';

/** Shared, dependency-free SVG chart toolkit for all KATS accounts.
 * One rendering implementation (not a mix of Recharts and Chart.js).
 * SVG viewBox + CSS responsive sizing work without browser ResizeObserver.
 */
const PALETTE = ['#0072B2','#D55E00','#009E73','#CC79A7','#8559A5','#6D6574'];
export const formatUGX = value => 'UGX ' + Number(value || 0).toLocaleString('en-UG');
const formatValue = (value, unit) =>
  unit === 'UGX' ? formatUGX(value) : Number(value || 0).toLocaleString('en-UG') + (unit === 'percent' ? '%' : '');
const safe = value => Math.max(0, Number(value) || 0);

function Legend({ points, unit }) {
  return <ul className="kats-chart-legend">
    {points.map((point, index) => <li key={point.name}>
      <span className="kats-chart-swatch" style={{ backgroundColor: PALETTE[index % PALETTE.length] }} aria-hidden="true"/>
      <span className="kats-chart-name">{point.name}</span>
      <strong>{formatValue(point.value, unit)}</strong>
    </li>)}
  </ul>;
}
export function DonutChart({ points, unit = 'rooms', title = 'Distribution' }) {
  const total = points.reduce((sum, point) => sum + safe(point.value), 0);
  if (!total) return <p className="kats-chart-empty">No recorded values for this period.</p>;
  const radius=65, circumference=2*Math.PI*radius;
  let cumulative=0;
  return <div className="kats-chart-donut-layout">
    <svg className="kats-chart-donut" viewBox="0 0 230 210" role="img" aria-label={title}>
      <title>{title}</title><desc>Distribution of {total} recorded items by category. Values are listed alongside the chart.</desc>
      <circle cx="115" cy="104" r={radius} stroke="#DFE9F0" strokeWidth="25" fill="none"/>
      {points.map((point,index) => {
        const segment=safe(point.value)/total, start=cumulative; cumulative+=segment;
        return <circle key={point.name} cx="115" cy="104" r={radius} fill="none"
          stroke={PALETTE[index%PALETTE.length]} strokeWidth="25"
          strokeDasharray={Math.max(0,segment*circumference)+' '+circumference}
          strokeDashoffset={-start*circumference}
          transform="rotate(-90 115 104)">
          <title>{point.name}: {formatValue(point.value,unit)} ({Math.round(100*segment)}%)</title>
        </circle>;
      })}
      <text x="115" y="101" textAnchor="middle" className="kats-chart-number">{total.toLocaleString('en-UG')}</text>
      <text x="115" y="123" textAnchor="middle" className="kats-chart-small">{unit === 'rooms' ? 'units' : 'invoices'}</text>
    </svg>
    <Legend points={points} unit={unit}/>
  </div>;
}
export function BarChart({ points, unit = 'UGX', title = 'Monthly values' }) {
  if (!points.length) return <p className="kats-chart-empty">No recorded values for this period.</p>;
  const h=240,baseline=190,left=40,right=20,span=620-left-right;
  const max=Math.max(1,...points.map(point=>safe(point.value)));
  const step=span/points.length,barW=Math.min(49,step*.57);
  return <svg className="kats-chart-svg" viewBox={'0 0 620 '+h} role="img" aria-label={title}>
    <title>{title}</title><desc>Bar heights represent database-aggregated values. Exact figures are available in the data table.</desc>
    {[0,.5,1].map(f=> <g key={f}>
      <line x1={left} y1={baseline-145*f} x2={620-right} y2={baseline-145*f} stroke="#D5E2E9" strokeDasharray={f===0?'0':'3 5'}/>
      <text x={left-8} y={baseline-145*f+4} textAnchor="end" className="kats-chart-axis">{f===0?'0':unit==='UGX'?(Math.round(max*f/1000)+'k'):Math.round(max*f)}</text>
    </g>)}
    {points.map((point,i)=>{
      const x=left+(i+.5)*step;
      const barHeight=145*safe(point.value)/max;
      return <g key={point.name}>
        <rect x={x-barW/2} y={baseline-barHeight} width={barW} height={barHeight}
          rx="2" fill={PALETTE[i%PALETTE.length]} tabIndex="0">
          <title>{point.name}: {formatValue(point.value,unit)}</title>
        </rect>
        <text x={x} y={baseline+17} textAnchor="middle" className="kats-chart-axis">
          {point.name.length>13?point.name.slice(0,12)+'…':point.name}
        </text>
      </g>;
    })}
  </svg>;
}
export function LineChart({ points, unit='UGX', title='Monthly trend', secondary=false }) {
  if (!points.length) return <p className="kats-chart-empty">No recorded values for this period.</p>;
  const w=620,h=235,left=58,right=20,top=15,bottom=45;
  const values=points.flatMap(point=>secondary?
    [safe(point.value),safe(point.secondary)]:[safe(point.value)]);
  const max=Math.max(1,...values),width=w-left-right,height=h-top-bottom;
  const x=i=>left+(points.length<=1?width/2:i*width/(points.length-1));
  const y=v=>top+height-(safe(v)/max)*height;
  const poly=key=>points.map((point,i)=>x(i)+','+y(point[key])).join(' ');
  return <div>
    <svg className="kats-chart-svg" viewBox={'0 0 '+w+' '+h} role="img" aria-label={title}>
      <title>{title}</title><desc>Time-ordered SQL aggregates for the account. Exact values appear in tooltips and tables.</desc>
      {[0,.5,1].map(f=><g key={f}>
        <line x1={left} y1={top+height*(1-f)} x2={w-right} y2={top+height*(1-f)} stroke="#D4E0E8" strokeDasharray="3 5"/>
        <text x={left-7} y={top+height*(1-f)+4} textAnchor="end" className="kats-chart-axis">
          {unit==='UGX'?Math.round(max*f/1000)+'k':Math.round(max*f)}
        </text>
      </g>)}
      <polyline points={poly('value')} stroke={PALETTE[0]} strokeWidth="2.7" fill="none" strokeLinejoin="round"/>
      {secondary && <polyline points={poly('secondary')} stroke={PALETTE[1]} strokeWidth="2.7" fill="none" strokeDasharray="5 4" strokeLinejoin="round"/>}
      {points.map((point,i)=><g key={point.name}>
        <circle cx={x(i)} cy={y(point.value)} r="4.8" fill={PALETTE[0]} tabIndex="0"><title>{point.name}: {formatValue(point.value,unit)}</title></circle>
        {secondary && <circle cx={x(i)} cy={y(point.secondary)} r="4.1" fill={PALETTE[1]} tabIndex="0"><title>{point.name}: invoiced {formatValue(point.secondary,unit)}</title></circle>}
        <text x={x(i)} y={h-15} textAnchor="middle" className="kats-chart-axis">{/^\\d{4}-\\d{2}$/.test(point.name) ? point.name.slice(2) : point.name}</text>
      </g>)}
    </svg>
    {secondary && <div className="kats-chart-line-key"><span>● Verified collections</span><span>◆ Net invoiced</span></div>}
  </div>;
}
export function VennChart({ data }) {
  const current=safe(data.current),maintenance=safe(data.maintenance),both=safe(data.both),total=safe(data.total);
  return <div className="kats-venn-layout">
    <svg className="kats-chart-venn" viewBox="0 0 420 200" role="img" aria-label="Current rent and open maintenance overlap">
      <title>Tenants current on rent and with open maintenance requests</title>
      <desc>{both} tenants belong to both groups. Diagram is schematic, not area-proportional.</desc>
      <circle cx="166" cy="94" r="85" fill="#0072B2" fillOpacity=".22" stroke="#0072B2" strokeWidth="2"/>
      <circle cx="254" cy="94" r="85" fill="#D55E00" fillOpacity=".21" stroke="#D55E00" strokeWidth="2"/>
      <text x="127" y="89" textAnchor="middle" className="kats-venn-count">{current-both}</text>
      <text x="210" y="99" textAnchor="middle" className="kats-venn-count">{both}</text>
      <text x="296" y="89" textAnchor="middle" className="kats-venn-count">{maintenance-both}</text>
      <text x="119" y="188" textAnchor="middle" className="kats-chart-axis">Current rent</text>
      <text x="296" y="188" textAnchor="middle" className="kats-chart-axis">Open tickets</text>
    </svg>
    <div className="kats-chart-venn-summary">
      <span>Current only <strong>{current-both}</strong></span>
      <span>Both groups <strong>{both}</strong></span>
      <span>Open tickets only <strong>{maintenance-both}</strong></span>
      <span>Neither <strong>{Math.max(0,total-current-maintenance+both)}</strong></span>
      <small>Active tenants. Overlap sizes are exact; circle area is illustrative.</small>
    </div>
  </div>;
}
export function RadarChart({ points }) {
  const [selected,setSelected]=useState('');
  if (!points.length) return <p className="kats-chart-empty">No property metrics available yet.</p>;
  const point=points.find(p=>(p.id || p.name)===selected)||points[0];
  const axes=[['occupancy','Occupancy'],['collection','Collection'],['maintenance','Ticket resolution']];
  const polar=(n,r)=>[190+Math.sin(2*Math.PI*n/3)*r,135-Math.cos(2*Math.PI*n/3)*r];
  const coords=axes.map(([key],i)=>polar(i,Math.min(100,safe(point[key]))*.94));
  return <div className="kats-radar-layout">
    <svg viewBox="0 0 390 280" className="kats-chart-radar" role="img" aria-label={'Property score for '+point.name}>
      <title>{point.name} — property performance</title>
      <desc>Three percent metrics: occupied units, applied rent versus billed rent, and resolved versus all tickets.</desc>
      {[30,60,94].map(radius=><polygon key={radius} points={axes.map((_,i)=>polar(i,radius).join(',')).join(' ')}
        fill="none" stroke="#CEDCE5" strokeWidth="1"/>)}
      {axes.map(([,name],i)=>{const [x,y]=polar(i,109);return <text key={name} x={x} y={y} textAnchor="middle" className="kats-chart-axis">{name}</text>;})}
      <polygon points={coords.map(point=>point.join(',')).join(' ')}
        fill="#0072B2" fillOpacity=".28" stroke="#0072B2" strokeWidth="2.4"/>
      {coords.map(([x,y],i)=><circle key={axes[i][0]} cx={x} cy={y} r="4" fill="#0072B2">
        <title>{axes[i][1]}: {point[axes[i][0]]}%</title>
      </circle>)}
    </svg>
    <div className="kats-radar-metrics">
      <label>Property <select value={point.id || point.name} onChange={event=>setSelected(event.target.value)}>
        {points.map(row=><option key={row.id || row.name} value={row.id || row.name}>{row.name}</option>)}
      </select></label>
      {axes.map(([key,name])=><div key={key}><span>{name}</span><strong>{point[key]}%</strong></div>)}
      <small>Rates with no underlying observations are shown as 0%.</small>
    </div>
  </div>;
}
