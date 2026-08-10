"""Validate data, train forecasting models, and train Isolation Forest."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str], root: Path) -> None:
    print(f"Running: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=root, check=False)
    if completed.returncode:
        raise SystemExit(
            f"Training pipeline stopped with exit code "
            f"{completed.returncode}: {' '.join(command)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("quick", "full"), default="quick")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    run([python, "scripts/validate_model_data.py"], root)
    run(
        [
            python,
            "models/training/train_forecasting_models.py",
            "--mode",
            args.mode,
        ],
        root,
    )
    run([python, "models/training/train_isolation_forest.py"], root)
    print("Training pipeline completed successfully.", flush=True)


if __name__ == "__main__":
    main()
