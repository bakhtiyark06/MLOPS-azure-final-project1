# Author: Member D — dashboard demo workflow tests
# Purpose: Test system status, URL check, and local pipeline endpoints

"""Tests for dashboard demo control center endpoints."""

import sys
from pathlib import Path
from unittest.mock import patch

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


@pytest.fixture()
def isolated_history(tmp_path: Path):
    from src.api import url_check_history

    history_file = tmp_path / "url_check_history.json"
    url_check_history.set_history_path(history_file)
    yield history_file
    url_check_history.set_history_path(None)


@pytest.fixture()
def api_client_with_history(trained_model_path: Path, isolated_history: Path) -> TestClient:
    from src.api.config import ApiSettings
    from src.api.main import create_app

    app = create_app(settings=ApiSettings(model_path=trained_model_path))
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def isolated_url_history(tmp_path: Path):
    from src.api import url_check_history

    history_file = tmp_path / "url_check_history.json"
    url_check_history.set_history_path(history_file)
    yield history_file
    url_check_history.set_history_path(None)


def test_system_status_endpoint(api_client):
    response = api_client.get("/system-status")
    assert response.status_code == 200
    body = response.json()
    assert "api_health" in body
    assert "model_loaded" in body
    assert "data_exists" in body
    assert "model_file_exists" in body
    assert "eval_status" in body


def test_run_local_pipeline_endpoint_returns_json(api_client):
    mock_result = {
        "status": "success",
        "steps": [{"name": "Generate data", "status": "passed"}],
        "message": "Local pipeline completed successfully.",
    }
    with patch("src.api.local_dashboard.run_local_pipeline", return_value=mock_result):
        response = api_client.post("/run-local-pipeline")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["steps"][0]["name"] == "Generate data"


def test_check_url_metrics_blocks_localhost(api_client):
    response = api_client.post("/check-url-metrics", json={"url": "http://localhost/"})
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"].lower()


def test_check_url_metrics_blocks_private_ip(api_client):
    response = api_client.post("/check-url-metrics", json={"url": "http://127.0.0.1/health"})
    assert response.status_code == 400


def test_check_url_metrics_blocks_metadata_ip(api_client):
    response = api_client.post("/check-url-metrics", json={"url": "http://169.254.169.254/"})
    assert response.status_code == 400


def test_check_url_metrics_requires_http_scheme(api_client):
    response = api_client.post("/check-url-metrics", json={"url": "ftp://example.com"})
    assert response.status_code == 400


