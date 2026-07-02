# Author: Member B — unit tests for training, evaluation, and registry
# Purpose: Test quality gate, training artifacts, and registry gating

"""Tests for Member B training pipeline (Stages 02–04)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import joblib
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_df():
    """Synthetic monitoring data for training tests."""
    from scripts.generate_sample_data import generate_monitoring_data

    return generate_monitoring_data(n_samples=200, random_state=42)


@pytest.fixture
def model_config():
    """Load model config from YAML."""
    from src.utils.config import load_model_config

    return load_model_config()


def test_build_model_from_config(model_config):
    """RandomForest should match hyperparameters from config."""
    from src.models.train import build_model

    model = build_model(model_config)
    assert isinstance(model, RandomForestClassifier)
    assert model.n_estimators == model_config["model"]["n_estimators"]
    assert model.max_depth == model_config["model"]["max_depth"]
    assert model.random_state == model_config["model"]["random_state"]


def test_prepare_training_data(sample_df):
    """Feature prep should return train/test splits with correct shapes."""
    from src.features.build_features import prepare_training_data
    from src.data.preprocess import get_feature_columns

    X_train, X_test, y_train, y_test = prepare_training_data(sample_df)
    n_features = len(get_feature_columns())
    assert X_train.shape[1] == n_features
    assert X_test.shape[1] == n_features
    assert len(y_train) == len(X_train)
    assert len(y_test) == len(X_test)
    assert len(X_train) + len(X_test) > 0


def test_train_and_save_artifacts(sample_df, model_config, tmp_path):
    """Training should write joblib model and test set CSV."""
    from src.features.build_features import prepare_training_data
    from src.models.train import save_artifacts, train_model

    X_train, X_test, y_train, y_test = prepare_training_data(sample_df)
    model = train_model(X_train, y_train, model_config)

    model_path = tmp_path / "model.joblib"
    test_path = tmp_path / "test_set.csv"
    save_artifacts(model, X_test, y_test, model_path, test_path)

    assert model_path.exists()
    assert test_path.exists()
    loaded = joblib.load(model_path)
    assert hasattr(loaded, "predict")
    test_df = pd.read_csv(test_path)
    assert "outage_within_1h" in test_df.columns


def test_quality_gate_pass(model_config):
    """Metrics above thresholds should pass the gate."""
    from src.models.evaluate import run_quality_gate

    metrics = {"f1_score": 0.90, "accuracy": 0.92}
    passed, reasons = run_quality_gate(metrics, model_config)
    assert passed is True
    assert reasons == []


def test_quality_gate_fail(model_config):
    """Metrics below thresholds should fail the gate."""
    from src.models.evaluate import run_quality_gate

    metrics = {"f1_score": 0.50, "accuracy": 0.60}
    passed, reasons = run_quality_gate(metrics, model_config)
    assert passed is False
    assert len(reasons) == 2


def test_write_eval_metrics(tmp_path, model_config):
    """Eval metrics JSON should include gate_passed and thresholds."""
    from src.models.evaluate import write_eval_metrics

    metrics = {"f1_score": 0.88, "accuracy": 0.91}
    out_path = tmp_path / "eval_metrics.json"
    payload = write_eval_metrics(out_path, metrics, gate_passed=True)

    assert out_path.exists()
    assert payload["gate_passed"] is True
    assert payload["thresholds"]["min_f1_score"] == model_config["quality_gate"]["min_f1_score"]


def test_load_model_and_test_set(sample_df, model_config, tmp_path):
    """Evaluation loader should restore model and test data."""
    from src.features.build_features import prepare_training_data
    from src.models.evaluate import compute_metrics, load_model_and_test_set
    from src.models.train import save_artifacts, train_model

    X_train, X_test, y_train, y_test = prepare_training_data(sample_df)
    model = train_model(X_train, y_train, model_config)
    model_path = tmp_path / "model.joblib"
    test_path = tmp_path / "test_set.csv"
    save_artifacts(model, X_test, y_test, model_path, test_path)

    loaded_model, X_loaded, y_loaded = load_model_and_test_set(model_path, test_path)
    preds = loaded_model.predict(X_loaded)
    metrics = compute_metrics(y_loaded, preds)
    assert "f1_score" in metrics
    assert "accuracy" in metrics


def test_evaluate_force_fail(sample_df, model_config, tmp_path):
    """--force-fail should write gate_passed=false with demo flag."""
    from src.features.build_features import prepare_training_data
    from src.models.evaluate import write_eval_metrics
    from src.models.train import save_artifacts, train_model

    X_train, X_test, y_train, y_test = prepare_training_data(sample_df)
    model = train_model(X_train, y_train, model_config)
    model_path = tmp_path / "model.joblib"
    test_path = tmp_path / "test_set.csv"
    eval_path = tmp_path / "eval_metrics.json"
    save_artifacts(model, X_test, y_test, model_path, test_path)

    from src.models.evaluate import compute_metrics, load_model_and_test_set

    loaded_model, X_loaded, y_loaded = load_model_and_test_set(model_path, test_path)
    metrics = compute_metrics(y_loaded, loaded_model.predict(X_loaded))
    payload = write_eval_metrics(
        eval_path,
        metrics,
        gate_passed=False,
        gate_reasons=["--force-fail demo flag set"],
        force_fail=True,
    )

    assert payload["gate_passed"] is False
    assert payload.get("force_fail_demo") is True


def test_register_blocked_when_gate_failed(tmp_path):
    """Registry should refuse registration when gate_passed is false."""
    from src.models.registry import QualityGateError, register_model

    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"fake")
    eval_path = tmp_path / "eval_metrics.json"
    eval_path.write_text(
        json.dumps({"f1_score": 0.5, "accuracy": 0.5, "gate_passed": False}),
        encoding="utf-8",
    )

    with pytest.raises(QualityGateError):
        register_model(model_path, eval_path, dataset_hash="abc123", dry_run=True)


def test_register_dry_run_passes(tmp_path):
    """Dry run should succeed when gate passed."""
    from src.models.registry import register_model

    model_path = tmp_path / "model.joblib"
    joblib.dump(RandomForestClassifier(n_estimators=2), model_path)
    eval_path = tmp_path / "eval_metrics.json"
    eval_path.write_text(
        json.dumps({"f1_score": 0.9, "accuracy": 0.9, "gate_passed": True}),
        encoding="utf-8",
    )

    result = register_model(
        model_path, eval_path, dataset_hash="abc123def", dry_run=True
    )
    assert result["dry_run"] is True
    assert result["tags"]["dataset_hash"] == "abc123def"


@patch("src.models.registry.get_azure_configuration_status")
@patch("src.models.registry.get_ml_client")
def test_register_model_azure(mock_get_client, mock_status, tmp_path):
    """Azure registration should call MLClient.models.create_or_update."""
    mock_status.return_value = {
        "configured": True,
        "missing_env_vars": [],
        "config": {
            "subscription_id": "sub-123",
            "resource_group": "rg-test",
            "workspace_name": "mlw-test",
            "model_registry_name": "website-outage-model",
        },
    }
    mock_model_entity = MagicMock()
    mock_ml_module = MagicMock()
    mock_ml_module.entities.Model.return_value = mock_model_entity

    mock_client = MagicMock()
    mock_registered = MagicMock()
    mock_registered.version = "1"
    mock_registered.id = "/subscriptions/test/models/website-outage-model/versions/1"
    mock_client.models.create_or_update.return_value = mock_registered
    mock_get_client.return_value = mock_client

    model_path = tmp_path / "model.joblib"
    joblib.dump(RandomForestClassifier(n_estimators=2), model_path)
    eval_path = tmp_path / "eval_metrics.json"
    eval_path.write_text(
        json.dumps({"f1_score": 0.9, "accuracy": 0.9, "gate_passed": True}),
        encoding="utf-8",
    )

    import sys

    mock_azure_ai = MagicMock()
    mock_azure_ai.ml.entities.Model = mock_ml_module.entities.Model
    with patch.dict(sys.modules, {"azure.ai.ml": mock_azure_ai.ml, "azure.ai.ml.entities": mock_azure_ai.ml.entities}):
        from src.models.registry import register_model

        result = register_model(model_path, eval_path, dataset_hash="hash123", dry_run=False)

    assert result["version"] == "1"
    assert result["tags"]["stage"] == "approved"
    mock_client.models.create_or_update.assert_called_once()


def test_register_graceful_skip_without_azure(tmp_path, monkeypatch):
    """Registration should skip gracefully when Azure is not configured."""
    from src.models.registry import register_model

    monkeypatch.setattr(
        "src.models.registry.get_azure_configuration_status",
        lambda: {
            "configured": False,
            "missing_env_vars": [
                "AZURE_SUBSCRIPTION_ID",
                "AZURE_RESOURCE_GROUP",
                "AZURE_WORKSPACE_NAME",
            ],
            "config": None,
        },
    )

    model_path = tmp_path / "model.joblib"
    joblib.dump(RandomForestClassifier(n_estimators=2), model_path)
    eval_path = tmp_path / "eval_metrics.json"
    eval_path.write_text(
        json.dumps({"f1_score": 0.9, "accuracy": 0.9, "gate_passed": True}),
        encoding="utf-8",
    )

    result = register_model(model_path, eval_path, dataset_hash="hash123", dry_run=False)
    assert result["skipped"] is True
    assert "Skipping Azure Model Registry registration" in result["message"]


def test_load_azure_config_from_env(monkeypatch, tmp_path):
    """Env vars should take priority over YAML files."""
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub-env")
    monkeypatch.setenv("AZURE_RESOURCE_GROUP", "rg-env")
    monkeypatch.setenv("AZURE_WORKSPACE_NAME", "mlw-env")
    monkeypatch.setattr("src.utils.config.get_project_root", lambda: tmp_path)

    from src.utils.config import is_azure_configured, load_azure_config

    cfg = load_azure_config()
    assert cfg is not None
    assert cfg["subscription_id"] == "sub-env"
    assert cfg["resource_group"] == "rg-env"
    assert cfg["workspace_name"] == "mlw-env"
    assert is_azure_configured(cfg) is True


def test_load_azure_config_example_not_for_registration(monkeypatch, tmp_path):
    """Example YAML should load but not be treated as configured."""
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "azure_config.example.yaml").write_text(
        "subscription_id: ${AZURE_SUBSCRIPTION_ID}\n"
        "resource_group: <your-rg>\n"
        "workspace_name: <your-ml-workspace>\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    monkeypatch.delenv("AZURE_RESOURCE_GROUP", raising=False)
    monkeypatch.delenv("AZURE_WORKSPACE_NAME", raising=False)
    monkeypatch.setattr("src.utils.config.get_project_root", lambda: tmp_path)

    from src.utils.config import is_azure_configured, load_azure_config

    cfg = load_azure_config()
    assert cfg is not None
    assert cfg["source"] == "example"
    assert is_azure_configured(cfg) is False


def test_load_azure_config_returns_none_when_missing(monkeypatch, tmp_path):
    """No env, local, or example config should return None."""
    configs = tmp_path / "configs"
    configs.mkdir()
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    monkeypatch.delenv("AZURE_RESOURCE_GROUP", raising=False)
    monkeypatch.delenv("AZURE_WORKSPACE_NAME", raising=False)
    monkeypatch.setattr("src.utils.config.get_project_root", lambda: tmp_path)

    from src.utils.config import load_azure_config

    assert load_azure_config() is None


def test_load_dataset_hash_from_metadata(tmp_path, monkeypatch):
    """Dataset hash should load from ingestion_metadata.json."""
    from src.models.registry import load_dataset_hash

    meta_dir = tmp_path / "data" / "raw"
    meta_dir.mkdir(parents=True)
    (meta_dir / "ingestion_metadata.json").write_text(
        json.dumps({"dataset_hash": "deadbeef"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.models.registry.get_project_root",
        lambda: tmp_path,
    )
    assert load_dataset_hash() == "deadbeef"


@patch("scripts.train_model.mlflow")
def test_train_model_script_main(mock_mlflow, sample_df, tmp_path, monkeypatch):
    """train_model.py main should train and return exit 0."""
    from scripts.generate_sample_data import generate_monitoring_data

    raw_path = tmp_path / "data" / "raw" / "website_monitoring.csv"
    raw_path.parent.mkdir(parents=True)
    generate_monitoring_data(n_samples=200).to_csv(raw_path, index=False)

    meta_dir = tmp_path / "data" / "raw"
    (meta_dir / "dataset_hash.txt").write_text("abc123", encoding="utf-8")

    models_dir = tmp_path / "models"
    processed_dir = tmp_path / "data" / "processed"

    import scripts.train_model as train_module

    monkeypatch.setattr(sys, "argv", ["train_model.py"])
    monkeypatch.setattr(
        train_module,
        "get_default_artifact_paths",
        lambda: (models_dir / "outage_model.joblib", processed_dir / "test_set.csv"),
    )
    monkeypatch.setattr(train_module, "get_project_root", lambda: tmp_path)
    monkeypatch.setattr(train_module, "_read_dataset_hash_safe", lambda: "abc123")
    monkeypatch.setattr(train_module, "_setup_mlflow", lambda: "test-exp")
    mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=None)
    mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(train_module, "load_raw_data", lambda path=None: sample_df)
    assert train_module.main() == 0
    assert (models_dir / "outage_model.joblib").exists()


def test_evaluate_model_script_pass(sample_df, model_config, tmp_path, monkeypatch):
    """evaluate_model.py should return 0 when gate passes."""
    from src.features.build_features import prepare_training_data
    from src.models.train import save_artifacts, train_model

    X_train, X_test, y_train, y_test = prepare_training_data(sample_df)
    model = train_model(X_train, y_train, model_config)
    model_path = tmp_path / "model.joblib"
    test_path = tmp_path / "test_set.csv"
    eval_path = tmp_path / "eval_metrics.json"
    save_artifacts(model, X_test, y_test, model_path, test_path)

    import scripts.evaluate_model as eval_module

    monkeypatch.setattr(sys, "argv", ["evaluate_model.py"])
    monkeypatch.setattr(
        eval_module,
        "get_default_eval_paths",
        lambda: (model_path, test_path, eval_path),
    )
    assert eval_module.main() == 0
    assert json.loads(eval_path.read_text(encoding="utf-8"))["gate_passed"] is True


def test_evaluate_model_script_force_fail(sample_df, model_config, tmp_path, monkeypatch):
    """evaluate_model.py --force-fail should return exit 1."""
    from src.features.build_features import prepare_training_data
    from src.models.train import save_artifacts, train_model

    X_train, X_test, y_train, y_test = prepare_training_data(sample_df)
    model = train_model(X_train, y_train, model_config)
    model_path = tmp_path / "model.joblib"
    test_path = tmp_path / "test_set.csv"
    eval_path = tmp_path / "eval_metrics.json"
    save_artifacts(model, X_test, y_test, model_path, test_path)

    import scripts.evaluate_model as eval_module

    monkeypatch.setattr(sys, "argv", ["evaluate_model.py", "--force-fail"])
    monkeypatch.setattr(
        eval_module,
        "get_default_eval_paths",
        lambda: (model_path, test_path, eval_path),
    )
    assert eval_module.main() == 1


def test_register_model_script_dry_run(tmp_path, monkeypatch):
    """register_model.py --dry-run should return 0 when gate passed."""
    model_path = tmp_path / "models" / "outage_model.joblib"
    model_path.parent.mkdir(parents=True)
    joblib.dump(RandomForestClassifier(n_estimators=2), model_path)
    eval_path = tmp_path / "data" / "processed" / "eval_metrics.json"
    eval_path.parent.mkdir(parents=True)
    eval_path.write_text(
        json.dumps({"f1_score": 0.9, "accuracy": 0.9, "gate_passed": True}),
        encoding="utf-8",
    )

    import scripts.register_model as reg_module

    monkeypatch.setattr(sys, "argv", ["register_model.py", "--dry-run"])
    monkeypatch.setattr(
        reg_module,
        "get_default_eval_paths",
        lambda: (model_path, tmp_path / "test.csv", eval_path),
    )
    monkeypatch.setattr(reg_module, "load_dataset_hash", lambda: "hash456")
    assert reg_module.main() == 0


def test_register_model_script_graceful_skip(tmp_path, monkeypatch, capsys):
    """register_model.py should skip gracefully without Azure configuration."""
    model_path = tmp_path / "models" / "outage_model.joblib"
    model_path.parent.mkdir(parents=True)
    joblib.dump(RandomForestClassifier(n_estimators=2), model_path)
    eval_path = tmp_path / "data" / "processed" / "eval_metrics.json"
    eval_path.parent.mkdir(parents=True)
    eval_path.write_text(
        json.dumps({"f1_score": 0.9, "accuracy": 0.9, "gate_passed": True}),
        encoding="utf-8",
    )

    import scripts.register_model as reg_module

    monkeypatch.setattr(sys, "argv", ["register_model.py"])
    monkeypatch.setattr(
        reg_module,
        "get_default_eval_paths",
        lambda: (model_path, tmp_path / "test.csv", eval_path),
    )
    monkeypatch.setattr(reg_module, "load_dataset_hash", lambda: "hash456")
    monkeypatch.setattr(
        "src.models.registry.get_azure_configuration_status",
        lambda: {
            "configured": False,
            "missing_env_vars": [
                "AZURE_SUBSCRIPTION_ID",
                "AZURE_RESOURCE_GROUP",
                "AZURE_WORKSPACE_NAME",
            ],
            "config": None,
        },
    )

    assert reg_module.main() == 0
    captured = capsys.readouterr().out
    assert "Skipping Azure Model Registry registration" in captured
