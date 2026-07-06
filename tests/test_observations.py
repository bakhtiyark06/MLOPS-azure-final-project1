"""Tests for demo production observation log."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.generate_sample_data import generate_monitoring_data
from src.data.preprocess import get_feature_columns


@pytest.fixture()
def obs_paths(tmp_path, monkeypatch):
    activity_dir = tmp_path / "artifacts" / "reports"
    activity_dir.mkdir(parents=True, exist_ok=True)
    ref = tmp_path / "data" / "reference" / "reference.csv"
    ref.parent.mkdir(parents=True, exist_ok=True)
    df = generate_monitoring_data(n_samples=100, random_state=1)
    df.head(50).to_csv(ref, index=False)

    cfg = {
        "activity_report_dir": activity_dir,
        "observations_path": activity_dir / "current_observations.csv",
        "current_snapshot_path": activity_dir / "current_snapshot.csv",
        "min_observations": 5,
        "reference_path": ref,
    }

    monkeypatch.setattr(
        "src.monitoring.observations.get_activity_drift_config",
        lambda: cfg,
    )
    monkeypatch.setattr(
        "src.api.drift_service.get_activity_drift_config",
        lambda: cfg,
    )
    return cfg


def test_append_observation_creates_file(obs_paths):
    from src.monitoring.observations import append_observation, observation_count

    features = {col: 1.0 for col in get_feature_columns()}
    features["response_time_ms"] = 200.0
    path = append_observation(
        features,
        outage_predicted=False,
        outage_probability=0.2,
        source="predict",
    )
    assert path.exists()
    assert observation_count() == 1


def test_build_current_snapshot(obs_paths):
    from src.monitoring.observations import append_observation, build_current_snapshot

    features = {col: float(i) for i, col in enumerate(get_feature_columns())}
    for i in range(3):
        append_observation(
            features,
            outage_predicted=False,
            outage_probability=0.1 * i,
            source="predict",
        )
    snap = build_current_snapshot()
    df = pd.read_csv(snap)
    assert len(df) == 3
    assert list(df.columns) == get_feature_columns()


def test_observation_count_zero_when_missing(obs_paths):
    from src.monitoring.observations import observation_count

    assert observation_count() == 0
