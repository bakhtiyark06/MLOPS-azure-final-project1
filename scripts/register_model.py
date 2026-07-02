# Author: Member B — model registry script
# Purpose: Register approved model in Azure ML Model Registry

"""CLI entrypoint for Stage 04 — Azure ML Model Registry registration."""

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.models.evaluate import get_default_eval_paths
from src.models.registry import (
    SKIP_MESSAGE,
    QualityGateError,
    load_dataset_hash,
    register_model,
)


def main() -> int:
    """Register model in Azure ML if quality gate passed."""
    parser = argparse.ArgumentParser(description="Register model in Azure ML Registry")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate gate and tags without calling Azure ML API",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Optional override for model joblib path",
    )
    parser.add_argument(
        "--eval-metrics-path",
        type=Path,
        default=None,
        help="Optional override for eval_metrics.json path",
    )
    args = parser.parse_args()

    model_path, _, default_eval_path = get_default_eval_paths()
    if args.model_path:
        model_path = args.model_path
    eval_metrics_path = args.eval_metrics_path or default_eval_path

    try:
        dataset_hash = load_dataset_hash()
        result = register_model(
            model_path=model_path,
            eval_metrics_path=eval_metrics_path,
            dataset_hash=dataset_hash,
            dry_run=args.dry_run,
        )
    except QualityGateError as exc:
        print(f"Registration blocked: {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    except EnvironmentError as exc:
        print(f"Azure configuration error: {exc}")
        return 1

    if result.get("skipped"):
        print(SKIP_MESSAGE)
        missing = result.get("missing_env_vars") or []
        if missing:
            print(f"Missing environment variables: {', '.join(missing)}")
        return 0

    if args.dry_run:
        print("Dry run complete")
        print(f"  Model name:    {result['model_name']}")
        print(f"  Dataset hash:  {result['tags']['dataset_hash']}")
        print(f"  Accuracy:      {result['tags']['accuracy']}")
        print(f"  F1 macro:      {result['tags']['f1_macro']}")
        print(f"  {result['message']}")
        return 0

    print("Model registration successful")
    print(f"  Model name:    {result['model_name']}")
    print(f"  Dataset hash:  {result['tags']['dataset_hash']}")
    print(f"  Accuracy:      {result['tags']['accuracy']}")
    print(f"  F1 macro:      {result['tags']['f1_macro']}")
    if "version" in result:
        print(f"  Version:       {result['version']}")
        print(f"  ARM ID:        {result['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
