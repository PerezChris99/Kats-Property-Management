# KATS Account UI — Engineering Delivery and Acceptance

**Architecture:** Private single-owner property management. React 19 + Flask + PostgreSQL. Tenant and caretaker are authorized account roles; this is NOT a multi-customer SaaS.

## Assumptions

1. Preserve the existing `/api/v1/analytics/...` contracts instead of introducing `/api/landlord/<id>/...` endpoints. The account identity comes from the authenticated cookie/JWT, so tenant IDs and landlord IDs are **not** trusted from browser paths.
2. Keep **one** existing responsive SVG chart toolkit, `ChartKit.jsx`, rather than installing a second charting library and changing the project's reproducible package lock. It supplies viewBox scaling, accessible SVG titles, tabular exact values, and a common colorblind-safe palette. This achieves responsive charts without Recharts' `ResponsiveContainer` API; the exact library preference is intentionally not followed.
3. Seeded synthetic data is allowed **only in disposable tests/demo preview**. The authenticated application always queries Flask and its configured database.
4. The existing 14px token/12-column system and functional React Router error/404 screens already exist; extend and enforce them rather than introducing duplicate competing implementations.
5. Financial 'applied' payments and actual 'settled' payments are distinct, and invoices are not cash.

## Changed source paths

- `backend/app/workspace_analytics.py`
- `backend/tests/test_extended_workspace_analytics.py`
- `frontend/src/App.jsx`
- `frontend/src/charts/WorkspaceAnalytics.jsx`
- `frontend/src/charts/ChartKit.jsx`
- `frontend/src/components/WorkspacePrimitives.jsx`
- `frontend/src/workspace.css`
- `frontend/tests/workspace-ui-contract.test.mjs`
- `ops/test_browser_e2e.py`
- `docs/KATS_UI_ACCEPTANCE.md`

## API contract and aggregated SQL reference

Existing routes are retained. All are GET, require cookie authentication, and are registered under `/api/v1`. Landlord endpoints allow OWNER / MANAGER / ACCOUNTANT / SUPER_ADMIN; tenant endpoints allow TENANT and derive a tenant record from the authenticated user.

| Method and endpoint | Live SQL method | Chart |
| --- | --- | --- |
| GET `/api/v1/analytics/landlord/occupancy` | `SELECT status, count(id) FROM rooms WHERE status != 'ARCHIVED' GROUP BY status` | Donut |
| GET `/api/v1/analytics/landlord/collections-by-property` | Join properties → rooms → leases → invoices → unreversed reconciled payments; `SUM(payments.amount_ugx) GROUP BY properties.id, name` | Bar |
| GET `/api/v1/analytics/landlord/monthly` | `DATE_TRUNC('month', settled_at)` + `SUM` for reconciled payments, independently `DATE_TRUNC('month', period_start)` + `SUM` for net invoices | Line |
| GET `/api/v1/analytics/landlord/tenant-overlap` | Correlated EXISTS on active leases, overdue rent, open maintenance; `COUNT(DISTINCT CASE...tenant.id)` | Set overlap |
| GET `/api/v1/analytics/landlord/property-scores` | Independent room, invoice and ticket GROUP BY aggregates by property; occupancy, collection, completion percentages | Polar/radar |
| GET `/api/v1/analytics/tenant/payment-status` | `CASE` payment status and `COUNT(invoice.id) GROUP BY status` on tenant's invoices | Donut |
| GET `/api/v1/analytics/tenant/applied-payments` | `DATE_TRUNC('month', invoice.period_start)`, `SUM(invoice.paid_ugx)` by tenant | Bar |
| GET `/api/v1/analytics/tenant/balance-trend` | `SUM(total-paid-credit) GROUP BY rent_month`, cumulative `SUM(...) OVER (ORDER BY rent_month)` | Line |
| **NEW** GET `/api/v1/analytics/landlord/portfolio` | LEFT JOIN properties → non-archived rooms; `COUNT(room.id)`, `SUM(CASE WHEN status='OCCUPIED'...)`, `SUM(CASE WHEN status='VACANT'...)`, `GROUP BY properties.id,name,district` | KPI row + details table |
| **NEW** GET `/api/v1/analytics/tenant/payment-history` | Join payment → invoice, filter tenant ID, reconciled / not reversed / settled date present, `DATE_TRUNC('month',settled_at)`, `SUM(amount_ugx)`, GROUP BY month | Bar |

