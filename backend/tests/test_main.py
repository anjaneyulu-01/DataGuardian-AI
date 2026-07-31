"""Smoke tests proving the application boots and serves its system routes."""

from fastapi.testclient import TestClient

from app.main import app


def test_root_returns_service_info() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"project": "DataGuardian AI", "status": "running"}


def test_health_reports_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_schema_is_generated() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "DataGuardian AI"
