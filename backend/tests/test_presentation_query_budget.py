"""Budget SQL reporting round-trips on the 31-account seeded demo.

Avoid a query per tenant, invoice, month or chart point. This is a query-count
regression, not a claimed p95 latency or throughput benchmark.
"""
from sqlalchemy import event
from app.extensions import db
from test_workspace_analytics import seeded


def test_shared_period_summary_uses_bounded_sql_grouping(app, monkeypatch):
    owner, tenant, _other = seeded(app, monkeypatch)
    query = "/api/v1/analytics/period-summary?months=12&end_month=2026-11"
    for actor in (owner, tenant):
        sql = []
        def count_sql(_conn, _cursor, statement, _params, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                sql.append(statement.lower())
        event.listen(db.engine, "before_cursor_execute", count_sql)
        try:
            result = actor.get(query)
        finally:
            event.remove(db.engine, "before_cursor_execute", count_sql)
        assert result.status_code == 200, result.json
        # Aggregation remains on the database; no per-month/per-record fetch.
        financial = [q for q in sql if (" from payments" in q or " from invoices" in q
                                       or " from expenses" in q) and "sum(" in q]
        assert len(financial) <= 3, financial
        assert all("group by" in q for q in financial)
        assert len(result.json["points"]) == 12
