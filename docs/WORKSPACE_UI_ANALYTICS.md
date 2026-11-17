# Authenticated workspace analytics

The owner/staff and tenant dashboards use one responsive Recharts toolkit, implemented in frontend/src/charts/ChartKit.jsx and WorkspaceAnalytics.jsx. No placeholder financial data is rendered or stored as completed browser-cache entries.

## Chart types and presentation controls

- Genuine Cartesian lines, filled areas, vertical/horizontal bars and grouped collection-versus-invoice columns.
- Distribution pies and doughnuts with percentages; current rent/maintenance intersections use **exact grouped bars and membership tables**, not area-implied Venn circles.
- Property score rates use labeled **0–100% horizontal bars**, not decorative polar/radar rings.
- Fixed measurable plot containers own CSS height. Never override Recharts SVG width/height with CSS percentages: this previously collapsed charts into tiny round shapes.
- Every chart has descriptive titles, source methodology, loading/error/empty states, interactive chart-type controls, accessible exact-data tables, mobile-friendly selectors, keyboard-friendly drill-down pickers and SVG export.
- Authenticated dashboards show generation/retrieval times and refresh on successful local mutations, tab reactivation or explicit user request.

## One reporting window for financial graphs and KPIs

The presentation_analytics module exposes:

| Endpoint (/api/v1/ prefix) | Scope |
| --- | --- |
| analytics/period-summary?months=6&end_month=2026-11 | Role-scoped 3/6/12-month financial series and equally long preceding-period comparisons |
| analytics/drilldown?metric=...&month=... | Up to 25 exact underlying authorized rows for a chart point |
| reports/export/period-summary.pdf?months=...&end_month=... | Server-verified printable monthly table, KPIs and methodology |
| reports/export/period-summary.xlsx?months=...&end_month=... | Same source numbers, previous-period comparison and **native editable Excel line chart** |

No caller-supplied tenant ID is accepted. The signed-in JWT's User→Tenant relationship and existing database RLS enforce account boundaries. Values are database GROUP BY aggregates, using **verified settlement dates** for receipts and **invoice periods** for invoiced and applied amounts. Approved expenses use incurred dates. Historic balance snapshots are not inferred from today's invoice balances. When no previous records exist, percentage growth is **N/A**, not infinity.

Occupancy, tenant invoice status and overall property scores remain **current-state** indicators, explicitly labeled separately from the dated financial series.

## Existing analytics

backend/app/workspace_analytics.py provides: owner occupancy, collections by property, monthly collections/billed rent, current-rent/maintenance overlap, property percentage scores and portfolio summary; plus tenant invoice status, applied rent payments, verified settlements and current outstanding by invoice period. backend/app/analytics.py provides staff annual financial trends with independent reconciled-unreversed payment, invoice and approved-expense measures. Endpoint permissions follow the established role contracts.

## Quality and release gates

- SQL aggregation/role/tenant tests: backend/tests/test_workspace_analytics.py, test_extended_workspace_analytics.py, test_presentation_analytics.py, test_presentation_query_budget.py and test_annual_trends.py.
- Source/UI tests: frontend/tests/workspace-analytics.test.mjs and presentation-insights.test.mjs.
- Actual Chromium checks: ops/test_browser_e2e.py verifies graph SVG dimensions, interactive type changes, 3/6/12-month shared filters, PDF/XLSX access, source drilldowns and owner/tenant isolation.
- Real low-cost Android + Safari/iPhone acceptance, bank/provider verification and measured concurrent-user load testing still require operational execution.

See **[Presentation acceptance and benchmark runbook](PRESENTATION_ACCEPTANCE.md)** for demonstration steps, financial definitions, staging-only 25/50/100-virtual-user testing and release signoff.
