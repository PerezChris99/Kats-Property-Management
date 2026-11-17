# KATS presentation acceptance and analytics release gate

**Scope:** Single-owner property operation. This document describes implemented, role-protected features and the remaining **physical/operational** acceptance gates. An automated CI pass is not a production or capacity certification.

## Demo flow (fictional local-only data)

Use the existing one-time local PostgreSQL demo preparation. Never run the seeder on production or use real tenant/payment information in screenshots. Sign into the local demo using the already-provisioned 31 fictional accounts. Each dashboard has a collapsed **Presentation walkthrough** with links that respect the signed-in role:

| Presenter | Demonstrate |
| --- | --- |
| OWNER / SUPER_ADMIN | Occupancy → property → lease → rent invoice → verified collections → annual financial trends → bank review |
| MANAGER | Portfolio → assigned maintenance → invoices → scoped reports |
| ACCOUNTANT | Invoicing → payment verification → general ledger → reconciliation exceptions |
| CARETAKER | Assigned rooms → maintenance ticket → cash custody record awaiting independent review |
| TENANT | Own lease → own invoice/payment → maintenance → own statement; explicitly verify that another tenant's records are inaccessible |

The walkthrough is intentionally visible only on loopback **development** builds and makes no database mutations. It does **not** enable a public production demo account.

## Shared financial reporting semantics

**Financial reporting panel on OWNER/MANAGER/ACCOUNTANT/SUPER_ADMIN and TENANT dashboards:**

- Select **3, 6 or 12 consecutive calendar months**, ending at a chosen YYYY-MM. All financial KPI comparisons and participating financial charts come from the **same** authenticated /analytics/period-summary request.
- Previous comparison covers the immediately preceding window of the **same duration**. When the prior value is zero, the percentage comparison is **N/A** rather than falsely infinite growth.
- **Verified collections:** reconciled, unreversed receipts by actual settlement month. No evidence of settlement means no verified cash.
- **Net invoiced:** nonvoid invoice amounts less applied credit notes by invoice period.
- **Applied payments:** current applied invoice amounts by the original billing month, not cash settlement month.
- **Approved expense:** approved costs by incurred month, not necessarily actual cash disbursement.
- **Open invoice balance graph (tenant):** the current unpaid balance grouped by billing period within the selected window. **Not** a reconstructed historic balance as of each past month.
- Occupancy, tenant payment status, property scores and tenancy intersections are **current / all-records** indicators and deliberately do not pretend to follow the historical financial window.
- Server responses are private, no-store. Client coalescing applies **only while GETs are pending**; successful non-auth write requests prompt the dashboard to refetch. Refresh and returning to a previously backgrounded tab revalidate. The **generated-at** label describes query generation, not the last transaction time.

## Drill-down and exports

Users can click chart marks or use the keyboard-accessible **Explore source records** picker. /analytics/drilldown whitelists the metric and relevant month/status, enforces JWT roles and account isolation, and limits preview records to **25**. Tenant identity is derived exclusively from the JWT to Tenant relationship; not from query parameters.

**Export matching KPIs:** the PDF and XLSX routes call the same period_payload aggregation, with the same dates and current role. The Excel file contains a genuine editable Excel line chart with underlying worksheet values; PDF is a printable signed-in financial summary with exact monthly tables. Both are internal reports, **not** tax invoices, fiscal receipts or audited accounts. Each graph can also be downloaded as a vector SVG for the presentation; the SVG is a snapshot of the browser's authorized source values, not a separately certified server report.

The annual performance page exposes source drill-downs, year-switching and 12-month PDF/XLSX exports. The annual payment query excludes reversed receipts.

## Automated validation

- Python: backend/tests/test_presentation_analytics.py, test_presentation_query_budget.py, test_annual_trends.py.
- Node/React: frontend/tests/workspace-analytics.test.mjs and presentation-insights.test.mjs; npm run build runs syntax, ESLint and tests.
- Chromium: ops/test_browser_e2e.py checks both account types, real SVG geometry, period filters, actual XLSX bytes, authorized drilldowns and responsive views.
- The existing GitHub Actions suite validates backend/PostgreSQL, frontend/browser and Windows launchers. Check the exact commit before merging.

## Benchmark and load acceptance (staging only)

The report endpoint groups payments, invoices and approved expenses **in SQL**, returning only bounded monthly aggregates. The query-budget test guards against per-month or per-tenant queries. Do not add new database indices or cache private records without evidence from PostgreSQL query plans.

To identify bottlenecks, use an isolated staging PostgreSQL replica with realistic **fictional** volumes. Sample:

~~~sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT EXTRACT(YEAR FROM settled_at) AS yr,
       EXTRACT(MONTH FROM settled_at) AS mon,
       SUM(amount_ugx)
FROM payments
WHERE status = 'RECONCILED' AND reversed_at IS NULL
  AND settled_at >= TIMESTAMPTZ '2026-01-01'
  AND settled_at < TIMESTAMPTZ '2027-01-01'
GROUP BY 1, 2;
~~~

Record query plan, scanned rows, buffer hits/reads, mean/p95/p99 API latency, database pool pressure, CPU/RAM and Celery queue depth. A suitable validated multicolumn/partial index can be added only after inspecting real scan volumes and write costs.

Use the existing read-only guarded k6 script with explicitly approved HTTPS staging and a **synthetic, isolated cookie**:

~~~text
KATS_LOAD_TEST_APPROVED=yes
KATS_STAGING_BASE_URL=https://<your-approved-staging-host>
KATS_STAGING_COOKIE=<synthetic-test-account-cookie>
KATS_STAGING_ROLE=OWNER or TENANT
KATS_STAGING_PROFILE=presentation
KATS_STAGING_VUS=25, 50 or 100
k6 run ops/load-workspace.js
~~~

These are **virtual users with a shared synthetic account**, not evidence of 100 independent RBAC tenants. Do not test payment mutations or production with this script. Meet the script's declared error/p95/p99 thresholds, review bottlenecks, then repeat with representative accounts and workflow concurrency.

## Signoff before a client demonstration or sale

- Confirm all owner, manager, accountant, caretaker and tenant walkthroughs on the actual deployed candidate.
- Test the drill-down and export APIs on tenant identities A and B: no cross-account records, including in downloaded files.
- Inspect charts and keyboard/touch controls on a low-cost Android handset and Safari on iPhone, plus a narrow laptop screen.
- Validate exported figures against accountant-approved source invoices and independently settled payments, not seeded test-only numbers.
- Complete production HTTPS, staging backup-restore, provider settlement, compliance, support and client UAT. The application is **not launch-certified** until the applicable gates pass.
