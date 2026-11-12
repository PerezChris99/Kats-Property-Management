/** Lightweight, accessible workspace primitives. No charting or data mocking. */
export function MetricTile({ label, value, description }) {
  return <article className="stat kats-metric-tile">
    <small>{label}</small>
    <strong>{value}</strong>
    {description && <span className="kats-metric-desc">{description}</span>}
  </article>;
}

export function DataStatus({ mode, label, error, onRetry }) {
  if (mode === 'loading') return <div role="status" className="kats-chart-skeleton"
      aria-label={'Loading ' + label}><span/><span/><span/></div>;
  if (mode === 'error') return <div className="kats-chart-feedback" role="alert">
    <p>{error || 'This information could not be loaded.'}</p>
    {onRetry && <button type="button" className="outline-button small" onClick={onRetry}>Retry</button>}
  </div>;
  if (mode === 'empty') return <div className="kats-chart-feedback kats-chart-zero" role="status">
    No recorded information for {label.toLowerCase()} yet.
  </div>;
  return null;
}

export function SectionHeading({ title, description }) {
  return <header className="kats-analytics-heading"><h2>{title}</h2>
    {description && <p>{description}</p>}</header>;
}
