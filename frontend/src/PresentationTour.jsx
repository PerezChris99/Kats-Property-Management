import { useState } from 'react';
import { Link } from 'react-router-dom';

const GUIDES = {
  OWNER: [
    ['Portfolio overview', '/dashboard', 'Review live occupancy, verified collection KPIs and the date filter.'],
    ['Property records', '/properties', 'Open a property and its buildings, floors and units.'],
    ['Tenancies', '/tenants', 'Trace a fictional tenant to the related lease and room.'],
    ['Rent invoices', '/invoices', 'Review billing periods, credits and outstanding rent.'],
    ['Verified payments', '/payments', 'Contrast recorded collections with verified settlement.'],
    ['Yearly trends', '/trends', 'Change the year and chart type; export the approved report.'],
    ['Finance control', '/bank-reconciliation', 'Explain what requires independent bank approval.'],
  ],
  ACCOUNTANT: [
    ['Financial summary', '/dashboard', 'Compare verified settlements with invoices.'],
    ['Review invoices', '/invoices', 'Open exact billing and credit notes.'],
    ['Verify payments', '/payments', 'Review supporting evidence and status.'],
    ['General ledger', '/general-ledger', 'Demonstrate journal traceability and reversals.'],
    ['Reconciliation', '/bank-reconciliation', 'Explain bank-statement review and exceptions.'],
  ],
  MANAGER: [
    ['Portfolio', '/dashboard', 'Compare occupancy and collections.'],
    ['Properties', '/properties', 'Inspect room status and unit allocations.'],
    ['Operations', '/maintenance', 'Follow maintenance assignments to resolution.'],
    ['Billing', '/invoices', 'Review invoiced versus collected rent.'],
    ['Reports', '/reports', 'Show reporting periods and financial exports.'],
  ],
  TENANT: [
    ['My rental account', '/dashboard', 'Review only the signed-in tenant’s lease and payment KPIs.'],
    ['My invoices', '/invoices', 'Open recorded rent invoices.'],
    ['My payments', '/payments', 'Review applied payments and independent settlement status.'],
    ['Maintenance request', '/maintenance', 'Trace a service request for the assigned unit.'],
    ['Statements', '/statements', 'Review the statement without accessing anyone else’s.'],
  ],
  CARETAKER: [
    ['Assigned work', '/dashboard', 'Show only rooms assigned to this caretaker.'],
    ['My rooms', '/rooms', 'Inspect permitted room records.'],
    ['Maintenance', '/maintenance', 'Follow a fictional ticket through its lifecycle.'],
    ['Cash custody', '/payments', 'Distinguish cash recording from independent finance approval.'],
    ['Work orders', '/work-orders', 'Review outstanding assigned work.'],
  ],
};
GUIDES.SUPER_ADMIN = GUIDES.OWNER;

/** Navigational guide only. Never seeds, mutates, or exposes live tenant data. */
export function PresentationTour({ role }) {
  const steps = GUIDES[role] || GUIDES.MANAGER;
  const [step, setStep] = useState(0);
  // Local-only: demonstrations must not be advertised to real customers.
  if (!import.meta.env.DEV || !['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)) return null;
  const [name, href, description] = steps[Math.min(step, steps.length - 1)];
  return <details className="kats-presentation-tour">
    <summary>Presentation walkthrough · {role.replaceAll('_', ' ').toLowerCase()} account</summary>
    <div className="kats-tour-content">
      <p><strong>Fictional local demonstration only.</strong> Use the isolated seeded database; never present actual tenant records or payment credentials.</p>
      <div className="kats-tour-progress" role="status">Step {step + 1} of {steps.length}</div>
      <h2>{name}</h2>
      <p>{description}</p>
      <div className="kats-tour-actions">
        <button type="button" className="outline-button small" disabled={step === 0}
          onClick={() => setStep(i => Math.max(0, i - 1))}>Previous</button>
        <Link className="button small" to={href}>Open {name}</Link>
        <button type="button" className="outline-button small"
          disabled={step === steps.length - 1}
          onClick={() => setStep(i => Math.min(steps.length - 1, i + 1))}>Next</button>
      </div>
    </div>
  </details>;
}
