"""Create the restricted RLS test role in the DISPOSABLE kats_ci database only.

Never run against production, staging, or the application database.
"""
import os
from urllib.parse import urlsplit
import psycopg

url = os.environ.get("TEST_POSTGRES_URL", "")
normalized = url.replace("postgresql+psycopg://", "postgresql://", 1)
parsed = urlsplit(normalized)
if parsed.hostname != "test-db" or parsed.path != "/kats_ci" or parsed.username != "kats_ci":
    raise SystemExit("Refusing to provision a database other than isolated test-db/kats_ci")
with psycopg.connect(normalized) as connection:
    if not connection.execute(
        "SELECT 1 FROM pg_roles WHERE rolname='kats_rls_test'"
    ).fetchone():
        connection.execute("CREATE ROLE kats_rls_test LOGIN PASSWORD 'rls_ci_password'")
    connection.execute("GRANT USAGE ON SCHEMA public TO kats_rls_test")
    connection.execute("GRANT SELECT ON documents TO kats_rls_test")
    connection.execute("GRANT SELECT ON caretaker_assignments TO kats_rls_test")
print("Isolated kats_ci PostgreSQL RLS test role ready.")
