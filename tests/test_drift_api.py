"""Tests for drift API endpoints and auto-generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
def drift_paths(tmp_path, monkeypatch):
    """Isolate drift data and report paths under tmp_path."""
    ref = tmp_path / "reference.csv"
    cur = tmp_path / "current.csv"
    out = tmp_path / "reports" / "drift"
    activity = tmp_path / "artifacts" / "reports"
    activity.mkdir(parents=True, exist_ok=True)

    from scripts.generate_sample_data import generate_monitoring_data

    df = generate_monitoring_data(n_samples=200, random_state=7)
    df.head(100).to_csv(ref, index=False)
    df.tail(80).to_csv(cur, index=False)

    def fake_paths():
        return ref, cur, out

    activity_cfg = {
        "activity_report_dir": activity,
        "observations_path": activity / "current_observations.csv",
        "current_snapshot_path": activity / "current_snapshot.csv",
        "min_observations": 5,
        "reference_path": ref,
    }

    monkeypatch.setattr("src.monitoring.drift.get_default_drift_paths", fake_paths)
    monkeypatch.setattr("src.api.drift_service.get_default_drift_paths", fake_paths)
    monkeypatch.setattr("src.monitoring.observations.get_activity_drift_config", lambda: activity_cfg)
    monkeypatch.setattr("src.api.drift_service.get_activity_drift_config", lambda: activity_cfg)
    monkeypatch.setattr("src.api.drift_service.get_activity_report_dir", lambda: activity)
    return ref, cur, activity


@pytest.fixture()
def drift_api_client(trained_model_path, drift_paths, tmp_path):
    from src.api.config import ApiSettings
    from src.api.main import create_app

    app = create_app(settings=ApiSettings(model_path=trained_model_path))
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def trained_model_path(tmp_path):
    from scripts.generate_sample_data import generate_monitoring_data
    from src.features.build_features import prepare_training_data
    from src.models.train import train_model
    from src.utils.config import load_model_config
    import joblib

    df = generate_monitoring_data(n_samples=200, random_state=42)
    config = load_model_config()
    X_train, _, y_train, _ = prepare_training_data(df, random_state=42)
    model = train_model(X_train, y_train, config)
    model_path = tmp_path / "outage_model.joblib"
    joblib.dump(model, model_path)
    return model_path


def test_get_drift_auto_generates(drift_api_client, drift_paths):
    _, _, activity = drift_paths
    summary_path = activity / "drift_summary.json"
    assert not summary_path.exists()

    response = drift_api_client.get("/drift")
    assert response.status_code == 200
    body = response.json()
    assert "generated_at" in body
    assert "drift_score" in body
    assert "drifted_columns" in body
    assert "recommendation" in body
    assert "reference_rows" in body
    assert "current_rows" in body
    assert summary_path.exists()
    assert (activity / "drift_report.html").exists()


def test_post_drift_run_regenerates(drift_api_client, drift_paths):
    _, _, activity = drift_paths
    first = drift_api_client.get("/drift")
    assert first.status_code == 200

    second = drift_api_client.post("/drift/run")
    assert second.status_code == 200
    body = second.json()
    assert body["reference_rows"] == 100
    assert body["current_rows"] == 80
    assert (activity / "drift_summary.json").exists()


def test_drift_insufficient_data_with_few_observations(drift_api_client, drift_paths, sample_payload):
    from src.monitoring.observations import append_observation

    _, _, activity = drift_paths
    features = sample_payload
    for i in range(3):
        append_observation(
            features,
            outage_predicted=False,
            outage_probability=0.1,
            source="predict",
        )

    response = drift_api_client.get("/drift")
    assert response.status_code == 200
    body = response.json()
    assert body.get("insufficient_data") is True
    assert body.get("observation_count") == 3
    assert not (activity / "drift_summary.json").exists()


def test_drift_summary_after_five_predictions(drift_api_client, drift_paths, sample_payload):
    for _ in range(5):
        resp = drift_api_client.post("/predict", json=sample_payload)
        assert resp.status_code == 200

    _, _, activity = drift_paths
    assert (activity / "current_observations.csv").exists()
    summary_path = activity / "drift_summary.json"
    assert summary_path.exists() or drift_api_client.get("/drift").json().get("insufficient_data")


def test_monitoring_drift_summary_delegates(drift_api_client):
    response = drift_api_client.get("/monitoring/drift-summary")
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "error" not in body


def test_monitoring_status_includes_drift(drift_api_client):
    response = drift_api_client.get("/monitoring/status")
    assert response.status_code == 200
    body = response.json()
    assert body["drift"] is not None
    assert "drift_score" in body["drift"]


def test_drift_returns_cached_without_force(drift_api_client, drift_paths, monkeypatch):
    _, _, activity = drift_paths
    summary_path = activity / "drift_summary.json"
    cached = {
        "generated_at": "2020-01-01T00:00:00+00:00",
        "dataset_drift": False,
        "drift_detected": False,
        "drift_score": 0.0,
        "drifted_columns": [],
        "column_drifts": {},
        "reference_rows": 1,
        "current_rows": 1,
        "summary": "Cached summary",
        "recommendation": "Continue monitoring",
        "method": "test",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(cached), encoding="utf-8")

    calls = {"count": 0}
    original = __import__("src.api.drift_service", fromlist=["execute_drift_pipeline"]).execute_drift_pipeline

    def spy(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr("src.api.drift_service.execute_drift_pipeline", spy)
    response = drift_api_client.get("/drift")
    assert response.status_code == 200
    assert response.json()["summary"] == "Cached summary"
    assert calls["count"] == 0


def test_drift_pipeline_failure_returns_503(drift_api_client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("pipeline broke")

    monkeypatch.setattr("src.api.drift_service.execute_drift_pipeline", boom)
    response = drift_api_client.post("/drift/run")
    assert response.status_code == 503
    assert "pipeline broke" in response.json()["detail"]
