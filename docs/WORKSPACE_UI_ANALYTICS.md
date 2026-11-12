# Authenticated KATS workspace UI and live analytics

The landlord/owner and tenant dashboards use a shared **SVG chart toolkit**
(`frontend/src/charts/ChartKit.jsx`). This is the application's **one**
charting implementation, including the existing annual performance page.
No new third-party chart package or UI framework is introduced, keeping bundle
size controlled. The SVG charts have responsive viewBoxes and chart-specific
data tables, native browser tooltips, text legends, descriptive titles,
status placeholders and keyboard-focusable data points. The palette is based
on colorblind-aware blue / orange / green / purple with dark text labels.
Venn-circle area is **illustrative, not proportional**; numeric overlaps are
exact SQL counts.

## Account visual hierarchy and sizing

The authenticated workspace has its own CSS file,
`frontend/src/workspace.css`, loaded **after** existing site styles:
- Base font 14px; named XS (11), SM (12), LG (16), XL (20), 2XL (24).
- Line-height, weight, spacing `--space-1` through `--space-8` (4px increments),
  card radius, input/button heights, chart container heights are tokens.
- Default button 32px minimum, compact 28px; inputs 32px minimum.
- Twelve-column responsive grid, 16px gaps; authenticated content width limited
  to 1392px. Breakpoints: 640, 768, 1024 and 1280px.
- Consistent compact cards, heading hierarchy, tabular numbers and horizontal
  table containment. Public marketing typography is unaffected.
- The scorecard sits between the KPI overview and detail/quick-link tables;
  charts are lazy-loaded per account route.
- Functional data-router error boundaries and explicit 404 recovery replace a
  blank screen when a component crashes or a route is missing. Failed private
  GET requests also surface an account-level reload notice, even if an
  individual screen consumes its error internally.

## Added Flask analytics endpoints

All read-only endpoints use `@roles` to enforce existing JWT, revocation
state, route permissions and role ceiling. No account ID is accepted from the
browser: tenant ID comes from the authenticated `User -> Tenant` mapping,
and existing PostgreSQL FORCE RLS enforces independent SQL restrictions.
They are added to `backend/app/workspace_analytics.py` with no schema
migration. The calculations come from SQL GROUP BY / SUM / COUNT / CASE and
PostgreSQL DATE_TRUNC or window functions.

| Endpoint (`GET /api/v1/` prefix) | Audience | Database aggregation |
|---|---|---|
| `analytics/landlord/occupancy` | OWNER/MANAGER/ACCOUNTANT/SUPER_ADMIN | Rooms grouped by non-archived `status` |
| `analytics/landlord/collections-by-property` | Staff | RECONCILED and unreversed Payment amounts grouped by Property |
| `analytics/landlord/monthly` | Staff | DATE_TRUNC(month, payment settlement), SUM of reconciled payments; independent invoice period SUM for comparison |
| `analytics/landlord/tenant-overlap` | Staff | COUNT(DISTINCT CASE ...) over active tenants, correlated EXISTS of overdue invoices and open maintenance |
| `analytics/landlord/property-scores` | Staff | Independent SQL grouped room occupancy, net rent realization and maintenance completion per property (0–100%) |
| `analytics/tenant/payment-status` | TENANT | CASE paid/due/overdue per invoice, GROUP BY status |
| `analytics/tenant/applied-payments` | TENANT | SUM(invoice.paid_ugx) per invoiced rent month, **not** settlement month |
| `analytics/tenant/balance-trend` | TENANT | SUM(net outstanding) per month and cumulative SQL SUM OVER ORDER BY |
 
Representative PostgreSQL SQL (actual implementation uses SQLAlchemy
expressions and bound parameters):

