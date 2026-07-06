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
def activity_paths(tmp_path, monkeypatch, trained_model_path):
    """Activity drift paths for predict observation tests."""
    from scripts.generate_sample_data import generate_monitoring_data

    activity = tmp_path / "artifacts" / "reports"
    activity.mkdir(parents=True, exist_ok=True)
    ref = tmp_path / "reference.csv"
    df = generate_monitoring_data(n_samples=100, random_state=3)
    df.head(50).to_csv(ref, index=False)

    activity_cfg = {
        "activity_report_dir": activity,
        "observations_path": activity / "current_observations.csv",
        "current_snapshot_path": activity / "current_snapshot.csv",
        "min_observations": 5,
        "reference_path": ref,
    }
    monkeypatch.setattr("src.monitoring.observations.get_activity_drift_config", lambda: activity_cfg)
    monkeypatch.setattr("src.api.drift_service.get_activity_drift_config", lambda: activity_cfg)
    monkeypatch.setattr("src.api.drift_service.get_activity_report_dir", lambda: activity)
    return activity


@pytest.fixture()
def api_client(trained_model_path: Path, activity_paths) -> TestClient:
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
    assert body.get("drift") is not None
    assert "insufficient_data" in body["drift"]


def test_predict_appends_observation(api_client, sample_payload, activity_paths):
    api_client.post("/predict", json=sample_payload)
    obs_path = activity_paths / "current_observations.csv"
    assert obs_path.exists()
    content = obs_path.read_text(encoding="utf-8")
    assert "observed_at" in content
    assert "predict" in content


def test_predict_succeeds_when_drift_hook_fails(api_client, sample_payload, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("drift broke")

    monkeypatch.setattr("src.api.main.try_update_drift_after_activity", boom)
    monkeypatch.setattr("src.api.main.append_observation", boom)
    response = api_client.post("/predict", json=sample_payload)
    assert response.status_code == 200
    assert "outage_probability" in response.json()


def test_check_url_appends_observation_when_model_loaded(api_client, activity_paths, monkeypatch):
    from src.api.schemas import UrlMetricsResponse

    fake_metrics = UrlMetricsResponse(
        response_time_ms=120.0,
        status_code=200.0,
        error_rate=0.0,
        latency_p95_ms=150.0,
        request_count=5.0,
        cpu_usage_percent=50.0,
        memory_usage_percent=50.0,
        note="ok",
    )
    monkeypatch.setattr("src.api.local_dashboard.probe_url_metrics", lambda _url: fake_metrics)
    monkeypatch.setattr("src.api.local_dashboard.validate_public_url", lambda url: url)

    response = api_client.post("/check-url-metrics", json={"url": "https://example.com"})
    assert response.status_code == 200
    obs_path = activity_paths / "current_observations.csv"
    assert obs_path.exists()
    assert "url_check" in obs_path.read_text(encoding="utf-8")


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
    assert 'class="tab-nav__link' in html
    assert 'tab-nav__icon' in html
    assert 'aria-label="Dashboard"' in html
    assert 'href="#url-check"' in html
    assert 'href="#predict"' in html
    assert 'id="system-apis"' in html
    assert 'href="#system-apis"' in html
    assert 'data-panel="system-apis"' in html
    assert "System APIs" in html
    assert "/docs" in html
    assert "/health" in html
    assert "/monitoring/eval-metrics" in html
    assert 'id="drift-summary"' in html
    assert "btn-refresh-drift" in html
    assert "drift-summary-grid" in html
    assert 'href="#drift-summary"' in html
    assert "drift-insufficient" in html
    assert "Open HTML Drift Report" in html
    assert "/monitoring/status" in html
    assert "Predict Outage Risk" in html
    assert "How to Predict Any Website" in html


def test_dashboard_has_about_section(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="about"' in html
    assert 'href="#about"' in html
    assert 'href="#dashboard"' in html
    assert 'id="dashboard"' in html
    assert "Real-World Workflow" in html
    assert "url-history-list" in html
    assert 'class="tab-panel"' in html
    assert 'id="about-faq"' in html
    assert "Frequently Asked Questions" in html
    assert "<dt>What is Website Outage Prediction?</dt>" in html


def test_dashboard_static_assets(api_client):
    css = api_client.get("/static/dashboard.css")
    js = api_client.get("/static/dashboard.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "tab-nav" in css.text
    assert "tab-nav__link" in css.text
    assert "prefers-reduced-motion" in css.text


def test_monitoring_status(api_client):
    response = api_client.get("/monitoring/status")
    assert response.status_code == 200
    body = response.json()
    assert body["health"] == "http://127.0.0.1:8000/health"
    assert "reports" in body


def test_openapi_json_available(api_client):
    response = api_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "Website Outage Prediction" in schema["info"]["title"]
    paths = schema["paths"]
    assert "/health" in paths
    assert "/predict" in paths
    assert "/check-url-metrics" in paths


def test_openapi_tags_grouped(api_client):
    schema = api_client.get("/openapi.json").json()
    health_tags = schema["paths"]["/health"]["get"]["tags"]
    predict_tags = schema["paths"]["/predict"]["post"]["tags"]
    url_tags = schema["paths"]["/check-url-metrics"]["post"]["tags"]
    assert health_tags == ["System"]
    assert predict_tags == ["Prediction"]
    assert url_tags == ["Website Health"]


def test_custom_docs_page(api_client):
    response = api_client.get("/docs")
    assert response.status_code == 200
    html = response.text
    assert "Website Outage Prediction API" in html
    assert "/static/swagger-theme.css" in html
    assert 'href="/health"' in html
    assert "swagger-ui-bundle.js" in html


def test_swagger_theme_css(api_client):
    response = api_client.get("/static/swagger-theme.css")
    assert response.status_code == 200
    assert "platform-header" in response.text
