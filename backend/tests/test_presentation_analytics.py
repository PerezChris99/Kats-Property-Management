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
        assert "no-store" in res.headers["Cache-Control"]
        assert "generated_at" in body
    assert "approved_expenses" in owner.get(path).json["metrics"]
    assert "approved_expenses" not in tenant.get(path).json["metrics"]
    assert "applied_payments" in tenant.get(path).json["metrics"]
    for row in tenant.get(path).json["points"]:
        assert row["current_open_invoice_balance_ugx"] == (
            row["net_invoiced_ugx"] - row["applied_payments_ugx"])
        assert row["current_open_invoice_balance_ugx"] >= 0
    assert tenant.get(path).json != other.get(path).json
    for invalid in ("months=0", "months=400", "months=6&end_month=2026-99"):
        assert owner.get("/api/v1/analytics/period-summary?" + invalid).status_code == 400


def test_chart_drilldown_rejects_tenant_escalation(app, monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    base = "/api/v1/analytics/drilldown?"
    assert tenant.get(base + "metric=occupancy&category=Occupied").status_code == 403
    assert tenant.get(base + "metric=approved_expenses&month=2026-11").status_code == 403
    assert owner.get(base + "metric=applied_payments&month=2026-11").status_code == 403
    assert owner.get(base + "metric=open_invoices&month=2026-11").status_code == 403
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



def test_presentation_exports_are_identical_scope_and_excel_has_real_chart(app, monkeypatch):
    from io import BytesIO
    from zipfile import ZipFile
    owner, tenant, other = seeded(app, monkeypatch)
    params = "months=6&end_month=2026-11"
    for actor in (owner, tenant, other):
        json_result = actor.get("/api/v1/analytics/period-summary?" + params)
        assert json_result.status_code == 200
        pdf = actor.get("/api/v1/reports/export/period-summary.pdf?" + params)
        assert pdf.status_code == 200
        assert pdf.data.startswith(b"%PDF-")
        assert pdf.headers["Cache-Control"] == "no-store"
        xlsx = actor.get("/api/v1/reports/export/period-summary.xlsx?" + params)
        assert xlsx.status_code == 200
        with ZipFile(BytesIO(xlsx.data)) as workbook:
            names = workbook.namelist()
            assert "xl/charts/chart1.xml" in names
            assert "xl/worksheets/sheet1.xml" in names
            assert "xl/worksheets/sheet2.xml" in names
            chart = workbook.read("xl/charts/chart1.xml")
            assert b"lineChart" in chart and b"Monthly results" in chart
        assert xlsx.headers["Cache-Control"] == "no-store"
    assert owner.get("/api/v1/reports/export/period-summary.pdf?months=999").status_code == 400
    assert tenant.get("/api/v1/reports/export/period-summary.xlsx?end_month=invalid").status_code == 400


def test_current_source_records_are_never_shared_with_other_tenants(app, monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    base = "/api/v1/analytics/drilldown?"
    first = tenant.get(base + "metric=payment_status&category=Paid")
    second = other.get(base + "metric=payment_status&category=Paid")
    assert first.status_code == second.status_code == 200
    # Different seeded customers have different invoices and cannot see one another's.
    first_names = {x["title"] for x in first.json["items"]}
    second_names = {x["title"] for x in second.json["items"]}
    assert not first_names.intersection(second_names)
    assert tenant.get(base + "metric=property_collections&category=Demo").status_code == 403
    assert other.get(base + "metric=overlap&category=Both").status_code == 403
    assert owner.get(base + "metric=overlap&category=Neither").status_code == 200


def test_tenant_current_open_invoice_drilldown_matches_period_graph(app, monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    summary = tenant.get("/api/v1/analytics/period-summary?months=6&end_month=2026-11")
    assert summary.status_code == 200
    rows = summary.json["points"]
    for row in rows:
        response = tenant.get("/api/v1/analytics/drilldown?metric=open_invoices&month=" + row["name"])
        assert response.status_code == 200
        assert sum(item["amount_ugx"] for item in response.json["items"]) == row["current_open_invoice_balance_ugx"]
    assert owner.get("/api/v1/analytics/drilldown?metric=open_invoices&month=2026-11").status_code == 403
