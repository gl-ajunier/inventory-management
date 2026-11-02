"""
Tests for the /api/reports endpoints and their filter support.
"""
import pytest

QUARTERLY = "/api/reports/quarterly"
MONTHLY = "/api/reports/monthly-trends"


class TestReportFilters:
    def test_unfiltered_totals_match_orders(self, client):
        orders = client.get("/api/orders").json()
        monthly = client.get(MONTHLY).json()
        assert sum(m["order_count"] for m in monthly) == len(orders)

    def test_month_filter_limits_monthly_trends(self, client):
        month = client.get(MONTHLY).json()[0]["month"]
        data = client.get(MONTHLY, params={"month": month}).json()
        assert [m["month"] for m in data] == [month]

    def test_quarter_filter_limits_quarterly_report(self, client):
        data = client.get(QUARTERLY, params={"month": "Q1-2025"}).json()
        assert all(q["quarter"] == "Q1-2025" for q in data)

    def test_warehouse_filter_matches_orders_endpoint(self, client):
        warehouse = client.get("/api/orders").json()[0]["warehouse"]
        expected = client.get("/api/orders", params={"warehouse": warehouse}).json()
        monthly = client.get(MONTHLY, params={"warehouse": warehouse}).json()
        quarterly = client.get(QUARTERLY, params={"warehouse": warehouse}).json()
        assert sum(m["order_count"] for m in monthly) == len(expected)
        assert sum(q["total_orders"] for q in quarterly) == len(expected)

    def test_status_filter_matches_orders_endpoint(self, client):
        expected = client.get("/api/orders", params={"status": "Delivered"}).json()
        monthly = client.get(MONTHLY, params={"status": "Delivered"}).json()
        assert sum(m["order_count"] for m in monthly) == len(expected)

    @pytest.mark.parametrize("url", [QUARTERLY, MONTHLY])
    def test_no_matches_returns_empty_list(self, client, url):
        response = client.get(url, params={"warehouse": "does-not-exist"})
        assert response.status_code == 200
        assert response.json() == []
