import { ChartPanel } from './charts/WorkspaceAnalytics';

export default function MaintenanceAgingPage() {
  return <section className="page">
    <div className="page-head"><div>
      <span className="eyebrow">OPERATIONS</span>
      <h1>Maintenance aging</h1>
      <p>Unresolved work grouped by priority and time open. This is not a contractual SLA score.</p>
    </div></div>
    <div className="kats-chart-grid">
      <ChartPanel title="Open maintenance by priority and age" endpoint="operations/maintenance-aging"
        kind="bar" className="kats-chart-wide"/>
    </div>
    <p className="note">Use work orders to assign and resolve tickets. Aging alone does not establish a breach of service terms.</p>
  </section>;
}
