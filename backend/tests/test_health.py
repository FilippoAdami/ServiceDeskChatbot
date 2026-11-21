from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


def test_health_success(client: TestClient) -> None:
    """Test that GET /api/health returns HTTP 200 with valid typed payload and DB connected."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "test"
    assert data["detail"] is None

    # Verify timestamp is valid ISO format in UTC
    parsed_time = datetime.fromisoformat(data["timestamp"])
    assert parsed_time.tzinfo is not None
    # Check that timestamp is recent (within 60 seconds)
    now_utc = datetime.now(timezone.utc)
    assert abs((now_utc - parsed_time).total_seconds()) < 60


def test_health_db_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that GET /api/health returns HTTP 503 when the database check fails."""
    # Monkeypatch check_db_connection to simulate database unreachable
    monkeypatch.setattr("backend.app.api.health.check_db_connection", lambda: False)

    response = client.get("/api/health")
    assert response.status_code == 503

    data = response.json()
    assert data["status"] == "error"
    assert data["database"] == "disconnected"
    assert "detail" in data
    assert "Database connection check failed" in data["detail"]


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint returns application metadata and docs link."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"
