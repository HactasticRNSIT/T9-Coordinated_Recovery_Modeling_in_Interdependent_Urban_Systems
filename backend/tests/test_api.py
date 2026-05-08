"""
API integration tests for UrbanSync AI backend.
Run with: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "UrbanSync AI"


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "UrbanSync AI" in response.json()["message"]


@pytest.mark.asyncio
async def test_list_incidents_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_create_incident_validation():
    """Test that invalid incident data returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/incidents", json={
            "disaster_type": "invalid_type",  # Invalid
            "severity": "high",
            "epicenter": {"lat": 40.7128, "lon": -74.006},
            "start_time": "2025-01-01T00:00:00Z"
        })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_simulation_strategies():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/simulation/strategies/list")
    assert response.status_code == 200
    data = response.json()
    assert "strategies" in data
    assert len(data["strategies"]) == 5
    strategy_ids = [s["id"] for s in data["strategies"]]
    assert "dependency_optimal" in strategy_ids
    assert "power_first" in strategy_ids


@pytest.mark.asyncio
async def test_simulation_run_validation():
    """Test that simulation with invalid strategy returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/simulation/run", json={
            "incident_id": 1,
            "strategies": [],  # Empty — invalid
            "n_monte_carlo": 100,
        })
    assert response.status_code == 422
