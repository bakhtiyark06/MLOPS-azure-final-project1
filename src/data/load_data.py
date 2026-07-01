# Author: Member A — data ingestion stage
# Purpose: Load raw website monitoring CSV data from local path or Azure Blob

"""Data loading utilities for website outage prediction dataset."""

from pathlib import Path  # Path handling for local CSV files
from typing import Optional  # Optional blob path parameter

import pandas as pd  # Tabular data loading and manipulation

from src.utils.config import get_project_root  # Project root for default paths


def get_default_raw_path() -> Path:
    """
    Return the default path to the raw monitoring CSV file.

    Returns:
        Path to data/raw/website_monitoring.csv
    """
    # Standard location for raw ingested data per project structure
    return get_project_root() / "data" / "raw" / "website_monitoring.csv"


def load_raw_data(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load the raw website monitoring dataset from a CSV file.

    Args:
        csv_path: Optional override path; defaults to data/raw/website_monitoring.csv.

    Returns:
        DataFrame with monitoring features and target column.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    # Use provided path or fall back to project default
    path = csv_path or get_default_raw_path()
    # Verify file exists before attempting read
    if not path.exists():
        raise FileNotFoundError(
            f"Raw data not found at {path}. Run scripts/generate_sample_data.py first."
        )
    # Read CSV into a pandas DataFrame with default inference
    df = pd.read_csv(path)
    # Return the loaded dataframe to callers (preprocess, feature build, etc.)
    return df


def load_from_blob(connection_string: str, container: str, blob_name: str) -> pd.DataFrame:
    """
    Download a CSV from Azure Blob Storage and load into a DataFrame.

    Args:
        connection_string: Azure Storage account connection string.
        container: Blob container name, e.g. 'datasets'.
        blob_name: Path/name of the blob object inside the container.

    Returns:
        DataFrame parsed from the downloaded CSV bytes.
    """
    # Import here to avoid requiring azure SDK for local-only tests
    from azure.storage.blob import BlobServiceClient  # Azure Blob SDK client

    # Create a client authenticated via the connection string
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    # Get a handle to the specific blob inside the container
    blob_client = blob_service.get_blob_client(container=container, blob=blob_name)
    # Download blob content as raw bytes
    download = blob_client.download_blob()
    # Wrap bytes in BytesIO so pandas read_csv accepts a file-like object
    import io

    buffer = io.BytesIO(download.readall())
    # Read CSV from in-memory buffer
    df = pd.read_csv(buffer)
    # Return dataframe for downstream preprocessing
    return df
