# Author: Member B — evaluation script
# Purpose: Evaluate model and enforce quality gate

"""CLI entrypoint for Stage 03 — model evaluation and quality gate."""

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.models.evaluate import (
    compute_metrics,
    get_default_eval_paths,
    load_model_and_test_set,
    run_quality_gate,
    write_eval_metrics,
)
from src.utils.config import load_model_config


def main() -> int:
    """Evaluate holdout set and enforce quality gate thresholds."""
    parser = argparse.ArgumentParser(description="Evaluate model and run quality gate")
    parser.add_argument(
        "--force-fail",
        action="store_true",
        help="Demo mode: simulate gate failure to show deploy blocking",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Optional override for model joblib path",
    )
    parser.add_argument(
        "--test-set-path",
        type=Path,
        default=None,
        help="Optional override for test set CSV path",
    )
    args = parser.parse_args()

    default_model, default_test, eval_metrics_path = get_default_eval_paths()
    model_path = args.model_path or default_model
    test_set_path = args.test_set_path or default_test

    config = load_model_config()
    model, X_test, y_test = load_model_and_test_set(model_path, test_set_path)
    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred)

    print("Holdout evaluation metrics:")
    print(f"  F1 score:  {metrics['f1_score']:.4f}")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Thresholds: F1 >= {config['quality_gate']['min_f1_score']}, "
          f"accuracy >= {config['quality_gate']['min_accuracy']}")

    if args.force_fail:
        print("\nQUALITY GATE FAILED (--force-fail demo)")
        print("Bad models cannot proceed to registry or deployment.")
        write_eval_metrics(
            eval_metrics_path,
            metrics,
            gate_passed=False,
            gate_reasons=["--force-fail demo flag set"],
            force_fail=True,
        )
        print(f"  Wrote {eval_metrics_path} with gate_passed=false")
        return 1

    passed, reasons = run_quality_gate(metrics, config)
    write_eval_metrics(eval_metrics_path, metrics, gate_passed=passed, gate_reasons=reasons)

    if passed:
        print("\nQUALITY GATE PASSED")
        print(f"  Wrote {eval_metrics_path}")
        return 0

    print("\nQUALITY GATE FAILED")
    for reason in reasons:
        print(f"  - {reason}")
    print("Bad models cannot proceed to registry or deployment.")
    print(f"  Wrote {eval_metrics_path} with gate_passed=false")
    return 1


if __name__ == "__main__":
    sys.exit(main())
