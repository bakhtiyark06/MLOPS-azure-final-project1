"""Tests for Member D monitoring: telemetry and drift detection."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.generate_sample_data import generate_monitoring_data
from src.monitoring.drift import (
    DriftResult,
    get_default_drift_paths,
    load_drift_datasets,
    write_drift_summary,
)
from src.monitoring.telemetry import get_app_insights_connection_string, setup_telemetry


@pytest.fixture
def drift_csvs(tmp_path):
    """Create minimal reference and current CSVs for drift tests."""
    df = generate_monitoring_data(n_samples=200, random_state=42)
    ref_path = tmp_path / "reference.csv"
    cur_path = tmp_path / "current.csv"
    df.head(100).to_csv(ref_path, index=False)
    df.tail(80).to_csv(cur_path, index=False)
    return ref_path, cur_path


def test_get_default_drift_paths():
    ref, cur, out = get_default_drift_paths()
    assert ref.name == "reference.csv"
    assert cur.name == "current.csv"
    assert out.name == "drift"


def test_load_drift_datasets(drift_csvs):
    ref_path, cur_path = drift_csvs
    ref_df, cur_df, features = load_drift_datasets(ref_path, cur_path)
    assert len(features) == 7
    assert list(ref_df.columns) == features
    assert len(ref_df) == 100
    assert len(cur_df) == 80


def test_load_drift_datasets_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_drift_datasets(tmp_path / "missing.csv", tmp_path / "also_missing.csv")


def test_write_drift_summary(tmp_path):
    result = DriftResult(
        drift_detected=True,
        report_path=tmp_path / "drift_report.html",
        json_path=tmp_path / "drift_report.json",
        dataset_drift=True,
        column_drifts={"error_rate": True},
        summary="Drift in error_rate",
    )
    out = write_drift_summary(result, tmp_path / "summary.json")
    payload = json.loads(out.read_text())
    assert payload["drift_detected"] is True
    assert payload["column_drifts"]["error_rate"] is True


def test_setup_telemetry_skips_without_connection_string(monkeypatch):
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    assert setup_telemetry() is False


def test_get_app_insights_connection_string(monkeypatch):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")
    assert get_app_insights_connection_string() == "InstrumentationKey=test"


def test_setup_telemetry_configures_when_set(monkeypatch):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")
    import sys
    import types

    import src.monitoring.telemetry as telemetry_module

    telemetry_module._telemetry_configured = False
    calls: list[dict] = []

    def fake_configure(**kwargs):
        calls.append(kwargs)

    fake_module = types.SimpleNamespace(configure_azure_monitor=fake_configure)
    monkeypatch.setitem(sys.modules, "azure.monitor.opentelemetry", fake_module)

    assert setup_telemetry() is True
    assert len(calls) == 1
    assert calls[0]["connection_string"] == "InstrumentationKey=test"


def test_openrouter_build_prompts():
    from src.monitoring.llm_prompts import build_eval_prompt, build_failure_prompt

    metrics = {
        "f1_score": 0.82,
        "accuracy": 0.85,
        "gate_passed": True,
        "thresholds": {"min_f1_score": 0.75, "min_accuracy": 0.8},
    }
    drift = {"drift_detected": True, "summary": "Drift detected", "column_drifts": {}}
    assert "f1_score" in build_eval_prompt(metrics, drift)
    assert "gate" in build_failure_prompt({**metrics, "gate_passed": False}, drift).lower()


def test_deploy_aks_gate_check_blocks(tmp_path):
    from infra.deploy_aks import check_quality_gate

    bad_metrics = tmp_path / "eval_metrics.json"
    bad_metrics.write_text(json.dumps({"gate_passed": False, "gate_failure_reasons": ["low f1"]}))
    assert check_quality_gate(bad_metrics) is False

    good_metrics = tmp_path / "good.json"
    good_metrics.write_text(json.dumps({"gate_passed": True}))
    assert check_quality_gate(good_metrics) is True


def test_deploy_aks_render_manifest():
    from infra.deploy_aks import render_manifest

    template = Path(__file__).resolve().parents[1] / "infra" / "k8s" / "deployment.yaml"
    rendered = render_manifest(template, {"IMAGE": "test.azurecr.io/app:v1", "APPLICATIONINSIGHTS_CONNECTION_STRING": ""})
    assert "test.azurecr.io/app:v1" in rendered
    assert "${IMAGE}" not in rendered


def test_run_drift_check_integration(drift_csvs, tmp_path):
    """Run Evidently drift check on synthetic data."""
    from src.monitoring.drift import run_drift_check

    ref_path, cur_path = drift_csvs
    result = run_drift_check(ref_path, cur_path, tmp_path / "reports")
    assert result.report_path.exists()
    assert result.json_path.exists()
    assert isinstance(result.drift_detected, bool)
    assert isinstance(result.summary, str)
