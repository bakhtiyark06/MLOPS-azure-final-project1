# Author: Member A — unit tests for data ingestion pipeline
# Purpose: Test data generation, validation, ingestion, and loading

"""Tests for Member A data pipeline (Stage 01)."""

import json  # Parse ingestion metadata
import sys  # Path setup
from pathlib import Path  # Temp files
from unittest.mock import MagicMock, patch  # Mock Azure Blob

import pandas as pd  # Test DataFrames
import pytest  # Test framework

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def valid_monitoring_df():
    """Minimal valid monitoring DataFrame matching model_config schema."""
    from scripts.generate_sample_data import generate_monitoring_data

    return generate_monitoring_data(n_samples=100, random_state=99)


def test_get_required_columns():
    """validate_data should return 7 features + 1 target column."""
    from src.data.validate_data import get_required_columns

    cols = get_required_columns()
    assert len(cols) == 8
    assert "outage_within_1h" in cols
    assert "response_time_ms" in cols


def test_validate_raw_dataframe_valid(valid_monitoring_df):
    """Valid synthetic data should pass schema validation."""
    from src.data.validate_data import validate_raw_dataframe

    is_valid, errors = validate_raw_dataframe(valid_monitoring_df)
    assert is_valid is True
    assert errors == []


def test_validate_raw_dataframe_missing_column(valid_monitoring_df):
    """Missing column should fail validation with clear error."""
    from src.data.validate_data import validate_raw_dataframe

    bad_df = valid_monitoring_df.drop(columns=["error_rate"])
    is_valid, errors = validate_raw_dataframe(bad_df)
    assert is_valid is False
    assert any("Missing columns" in e for e in errors)


def test_validate_raw_dataframe_empty():
    """Empty DataFrame should fail validation."""
    from src.data.validate_data import validate_raw_dataframe

    empty = pd.DataFrame()
    is_valid, errors = validate_raw_dataframe(empty)
    assert is_valid is False


def test_validate_raw_dataframe_invalid_target(valid_monitoring_df):
    """Target values outside 0/1 should fail validation."""
    from src.data.validate_data import validate_raw_dataframe

    bad_df = valid_monitoring_df.copy()
    bad_df["outage_within_1h"] = 2
    is_valid, errors = validate_raw_dataframe(bad_df)
    assert is_valid is False


def test_generate_sample_data_writes_files(tmp_path, monkeypatch):
    """generate_sample_data main should create raw, reference, and current files."""
    from scripts import generate_sample_data as gen_mod

    root = ROOT
    monkeypatch.setattr(sys, "argv", ["generate_sample_data.py", "--n-samples", "80"])
    assert gen_mod.main() == 0
    assert (root / "data" / "raw" / "website_monitoring.csv").exists()
    assert (root / "data" / "reference" / "reference.csv").exists()
    assert (root / "data" / "processed" / "current.csv").exists()


def test_compute_file_hash_stable(tmp_path):
    """Same file content should produce identical SHA256 hash."""
    from scripts.ingest_data import compute_file_hash

    f = tmp_path / "data.csv"
    f.write_text("col1,col2\n1,2\n", encoding="utf-8")
    assert compute_file_hash(f) == compute_file_hash(f)
    assert len(compute_file_hash(f)) == 64


def test_ingest_data_writes_metadata(monkeypatch, valid_monitoring_df):
    """ingest_data should write hash and ingestion_metadata.json."""
    from scripts import ingest_data as ingest_mod

    root = ROOT
    raw_path = root / "data" / "raw" / "website_monitoring.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    valid_monitoring_df.to_csv(raw_path, index=False)
    monkeypatch.setattr(
        sys, "argv", ["ingest_data.py", "--skip-blob", "--skip-dvc"]
    )
    assert ingest_mod.main() == 0
    assert (root / "data" / "raw" / "dataset_hash.txt").exists()
    meta_path = root / "data" / "raw" / "ingestion_metadata.json"
    assert meta_path.exists()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert "dataset_hash" in meta
    assert meta["row_count"] == len(valid_monitoring_df)
    assert meta["stage"] == "01-data-ingestion"


def test_ingest_data_rejects_invalid_schema(monkeypatch, tmp_path):
    """ingest_data should return 1 when CSV fails validation."""
    from scripts import ingest_data as ingest_mod

    root = ROOT
    raw_path = root / "data" / "raw" / "website_monitoring.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"bad_column": [1, 2]}).to_csv(raw_path, index=False)
    monkeypatch.setattr(
        sys, "argv", ["ingest_data.py", "--skip-blob", "--skip-dvc"]
    )
    assert ingest_mod.main() == 1


def test_upload_to_blob_mock(valid_monitoring_df, tmp_path):
    """upload_to_blob should call Azure SDK with mocked client."""
    from scripts.ingest_data import upload_to_blob

    csv_path = tmp_path / "test.csv"
    valid_monitoring_df.to_csv(csv_path, index=False)
    mock_blob_client = MagicMock()
    mock_service = MagicMock()
    mock_service.get_blob_client.return_value = mock_blob_client
    mock_service.account_name = "testaccount"
    with patch(
        "azure.storage.blob.BlobServiceClient.from_connection_string",
        return_value=mock_service,
    ):
        with patch(
            "scripts.ingest_data.get_storage_connection_string",
            return_value="DefaultEndpointsProtocol=https;AccountName=test;",
        ):
            url = upload_to_blob(csv_path, "datasets", "raw/test.csv")
    assert "datasets" in url
    mock_blob_client.upload_blob.assert_called_once()


def test_load_raw_data(valid_monitoring_df):
    """load_raw_data should return DataFrame with expected columns."""
    from src.data.load_data import load_raw_data

    root = ROOT
    raw_path = root / "data" / "raw" / "website_monitoring.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    valid_monitoring_df.to_csv(raw_path, index=False)
    df = load_raw_data(raw_path)
    assert len(df) == len(valid_monitoring_df)
    assert "outage_within_1h" in df.columns


def test_load_from_blob_mock(valid_monitoring_df):
    """load_from_blob should parse CSV bytes from mocked blob download."""
    from src.data.load_data import load_from_blob

    csv_bytes = valid_monitoring_df.to_csv(index=False).encode("utf-8")
    mock_download = MagicMock()
    mock_download.readall.return_value = csv_bytes
    mock_blob_client = MagicMock()
    mock_blob_client.download_blob.return_value = mock_download
    mock_service = MagicMock()
    mock_service.get_blob_client.return_value = mock_blob_client
    with patch(
        "azure.storage.blob.BlobServiceClient.from_connection_string",
        return_value=mock_service,
    ):
        df = load_from_blob("conn", "datasets", "raw/website_monitoring.csv")
    assert len(df) == len(valid_monitoring_df)


def test_load_data_config():
    """data_config.yaml should load with required keys."""
    from scripts.ingest_data import load_data_config

    cfg = load_data_config()
    assert cfg["raw_filename"] == "website_monitoring.csv"
    assert "blob_path" in cfg


def test_setup_dvc_init_already_exists(monkeypatch):
    """setup_dvc should skip init when .dvc already exists."""
    from scripts.setup_dvc import init_dvc

    root = ROOT
    (root / ".dvc").mkdir(exist_ok=True)
    assert init_dvc(root) is True
