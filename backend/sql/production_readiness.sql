-- KATS · read-only PostgreSQL production readiness diagnostics.
-- Run with the restricted application role against an approved replica or
-- off-peak production session. NO schema/data changes occur.
-- Do not expose output containing role names or sensitive metadata publicly.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '8000ms';
SET LOCAL lock_timeout = '2000ms';

SELECT current_database() AS database_name,
       current_user AS runtime_role,
       current_setting('server_version') AS postgres_version,
       pg_is_in_recovery() AS is_replica;

-- All core private tables must have ENABLE + FORCE RLS.
SELECT c.relname AS table_name,
       c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced,
       CASE WHEN c.relname = 'documents' THEN 'kats_document_scope'
            ELSE 'kats_runtime_scope' END AS required_policy,
       EXISTS (
         SELECT 1 FROM pg_policies p WHERE p.schemaname = current_schema()
           AND p.tablename = c.relname AND p.policyname =
           CASE WHEN c.relname = 'documents' THEN 'kats_document_scope'
                ELSE 'kats_runtime_scope' END
       ) AS policy_exists
FROM pg_class c
WHERE c.relnamespace = current_schema()::regnamespace
  AND c.relname IN ('documents','tenants','leases','invoices','payments',
                    'maintenance_requests','notifications')
ORDER BY c.relname;

-- Required composite indexes. Missing indexes should block release acceptance.
SELECT ix.tablename, ix.indexname, ix.indexdef
FROM pg_indexes ix
WHERE ix.schemaname = current_schema()
  AND ix.indexname IN (
    'ix_invoices_history_seek','ix_invoices_tenant_history_seek',
    'ix_payments_history_seek','ix_maintenance_history_seek',
    'ix_audit_history_seek','ix_lease_tenant_active',
    'ix_payments_invoice_history_seek','ix_notifications_user_history_seek',
    'ix_maintenance_room_status','ix_caretaker_room_user_lookup',
    'ix_audit_target_history_seek','uq_maintenance_idempotency')
ORDER BY ix.tablename,ix.indexname;

-- Database connection load (including workers, migrations and operator tools).
SELECT datname, numbackends, xact_commit, xact_rollback,
       deadlocks, temp_files, temp_bytes
FROM pg_stat_database WHERE datname = current_database();

-- Large tables and dead tuples indicate vacuum/analyze tuning needs.
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze,
       vacuum_count, autovacuum_count
FROM pg_stat_user_tables
WHERE relname IN ('invoices','payments','ledger_entries','audit_logs',
                  'tenants','leases','maintenance_requests','notifications')
ORDER BY n_dead_tup DESC;

-- Long-running sessions should be investigated, not automatically terminated.
SELECT state, wait_event_type, count(*) AS sessions,
       max(now() - xact_start) AS oldest_transaction
FROM pg_stat_activity
WHERE datname = current_database() AND pid <> pg_backend_pid()
GROUP BY state, wait_event_type
ORDER BY sessions DESC;

ROLLBACK;
