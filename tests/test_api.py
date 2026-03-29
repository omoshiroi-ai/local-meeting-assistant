"""FastAPI smoke tests (uses temp data dir)."""

import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("MEETING_DATA_DIR", str(tmp_path))
    import src.config as cfg

    importlib.reload(cfg)
    import src.api.main as api_main

    importlib.reload(api_main)
    with TestClient(api_main.app) as client:
        yield client


def test_health(api_client: TestClient):
    r = api_client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "microphone" in data
    assert data["microphone"]["ok"] in (True, False)


def test_sessions_empty(api_client: TestClient):
    r = api_client.get("/api/sessions")
    assert r.status_code == 200
    assert r.json() == []


def test_models(api_client: TestClient):
    r = api_client.get("/api/models")
    assert r.status_code == 200
    data = r.json()
    assert data["llm"]["active_id"]
    assert data["llm"]["environment_default"]
    assert data["embedding"]["active_id"]
    assert data["whisper"]["active_id"]
    assert "note" in data


def test_llm_settings_get_defaults(api_client: TestClient):
    r = api_client.get("/api/settings/llm")
    assert r.status_code == 200
    j = r.json()
    assert j["effective_model_id"] == j["environment_model_id"]
    assert j["stored_model_id"] is None
    assert j["effective_max_new_tokens"] == j["environment_max_new_tokens"]


def test_llm_settings_patch_and_clear(api_client: TestClient):
    r = api_client.patch("/api/settings/llm", json={"model_id": "mlx-community/test-llm-override"})
    assert r.status_code == 200
    j = r.json()
    assert j["stored_model_id"] == "mlx-community/test-llm-override"
    assert j["effective_model_id"] == "mlx-community/test-llm-override"

    r2 = api_client.get("/api/models")
    assert r2.json()["llm"]["active_id"] == "mlx-community/test-llm-override"

    r3 = api_client.patch("/api/settings/llm", json={"model_id": None})
    assert r3.status_code == 200
    assert r3.json()["stored_model_id"] is None
    assert r3.json()["effective_model_id"] == r3.json()["environment_model_id"]