def test_check_url_metrics_returns_probe_data(api_client):
    from src.api.schemas import UrlMetricsResponse

    mock_metrics = UrlMetricsResponse(
        response_time_ms=120.5,
        status_code=200,
        error_rate=0.0,
        latency_p95_ms=150.0,
        request_count=5,
        cpu_usage_percent=50,
        memory_usage_percent=50,
        note="demo note",
    )
    with (
        patch("src.api.local_dashboard.validate_public_url", return_value="https://example.com"),
        patch("src.api.local_dashboard.probe_url_metrics", return_value=mock_metrics),
    ):
        response = api_client.post("/check-url-metrics", json={"url": "https://example.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["status_code"] == 200
    assert body["cpu_usage_percent"] == 50
    assert body["memory_usage_percent"] == 50
    assert "note" in body


def test_validate_public_url_accepts_https():
    from src.api.url_checker import validate_public_url

    with patch(
        "src.api.url_checker.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    ):
        url = validate_public_url("https://example.com")
    assert url == "https://example.com"


def test_probe_url_metrics_accesses_elapsed_after_read():
    """probe_url_metrics must not access httpx elapsed before response is consumed."""
    from datetime import timedelta
    from unittest.mock import MagicMock

    from src.api.url_checker import probe_url_metrics

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.elapsed = timedelta(milliseconds=100)

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    with patch("src.api.url_checker.httpx.Client", return_value=mock_client):
        result = probe_url_metrics("https://example.com")

    assert mock_client.get.call_count == 5
    assert result.status_code == 200
    assert result.response_time_ms == 100.0
    assert result.cpu_usage_percent == 50.0


def test_dashboard_contains_workflow_controls(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Website Outage Prediction Dashboard" in html
    assert "Run Full Local Pipeline" in html
    assert "Check Website Metrics" in html
    assert "Predict Outage Risk" in html
    assert "Refresh System Status" in html
    assert 'class="tab-nav"' in html
    assert "/docs" in html
    assert "/health" in html


def test_url_check_history_appends_on_success(api_client_with_history):
    from src.api.schemas import UrlMetricsResponse

    mock_metrics = UrlMetricsResponse(
        response_time_ms=120.5,
        status_code=200,
        error_rate=0.0,
        latency_p95_ms=150.0,
        request_count=5,
        cpu_usage_percent=50,
        memory_usage_percent=50,
        note="demo note",
    )
    with (
        patch("src.api.local_dashboard.validate_public_url", return_value="https://example.com"),
        patch("src.api.local_dashboard.probe_url_metrics", return_value=mock_metrics),
    ):
        response = api_client_with_history.post(
            "/check-url-metrics", json={"url": "https://example.com"}
        )
    assert response.status_code == 200

    history = api_client_with_history.get("/url-check-history").json()
    assert len(history["items"]) == 1
    assert history["items"][0]["url"] == "https://example.com"
    assert history["items"][0]["status_code"] == 200


def test_url_check_history_not_appended_on_validation_error(api_client_with_history):
    response = api_client_with_history.post("/check-url-metrics", json={"url": "http://localhost/"})
    assert response.status_code == 400
    history = api_client_with_history.get("/url-check-history").json()
    assert history["items"] == []


def test_clear_url_check_history(api_client_with_history):
    from src.api.schemas import UrlMetricsResponse

    mock_metrics = UrlMetricsResponse(
        response_time_ms=100.0,
        status_code=200,
        error_rate=0.0,
        latency_p95_ms=120.0,
        request_count=5,
        cpu_usage_percent=50,
        memory_usage_percent=50,
        note="ok",
    )
    with (
        patch("src.api.local_dashboard.validate_public_url", return_value="https://example.org"),
        patch("src.api.local_dashboard.probe_url_metrics", return_value=mock_metrics),
    ):
        api_client_with_history.post("/check-url-metrics", json={"url": "https://example.org"})

    clear_resp = api_client_with_history.delete("/url-check-history")
    assert clear_resp.status_code == 200
    assert clear_resp.json()["items"] == []
    assert api_client_with_history.get("/url-check-history").json()["items"] == []


def test_url_check_history_appends_on_success(api_client, isolated_url_history):
    from src.api.schemas import UrlMetricsResponse

    mock_metrics = UrlMetricsResponse(
        response_time_ms=120.5,
        status_code=200,
        error_rate=0.0,
        latency_p95_ms=150.0,
        request_count=5,
        cpu_usage_percent=50,
        memory_usage_percent=50,
        note="demo note",
    )
    with (
        patch("src.api.local_dashboard.validate_public_url", return_value="https://example.com"),
        patch("src.api.local_dashboard.probe_url_metrics", return_value=mock_metrics),
    ):
        response = api_client.post("/check-url-metrics", json={"url": "https://example.com"})
    assert response.status_code == 200

    history = api_client.get("/url-check-history").json()
    assert len(history["items"]) == 1
    assert history["items"][0]["url"] == "https://example.com"
    assert history["items"][0]["status_code"] == 200
    assert isolated_url_history.exists()


def test_url_check_history_not_appended_on_validation_error(api_client, isolated_url_history):
    response = api_client.post("/check-url-metrics", json={"url": "http://localhost/"})
    assert response.status_code == 400
    history = api_client.get("/url-check-history").json()
    assert history["items"] == []


def test_clear_url_check_history(api_client, isolated_url_history):
    from src.api.schemas import UrlMetricsResponse

    mock_metrics = UrlMetricsResponse(
        response_time_ms=100.0,
        status_code=200,
        error_rate=0.0,
        latency_p95_ms=120.0,
        request_count=5,
        cpu_usage_percent=50,
        memory_usage_percent=50,
        note="ok",
    )
    with (
        patch("src.api.local_dashboard.validate_public_url", return_value="https://example.org"),
        patch("src.api.local_dashboard.probe_url_metrics", return_value=mock_metrics),
    ):
        api_client.post("/check-url-metrics", json={"url": "https://example.org"})

    assert api_client.get("/url-check-history").json()["items"]

    cleared = api_client.delete("/url-check-history")
    assert cleared.status_code == 200
    assert cleared.json()["items"] == []
    assert api_client.get("/url-check-history").json()["items"] == []
