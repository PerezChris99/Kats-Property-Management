import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';

const thisMonth = () => new Date().toISOString().slice(0, 7);
const labelNumber = value => 'UGX ' + Number(value || 0).toLocaleString('en-UG');
const hour = value => {
  if (!value) return 'Not yet refreshed';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown retrieval time'
    : date.toLocaleString('en-UG', { dateStyle: 'medium', timeStyle: 'short' });
};

/**
 * Both the period KPIs and the financial charts use the exact same server
 * report response, avoiding mismatched date windows and stale cached totals.
 */
export function PeriodDashboard({ children }) {
  const [months, setMonths] = useState('6');
  const [endMonth, setEndMonth] = useState(thisMonth);
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({
    status: 'loading', data: null, error: '',
  });
  const lastRequest = useRef(0);
  const refresh = useCallback(() => setRevision(v => v + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    lastRequest.current = Date.now();
    setState({ status: 'loading', data: null, error: '' });
    const query = new URLSearchParams({ months, end_month: endMonth });
    api('analytics/period-summary?' + query.toString(), { signal: controller.signal })
      .then(data => {
        if (!Array.isArray(data?.points) || !data?.metrics ||
          !data?.generated_at) throw new Error('Incomplete presentation report response');
        if (!controller.signal.aborted) setState({ status: 'ready', data, error: '' });
      })
      .catch(error => {
        if (!controller.signal.aborted) setState({
          status: 'error', data: null,
          error: error instanceof Error ? error.message : 'Could not load period summary',
        });
      });
    return () => controller.abort();
  }, [months, endMonth, revision]);

  useEffect(() => {
    const dataChanged = () => refresh();
    const onFocus = () => {
      // Avoid repeated requests while a user is using chart selectors.
      if (Date.now() - lastRequest.current > 15000) refresh();
    };
    const onVisible = () => {
      if (document.visibilityState === 'visible') onFocus();
    };
    window.addEventListener('kats:data-updated', dataChanged);
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.removeEventListener('kats:data-updated', dataChanged);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [refresh]);

  const query = new URLSearchParams({ months, end_month: endMonth }).toString();
  const metrics = Object.entries(state.data?.metrics || {});
  return <section className="kats-period-panel" aria-label="Shared financial reporting period">
    <div className="kats-period-head">
      <div>
        <h2>Financial performance</h2>
        <p>One reporting window for every amount below. Occupancy and invoice status remain current-state measures.</p>
      </div>
      <div className="kats-period-controls">
        <label>Compare periods
          <select value={months} onChange={event => setMonths(event.target.value)}>
            <option value="3">Latest 3 months</option>
            <option value="6">Latest 6 months</option>
            <option value="12">Latest 12 months</option>
          </select>
        </label>
        <label>Through month
          <input type="month" min="2002-01" max="2099-11" value={endMonth}
            onChange={event => setEndMonth(event.target.value)}/>
        </label>
        <button className="outline-button small" type="button" onClick={refresh}
          disabled={state.status === 'loading'}>Refresh all charts</button>
      </div>
    </div>
    {state.status === 'loading' && <p role="status">Recalculating selected period…</p>}
    {state.status === 'error' && <p role="alert">{state.error}
      <button type="button" className="outline-button small" onClick={refresh}>Retry</button></p>}
    {state.status === 'ready' && <>
      <div className="kats-period-metrics stat-grid">
        {metrics.map(([key, metric]) => <div className="stat" key={key}>
          <small>{metric.label}</small>
          <strong>{labelNumber(metric.current)}</strong>
          <span className="kats-period-comparison">
            Previous: {labelNumber(metric.previous)} · {metric.change_percent === null
              ? 'No comparable prior-period percentage'
              : (metric.change_percent > 0 ? '+' : '') + metric.change_percent + '%'}
          </span>
        </div>)}
      </div>
      <div className="kats-period-actions">
        <span role="status">Report generated: <time dateTime={state.data.generated_at}>
          {hour(state.data.generated_at)}</time></span>
        <a href={'/api/v1/reports/export/period-summary.pdf?' + query}
          target="_blank" rel="noreferrer" className="outline-button small">Print / PDF</a>
        <a href={'/api/v1/reports/export/period-summary.xlsx?' + query}
          className="outline-button small">Export Excel + charts</a>
      </div>
      <p className="kats-chart-method">{state.data.method}</p>
    </>}
    {children(state, refresh)}
  </section>;
}

/** Translate the single authenticated reporting response to each chart measure. */
export function financialChartData(endpoint, data) {
  if (!data?.points) return null;
  let measure;
  if (endpoint === 'analytics/landlord/monthly') measure = 'verified_collections_ugx';
  else if (endpoint === 'analytics/tenant/applied-payments') measure = 'applied_payments_ugx';
  else if (endpoint === 'analytics/tenant/payment-history') measure = 'verified_collections_ugx';
  else if (endpoint === 'analytics/tenant/balance-trend') measure = 'current_open_invoice_balance_ugx';
  else return null;
  return {
    unit: 'UGX',
    generated_at: data.generated_at,
    method: data.method,
    points: data.points.map(row => ({
      name: row.name, value: row[measure],
      ...(endpoint === 'analytics/landlord/monthly' ? {
        secondary: row.net_invoiced_ugx,
      } : {}),
    })),
  };
}
