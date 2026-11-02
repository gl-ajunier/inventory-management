"""
Tests for restock order API endpoints.
"""
from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def reset_restock_orders():
    """Restock orders are module-level in-memory state; isolate each test."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


class TestDemandForecastRestockFields:
    """Test the restock fields added to demand forecasts."""

    def test_forecasts_have_cost_and_lead_time(self, client):
        """Test that every forecast carries a positive unit cost and lead time."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        for forecast in response.json():
            assert isinstance(forecast["unit_cost"], (int, float))
            assert isinstance(forecast["lead_time_days"], int)
            assert forecast["unit_cost"] > 0
            assert forecast["lead_time_days"] > 0


class TestRestockOrderEndpoints:
    """Test suite for restock order endpoints."""

    def test_get_restock_orders_empty(self, client):
        """Test that no restock orders exist initially."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restock_order(self, client):
        """Test submitting a restock order computes totals and lead time from forecasts."""
        payload = {
            "budget": 10000,
            "items": [
                {"item_sku": "WDG-001", "quantity": 150},  # 12.50, 10 days
                {"item_sku": "MTR-304", "quantity": 4},    # 385.00, 21 days
            ],
        }
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Submitted"
        assert order["budget"] == 10000
        assert len(order["items"]) == 2
        assert order["items"][0]["item_name"] == "Industrial Widget Type A"
        assert abs(order["items"][0]["line_total"] - 1875.0) < 0.01
        assert abs(order["total_cost"] - (1875.0 + 1540.0)) < 0.01
        assert order["lead_time_days"] == 21

        submitted = datetime.fromisoformat(order["submitted_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert expected - submitted == timedelta(days=21)

    def test_created_order_is_listed_newest_first(self, client):
        """Test that submitted orders are returned newest first."""
        for sku in ["FLT-405", "GSK-203"]:
            response = client.post(
                "/api/restock-orders",
                json={"budget": 5000, "items": [{"item_sku": sku, "quantity": 10}]},
            )
            assert response.status_code == 201

        data = client.get("/api/restock-orders").json()
        assert len(data) == 2
        assert data[0]["items"][0]["item_sku"] == "GSK-203"
        assert data[1]["items"][0]["item_sku"] == "FLT-405"

    def test_create_restock_order_ignores_client_prices(self, client):
        """Test that unit cost comes from the forecast, not the request."""
        payload = {
            "budget": 1000,
            "items": [{"item_sku": "PSU-501", "quantity": 10, "unit_cost": 0.01}],
        }
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201
        assert response.json()["items"][0]["unit_cost"] == 18.99

    def test_create_restock_order_unknown_sku(self, client):
        """Test that an unknown SKU is rejected."""
        payload = {"budget": 1000, "items": [{"item_sku": "NOPE-999", "quantity": 1}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]

    def test_create_restock_order_over_budget(self, client):
        """Test that an order exceeding the budget is rejected and not stored."""
        payload = {"budget": 100, "items": [{"item_sku": "MTR-304", "quantity": 1}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()
        assert client.get("/api/restock-orders").json() == []

    @pytest.mark.parametrize("payload", [
        {"budget": 1000, "items": []},
        {"budget": 1000, "items": [{"item_sku": "WDG-001", "quantity": 0}]},
        {"budget": 0, "items": [{"item_sku": "WDG-001", "quantity": 1}]},
    ])
    def test_create_restock_order_invalid_payload(self, client, payload):
        """Test that empty items, non-positive quantities and budgets fail validation."""
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 422