The PostgreSQL dialect uses `DATE_TRUNC`; isolated SQLite test environments use equivalent `strftime` bucketing. SQLAlchemy composes parameterized queries. The two NEW endpoints are authorization tested and have no client-selected user IDs.

Illustrative new endpoint responses:

```json
{
  "points": [
    {"id": "property-uuid", "name": "Property name", "district": "Kampala", "value": 12, "occupied": 10, "vacant": 2}
  ],
  "unit": "rooms",
  "method": "One owner's non-archived units grouped by property..."
}
```

```json
{
  "points": [{"name": "2026-10", "value": 450000}],
  "unit": "UGX",
  "method": "Verified unreversed receipts by actual settlement month..."
}
```

These values illustrate the response shape; they are not substituted for production SQL results.

## Design tokens

All private account pages use `frontend/src/workspace.css`. Public marketing pages remain independent.

| Token | Value |
| --- | --- |
| `--font-size-xs`, `--font-size-sm`, `--font-size-base` | 11px / 12px / **14px** |
| `--font-size-lg`, `--font-size-xl`, `--font-size-2xl` | 16px / 20px / 24px |
| `--space-1` through `--space-8` | 4px, 8px, 12px, 16px, 20px, 24px, 28px, 32px |
| `--line-height-tight/normal/loose` | 1.25 / 1.5 / 1.65 |
| `--weight-regular/medium/semibold/bold` | 400 / 550 / 650 / 750 |
| `--radius-sm/md/lg` | 4px / 6px / 8px |
| `--control-height`, `--control-height-sm` | 32px / 28px |
| `--chart-height` / `--table-height` | 240px / 42px |
| `--content-max`, grid | 1392px, 12 columns, 16px gaps |
| Responsive breakpoints | 640 / 768 / 1024 / 1280px |

Keyboard focus, reduced motion, loading/error/empty states, exact chart data tables and chart SVG titles remain visible. Deliberately removed oversized glass effects and redundant dashboard card padding.

## Changelog

- Added SQL-aggregated property metrics and real-date tenant verified payment history.
- Added shared functional `MetricTile`, `DataStatus`, `SectionHeading`.
- Added a real portfolio KPI row and detailed property table, plus a tenant settled-payments chart.
- Fixed property selection in radar charts to use stable property IDs instead of names.
- Fixed reports so an arrears API failure does not hide a valid financial report; both can retry independently and cancel stale requests.
- Hardened invalid chart payloads to display an error rather than failing during render.
- Consolidated account visual density through existing token scopes, retaining mobile-responsive SVG scaling.
- Added automated backend privacy/live-SQL tests, import/route/token tests and updated real-browser chart/route coverage.

## Acceptance and proof

| Criterion | Engineering status | Verification requirement |
| --- | --- | --- |
| All account routes, no blank pages, loading/empty/error | Existing route-level error/404 UI plus new independent report fallbacks | Browser route smoke and error simulation; partial API failures assessed |
| Typography and sizing | Existing 14px tokens, 32/28 controls, tighter account-only overrides | Node token contract and CSS responsive tests |
| Landlord 5 charts; tenant 3 required charts | Existing shared toolkit, plus additional verified history chart | Actual browser chart tests at 360–1440px |
| Live analytics with aggregated PostgreSQL | Ten existing/extended SQL endpoints and JWT role scoping | Backend live-mutation and authorization tests; Postgres migration and runtime tests |
| Responsive layout | One 12-column private grid and 640/768/1024/1280 media styles | Playwright narrow/wide layout and chart overflow checks |
| Build & server startup | Existing app factory and import tests, no removed module | `npm run build`, Flask SQLite boot, PostgreSQL runtime, Windows launcher job |

**Release boundary:** Passing the local CI matrix does not certify real tenant data, external payments, live hosting, offsite backup restores, or legal/regulatory acceptance. Do not falsely mark these as complete.
