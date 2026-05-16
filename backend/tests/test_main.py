from __future__ import annotations

import importlib
import logging

from fastapi.testclient import TestClient


def _load_main_module():
    return importlib.import_module("app.main")


def test_root_health_check():
    main = _load_main_module()
    with TestClient(main.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_header_present():
    main = _load_main_module()
    with TestClient(main.app) as client:
        response = client.get("/", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_app_has_title():
    main = _load_main_module()
    assert main.app.title == "AI Trust Analyzer"


def test_startup_logs_ready(caplog):
    main = _load_main_module()
    with caplog.at_level(logging.INFO, logger="ai_trust_analyzer"):
        with TestClient(main.app):
            pass

    assert "Application ready" in caplog.text
