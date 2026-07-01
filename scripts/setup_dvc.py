# Author: Member A — DVC setup script
# Purpose: Initialize DVC and configure Azure Blob remote (no manual shell steps)

"""Initialize DVC and configure Azure Blob Storage as the default remote."""

import argparse  # CLI flags
import subprocess  # Run dvc CLI from Python per project rules
import sys  # Exit codes
from pathlib import Path  # Project root paths

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils.config import get_project_root, load_azure_config
from src.utils.secrets import get_env_optional


def _dvc_cmd(*args: str) -> list:
    """
    Build DVC command argv using the current Python interpreter.

    Using `python -m dvc` works when the `dvc` executable is not on PATH (Windows).

    Returns:
        Command list for subprocess.run.
    """
    # sys.executable is the venv Python running this script
    return [sys.executable, "-m", "dvc", *args]


def run_command(cmd: list, cwd: Path) -> subprocess.CompletedProcess:
    """
    Run a subprocess command and return the result.

    Args:
        cmd: Command argv list, e.g. ['dvc', 'init'].
        cwd: Working directory for the command.

    Returns:
        CompletedProcess with returncode and stdout/stderr.
    """
    # Execute command with captured output for error messages
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def init_dvc(root: Path) -> bool:
    """
    Run `dvc init` if .dvc directory does not exist.

    Args:
        root: Project root directory.

    Returns:
        True if DVC is initialized (or was already), False on failure.
    """
    # Skip init if already done
    if (root / ".dvc").exists():
        print("DVC already initialized")
        return True
    # Create new DVC project metadata in .dvc/
    result = run_command(_dvc_cmd("init"), root)
    if result.returncode != 0:
        print(f"dvc init failed: {result.stderr}")
        return False
    print("DVC initialized successfully")
    return True


def configure_azure_remote(root: Path, connection_string: str = None) -> bool:
    """
    Add or update Azure Blob as the default DVC remote.

    Args:
        root: Project root directory.
        connection_string: Optional Azure Storage connection string.

    Returns:
        True if remote configured, False otherwise.
    """
    # Load container name from azure_config.yaml
    azure_cfg = load_azure_config()
    container = azure_cfg.get("blob_container", "datasets")
    remote_name = "azureblob"
    # DVC Azure URL format: azure://container/path-prefix
    remote_url = f"azure://{container}/dvc-storage"
    # Add remote (ignore error if it already exists)
    run_command(_dvc_cmd("remote", "add", remote_name, remote_url), root)
    # Set as default remote for push/pull
    result = run_command(_dvc_cmd("remote", "default", remote_name), root)
    if result.returncode != 0:
        print(f"dvc remote default failed: {result.stderr}")
    # Configure connection string on remote if provided via env
    conn = connection_string or get_env_optional("AZURE_STORAGE_CONNECTION_STRING")
    if conn:
        run_command(
            _dvc_cmd(
                "remote",
                "modify",
                remote_name,
                "connection_string",
                conn,
            ),
            root,
        )
        print(f"DVC remote '{remote_name}' configured with Azure connection string")
    else:
        print(
            "AZURE_STORAGE_CONNECTION_STRING not set; "
            "configure later with: dvc remote modify azureblob connection_string <secret>"
        )
    return True


def main() -> int:
    """
    CLI entrypoint: dvc init + Azure remote setup.

    Returns:
        0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(description="Initialize DVC with Azure Blob remote")
    parser.add_argument(
        "--skip-remote",
        action="store_true",
        help="Only run dvc init, skip remote configuration",
    )
    args = parser.parse_args()
    root = get_project_root()
    # Step 1: Initialize DVC
    if not init_dvc(root):
        return 1
    # Step 2: Configure Azure Blob remote unless skipped
    if not args.skip_remote:
        configure_azure_remote(root)
    print("DVC setup complete. Next: py scripts/generate_sample_data.py && py scripts/ingest_data.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
