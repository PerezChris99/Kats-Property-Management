# Architecture decisions

Kats is a custom single-business UGX property manager, not a multi-tenant SaaS product.

React 19 JavaScript / JSX PWA -> Nginx -> Flask/Gunicorn -> PostgreSQL. Celery + Redis run delayed jobs. External MTN/Airtel/EFRIS and notification integrations remain OFF until configured and independently verified.

**Invariants:** no overlapping active leases; amounts are integer UGX; payment credit requires verified approval or provider confirmation; invoice and ledger changes happen in a single DB transaction; financial corrections are reversals, not deletion; strict object-level tenant authorization; signed and replay-safe provider callbacks; every sensitive mutation is audited; PWA never caches private API responses. Production requires TLS, off-server backups, tested restore, owner acceptance and regulatory approval.
