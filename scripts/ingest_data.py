# Author: Member A — data ingestion script
# Purpose: Upload dataset to Azure Blob Storage and track with DVC

"""Ingest website monitoring data to Azure Blob Storage with DVC versioning."""

import argparse  # CLI arguments
import hashlib  # Dataset hash for model registry tags
import json  # Ingestion metadata artifact
import subprocess  # Run dvc commands from Python
import sys  # Exit codes
from datetime import datetime, timezone  # UTC timestamp for metadata
from pathlib import Path  # File paths

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.validate_data import validate_raw_csv_path  # Schema validation before upload
from src.utils.config import get_project_root, load_azure_config, load_yaml_config
from src.utils.secrets import get_env_optional, get_storage_connection_string


def _dvc_cmd(*args: str) -> list:
    """Build DVC argv via `python -m dvc` for Windows compatibility."""
    return [sys.executable, "-m", "dvc", *args]


def load_data_config() -> dict:
    """
    Load data pipeline settings from configs/data_config.yaml.

    Returns:
        Dict with blob paths, filenames, and metadata settings.
    """
    # Delegate to shared YAML loader with data config filename
    return load_yaml_config("data_config.yaml")


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of a file for dataset versioning metadata.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hex digest string of SHA256 hash.
    """
    # SHA256 hasher instance
    hasher = hashlib.sha256()
    # Read file in chunks to handle large CSVs without loading all into memory
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    # Return hex string for tagging in Model Registry
    return hasher.hexdigest()


def upload_to_blob(local_path: Path, container: str, blob_name: str) -> str:
    """
    Upload a local file to Azure Blob Storage.

    Args:
        local_path: Path to local CSV file.
        container: Blob container name from azure_config.yaml.
        blob_name: Destination blob path inside the container.

    Returns:
        Blob URL string for logging and metadata.

    Raises:
        EnvironmentError: If storage connection string is not set.
    """
    # Import Azure Blob SDK
    from azure.storage.blob import BlobServiceClient

    # Get connection string from environment (never hardcoded)
    conn_str = get_storage_connection_string()
    # Create authenticated blob service client
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    # Get client for target blob
    blob_client = blob_service.get_blob_client(container=container, blob=blob_name)
    # Upload local file, overwriting existing blob with same name
    with open(local_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    # Build blob URI for metadata and logs
    blob_url = f"https://{blob_service.account_name}.blob.core.windows.net/{container}/{blob_name}"
    print(f"Uploaded {local_path} -> blob://{container}/{blob_name}")
    return blob_url


def run_dvc_track(file_path: Path) -> bool:
    """
    Track a data file with DVC (`dvc add`) and push to configured remote.

    Args:
        file_path: Path to CSV file relative to project root.

    Returns:
        True if DVC tracking succeeded, False otherwise.
    """
    # Project root for subprocess cwd
    root = get_project_root()
    # Check if .dvc directory exists (setup_dvc.py was run)
    if not (root / ".dvc").exists():
        print("DVC not initialized. Run: py scripts/setup_dvc.py")
        return False
    try:
        # dvc add creates .dvc pointer file and updates .gitignore
        add_result = subprocess.run(
            _dvc_cmd("add", str(file_path)),
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"DVC tracked: {file_path}")
        # Push to Azure remote when connection string is configured
        if get_env_optional("AZURE_STORAGE_CONNECTION_STRING"):
            push_result = subprocess.run(
                _dvc_cmd("push", str(file_path)),
                cwd=str(root),
                capture_output=True,
                text=True,
            )
            if push_result.returncode == 0:
                print("DVC push to Azure remote succeeded")
            else:
                print(f"DVC push skipped or failed: {push_result.stderr}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        # Non-fatal in CI if DVC remote not configured yet
        print(f"DVC track failed: {exc}")
        return False


def write_ingestion_metadata(
    metadata_path: Path,
    dataset_hash: str,
    row_count: int,
    blob_url: str = None,
    dvc_tracked: bool = False,
) -> None:
    """
    Write JSON metadata file documenting this ingestion run.

    Args:
        metadata_path: Path to ingestion_metadata.json.
        dataset_hash: SHA256 hash of the raw CSV.
        row_count: Number of rows ingested.
        blob_url: Optional Azure Blob URL after upload.
        dvc_tracked: Whether DVC add/push succeeded.
    """
    # Build metadata record for audit trail and model registry tags
    metadata = {
        "dataset_hash": dataset_hash,
        "row_count": row_count,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        "blob_url": blob_url,
        "dvc_tracked": dvc_tracked,
        "stage": "01-data-ingestion",
        "owner": "Member A",
    }
    # Ensure parent directory exists
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    # Write pretty-printed JSON for human review in PRs
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Ingestion metadata -> {metadata_path}")


def main() -> int:
    """
    CLI: validate, upload raw CSV to Azure Blob, DVC-track, write metadata.

    Returns:
        0 on success, 1 on missing/invalid data file.
    """
    parser = argparse.ArgumentParser(description="Ingest data to Azure Blob + DVC")
    parser.add_argument(
        "--skip-blob",
        action="store_true",
        help="Skip Azure upload (local-only mode)",
    )
    parser.add_argument(
        "--skip-dvc",
        action="store_true",
        help="Skip DVC tracking",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Override path to raw CSV",
    )
    args = parser.parse_args()
    # Load data pipeline config
    data_cfg = load_data_config()
    root = get_project_root()
    # Resolve raw CSV path from arg or config default
    data_path = (
        Path(args.data_path)
        if args.data_path
        else root / "data" / "raw" / data_cfg["raw_filename"]
    )
    # Fail fast if CSV missing
    if not data_path.exists():
        print(f"Data not found: {data_path}. Run: py scripts/generate_sample_data.py")
        return 1
    # Validate schema before ingestion (quality gate for data)
    is_valid, errors = validate_raw_csv_path(data_path)
    if not is_valid:
        print("Data validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Data validation passed")
    # Compute hash for logging and model registry tags
    dataset_hash = compute_file_hash(data_path)
    print(f"Dataset SHA256: {dataset_hash}")
    # Write hash file for DVC pipeline downstream stages
    hash_path = root / "data" / "raw" / "dataset_hash.txt"
    hash_path.write_text(dataset_hash, encoding="utf-8")
    # Count rows for metadata (read without loading full file into memory twice)
    import pandas as pd

    row_count = len(pd.read_csv(data_path))
    blob_url = None
    # Upload to Azure unless skipped or no connection string
    if not args.skip_blob:
        if get_env_optional("AZURE_STORAGE_CONNECTION_STRING"):
            azure_cfg = load_azure_config() or {}
            container = azure_cfg.get("blob_container", "datasets")
            blob_name = data_cfg.get("blob_path", "raw/website_monitoring.csv")
            blob_url = upload_to_blob(data_path, container, blob_name)
        else:
            print("AZURE_STORAGE_CONNECTION_STRING not set; skipping blob upload")
    # DVC track unless skipped
    dvc_ok = False
    if not args.skip_dvc:
        dvc_ok = run_dvc_track(data_path)
    # Write ingestion metadata JSON artifact
    meta_path = root / data_cfg.get("ingestion_metadata_file", "data/raw/ingestion_metadata.json")
    write_ingestion_metadata(meta_path, dataset_hash, row_count, blob_url, dvc_ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
