# Local KATS landlord + tenant demo

**Scope:** isolated, synthetic data in `.local/kats-preview.sqlite3`. This is not a production database, a real tenancy, or a public one-click authentication feature.

## Start in VS Code on Windows

1. Open the KATS repository folder in VS Code.
2. Choose **Terminal → Run Task → KATS: Demo start (landlord + 30 tenants)**.
3. Open **http://127.0.0.1:5173/login**.
4. Under **LOCAL DEMO**, click **Landlord workspace** or any of the 30 searchable **Tenant workspaces**. The server issues the normal authenticated cookies and opens the correct dashboard.
5. Sign out to switch between landlord and tenant accounts.

The dedicated task initialises the isolated SQLite preview automatically. **Only the dedicated Demo tasks opt into synthetic seeding**; ordinary Native start/setup does not add fictional tenants to an existing developer database. A separate **KATS: Demo preview setup (30 tenants)** task is available if you want to initialise or verify the sample data without launching services. Existing custom accounts and changes are preserved. The seeder refuses incomplete existing demo accounts rather than deleting or overwriting them.

### Demo dataset

| Entity | Seeded |
|---|---:|
| Landlord owner account | 1 |
| Tenant login accounts | 30 |
| Linked tenant profiles and active leases | 30 each |
| Fictional properties | 3 |
| Buildings | 3 |
| Floors | 9 |
| Rooms | 33 (30 occupied, 3 vacant) |
| Monthly rent invoices | 60 (previous and current month) |
| Reviewed sample payments | A realistic mix of full, partial, and unpaid invoices |
| Maintenance requests | 4 |

The fictitious landlord is **Grace Namatovu (Demo Landlord)**, account `landlord@demo.kats.invalid`, application role `OWNER`. Tenant accounts are `tenant01@demo.kats.invalid` through `tenant30@demo.kats.invalid`. Their names, phones, properties, leases, balances, invoices, and payment references are *synthetic*, for testing only. No live money moves or providers are called.

### Auth, permissions, and safety

- A demo click calls `POST /api/v1/auth/demo-sign-in` with only a whitelisted account key, for example `landlord` or `tenant-07`.
- The API issues standard, revocable JWT access and refresh session cookies and records an audit event. It does **not** put reusable passwords or tokens in the React bundle.
- Only enabled where all conditions hold: `APP_ENV=development`, `KATS_PREVIEW_MODE=1`, the exact ignored `.local/kats-preview.sqlite3` database, and a loopback request to Flask.
- The API is unavailable outside that preview, including real PostgreSQL, public production deployments and test-app configurations.
- The landlord sees normal KATS OWNER dashboards and administration routes. Each tenant sees only their linked lease, invoices and allowed personal resources. Administrative endpoints reject TENANT roles.
- This is currently a **single-owner deployment** model; it does not imply separate database isolation for multiple unrelated landlord businesses.

No preset production credentials, permanent demo passwords, or public privilege elevation are included. Standard sign-in and MFA are unaffected.

### If the demo picker does not appear

Check that the frontend and backend are running, and that the backend was launched with the dedicated **Demo** VS Code task, not Docker/PostgreSQL mode. Stop an already-running standard backend before switching modes. Ensure the first setup completed without errors; the backend prints `[DEMO] Seeded ...` or `[DEMO] Existing ... verified`.

For a security-preserving local preview, never bind the backend/frontend to a public interface or upload the `.local` SQLite database to production.
