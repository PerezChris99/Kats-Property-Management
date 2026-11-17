"""Presentation analytics are authorized, SQL-aggregated and reproducible."""
from datetime import date
from app.presentation_analytics import month_number, period_args
from test_workspace_analytics import seeded


def test_period_parser_bounds_and_consecutive_comparisons():
    params = {"months": "6", "end_month": "2026-11"}
    count, last, earliest, first, end = period_args(params)
    assert count == 6
    assert first == date(2026, 6, 1)
    assert end == date(2026, 12, 1)
    assert earliest == date(2025, 12, 1)
    assert month_number("2026-11") == last
    for bad in ("2026-00", "2026-13", "1999-12", "../../etc", "2026-01-01"):
        import pytest
        with pytest.raises(ValueError):
            month_number(bad)


def test_role_scoped_period_summary_compare_and_errors(app, monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    path = "/api/v1/analytics/period-summary?months=6&end_month=2026-11"
    for actor in (owner, tenant, other):
        res = actor.get(path)
        assert res.status_code == 200, res.json
        body = res.json
        assert body["start_month"] == "2026-06"
        assert body["end_month"] == "2026-11"
        assert body["previous_start_month"] == "2025-12"
        assert len(body["points"]) == 6
        assert all(p["name"].startswith("2026-") for p in body["points"])
        assert sum(p["verified_collections_ugx"] for p in body["points"]) == \
            body["metrics"]["verified_collections"]["current"]
        assert body["metrics"]["verified_collections"]["previous"] >= 0
        assert res.headers["Cache-Control"] == "private, no-store"
        assert "generated_at" in body
    assert "approved_expenses" in owner.get(path).json["metrics"]
    assert "approved_expenses" not in tenant.get(path).json["metrics"]
    assert "applied_payments" in tenant.get(path).json["metrics"]
    assert tenant.get(path).json != other.get(path).json
    for invalid in ("months=0", "months=400", "months=6&end_month=2026-99"):
        assert owner.get("/api/v1/analytics/period-summary?" + invalid).status_code == 400


def test_chart_drilldown_rejects_tenant_escalation(app, monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    base = "/api/v1/analytics/drilldown?"
    assert tenant.get(base + "metric=occupancy&category=Occupied").status_code == 403
    assert tenant.get(base + "metric=approved_expenses&month=2026-11").status_code == 403
    assert owner.get(base + "metric=applied_payments&month=2026-11").status_code == 403
    assert tenant.get(base + "metric=verified_collections&month=../../etc").status_code == 400
    assert owner.get(base + "metric=nothing&month=2026-11").status_code == 400
    response = owner.get(base + "metric=occupancy&category=Occupied")
    assert response.status_code == 200
    assert len(response.json["items"]) <= 25
    assert all(item["resource"] == "rooms" for item in response.json["items"])
    for actor in (tenant, other):
        result = actor.get(base + "metric=payment_status&category=Due")
        assert result.status_code == 200, result.json
        assert len(result.json["items"]) <= 25
        assert all(item["resource"] == "invoices" for item in result.json["items"])
    a = tenant.get(base + "metric=net_invoiced&month=2026-10")
    b = other.get(base + "metric=net_invoiced&month=2026-10")
    assert a.status_code == 200 and b.status_code == 200
    assert a.json["items"] != b.json["items"]
