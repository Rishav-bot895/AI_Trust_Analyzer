"""Tests for API router wiring (Task 1.11)."""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient


def _load_main_module():
    return importlib.import_module("app.main")


def test_router_prefix_applied():
    """POST analyze route should be mounted under /api/v1 prefix."""
    main = _load_main_module()
    with TestClient(main.app) as client:
        prefixed_response = client.post("/api/v1/analyze")
        unprefixed_response = client.post("/analyze")

    assert prefixed_response.status_code == 501
    assert unprefixed_response.status_code == 404


def test_openapi_schema_includes_analyze():
    """Analyze endpoint should appear in generated OpenAPI schema."""
    main = _load_main_module()
    with TestClient(main.app) as client:
        schema = client.get("/openapi.json").json()

    assert "/api/v1/analyze" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/analyze"]


def test_health_route_exists():
    """Health endpoint should exist under API v1 and return ok payload."""
    main = _load_main_module()
    with TestClient(main.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}