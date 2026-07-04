# Author: Member C — API tests
# Purpose: Test /health and /predict endpoints

"""Tests for Member C FastAPI service (Stages 05–06)."""

import sys
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def sample_payload() -> dict[str, float]:
    return {
        "response_time_ms": 850.0,
        "status_code": 500.0,
        "error_rate": 0.12,
        "latency_p95_ms": 1200.0,
        "request_count": 4200.0,
        "cpu_usage_percent": 78.0,
        "memory_usage_percent": 81.0,
    }


@pytest.fixture()
def trained_model_path(tmp_path: Path) -> Path:
    from scripts.generate_sample_data import generate_monitoring_data
    from src.features.build_features import prepare_training_data
    from src.models.train import train_model
    from src.utils.config import load_model_config

    df = generate_monitoring_data(n_samples=200, random_state=42)
    config = load_model_config()
    X_train, _, y_train, _ = prepare_training_data(df, random_state=42)
    model = train_model(X_train, y_train, config)

    model_path = tmp_path / "outage_model.joblib"
    joblib.dump(model, model_path)
    return model_path


@pytest.fixture()
def api_client(trained_model_path: Path) -> TestClient:
    from src.api.config import ApiSettings
    from src.api.main import create_app

    app = create_app(settings=ApiSettings(model_path=trained_model_path))
    with TestClient(app) as client:
        yield client


def test_health_returns_ok(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["feature_count"] == 7


def test_health_degraded_without_model(tmp_path):
    from src.api.config import ApiSettings
    from src.api.main import create_app

    missing = tmp_path / "missing.joblib"
    app = create_app(settings=ApiSettings(model_path=missing))
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["model_loaded"] is False


def test_predict_returns_probability(api_client, sample_payload):
    response = api_client.post("/predict", json=sample_payload)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["outage_predicted"], bool)
    assert 0.0 <= body["outage_probability"] <= 1.0


def test_predict_validates_payload(api_client):
    bad_payload = {
        "response_time_ms": -1,
        "status_code": 500,
        "error_rate": 0.12,
        "latency_p95_ms": 1200,
        "request_count": 4200,
        "cpu_usage_percent": 78,
        "memory_usage_percent": 81,
    }
    response = api_client.post("/predict", json=bad_payload)
    assert response.status_code == 422


def test_predict_unavailable_without_model(tmp_path, sample_payload):
    from src.api.config import ApiSettings
    from src.api.main import create_app

    missing = tmp_path / "missing.joblib"
    app = create_app(settings=ApiSettings(model_path=missing))
    with TestClient(app) as client:
        response = client.post("/predict", json=sample_payload)
    assert response.status_code == 503


def test_dashboard_home(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Website Outage Prediction Dashboard" in html
    assert "Run Full Local Pipeline" in html
    assert "Check Website Metrics" in html
    assert 'class="tab-nav"' in html
    assert "/docs" in html
    assert "/health" in html
    assert "/monitoring/eval-metrics" in html
    assert "/monitoring/drift-summary" in html
    assert "/monitoring/status" in html
    assert "Predict Outage Risk" in html
    assert "How to Predict Any Website" in html


def test_dashboard_static_assets(api_client):
    css = api_client.get("/static/dashboard.css")
    js = api_client.get("/static/dashboard.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "tab-nav" in css.text


def test_monitoring_status(api_client):
    response = api_client.get("/monitoring/status")
    assert response.status_code == 200
    body = response.json()
    assert body["health"] == "http://127.0.0.1:8000/health"
    assert "reports" in body