```sql
SELECT date_trunc('month', settled_at), sum(amount_ugx)
FROM payments
WHERE status='RECONCILED' AND reversed_at IS NULL AND settled_at IS NOT NULL
GROUP BY date_trunc('month', settled_at);

SELECT status, count(*) FROM rooms WHERE status <> 'ARCHIVED'
GROUP BY status ORDER BY status;

-- Cumulative tenant outstanding after grouped billing periods;
-- tenant id comes from the verified signed-in principal.
SELECT month, sum(balance) OVER (ORDER BY month)
FROM (
  SELECT date_trunc('month', period_start) AS month,
         sum(total_ugx - paid_ugx - credit_ugx) AS balance
  FROM invoices
  WHERE tenant_id = :verified_tenant_id AND status <> 'VOID'
  GROUP BY date_trunc('month', period_start)
) monthly;
```

### Set overlap methodology

The Venn diagram uses distinct tenants with an **ACTIVE** lease:
- Current on rent: no non-void invoice with a positive remaining balance whose
  `due_date` has passed.
- Maintenance: at least one open / assigned / in-progress / on-hold repair.
- Both: the intersection of those two conditions (COUNT DISTINCT in SQL).
- Neither: active tenant count minus union count.

It does not imply that maintenance issues are the tenant's fault.

### Polar / radar property scores

Property metrics are aggregated in **separate** SQL GROUP BY queries to avoid
inflating totals from multiplying invoices by tickets:
- Occupancy: occupied rooms ÷ non-archived rooms.
- Collection realization: sum of `paid_ugx` ÷ net invoiced rent for that property.
- Ticket resolution: closed/non-open tickets ÷ all tickets.

If a property has no observations for a metric, that metric is disclosed as
0%, not a fabricated score. These are operational percentages, not a legal
compliance grade or an audited performance ranking.

## Loading and failure behavior

Each chart fetches its **dedicated** JSON endpoint through the existing
same-origin cookie/CSRF-aware API client. Every chart has a skeleton, an
explicit no-records message, a bounded descriptive error, and a Retry button.
AbortController cancels stale requests on navigation. Loaded values are not
cached to localStorage/service worker or converted into invented defaults.
Tables under the charts expose exact amounts for accessibility.

The annual performance chart retains the original endpoint and disclosure,
but now shares `ChartKit` with the dashboards. Navigation is still
role-filtered, and the new data-router `errorElement` provides a functional
render-error boundary without adding class components.

## Verification

- `backend/tests/test_workspace_analytics.py` checks each new route, rejects
  anonymous/cross-role requests, and **changes database data during tests** to
  verify updated responses. A second tenant's results must not change.
- `frontend/tests/workspace-analytics.test.mjs` verifies shared rendering,
  lazy modules, all eight endpoints, sizing/breakpoints and error routes.
- `ops/test_browser_e2e.py` navigates every landlord and tenant account
  page in the local synthetic demo and checks that all eight charts render
  without blank pages at five responsive viewport sizes.
- Execute: `npm run build`, `python -m pytest`, and the existing
  `tests/test-all.bat` (Docker for isolated database/E2E tests).

No placeholders or untrusted client-supplied account IDs are used in
production analytics responses. This version implements a **single-company
property manager**; multi-organization scoping is a separate architecture.

## Compact account navigation (landlord and tenant)

The left sidebar now contains primary destinations rather than every individual
route. The landlord/staff view groups routes under Dashboard, Portfolio,
Tenancies, Finance, Operations, Reports & files, and Administration. The tenant
view groups them under Dashboard, Rent & payments, Property care,
Records & updates, and My account.

Every group opens an existing, permission-checked URL. The content area exposes
numbered subpage tabs for the remaining authorized pages in that group; each
tab preserves its old canonical URL, API fetch, existing forms, permissions,
and browser history. Deep links and bookmarks therefore remain valid.
The sidebar has no vertical scrollbar in its normal desktop state. Filtering by
navigation search intentionally allows a scrollable result list when many
direct page matches are returned. Small screens retain the mobile drawer.

Regression coverage: `frontend/tests/workspace-navigation.test.mjs`.
For browser acceptance, inspect at desktop widths and short viewport heights,
including 1024×768 and 1280×720, and verify that each visible sidebar group
reaches every corresponding tab and that no page is lost due to RBAC.
