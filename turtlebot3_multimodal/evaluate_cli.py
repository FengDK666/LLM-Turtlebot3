from __future__ import annotations

import argparse
from pathlib import Path

from turtlebot3_multimodal.evaluation import run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    for name, path in run_evaluation(args.output_dir).items():
        print(f"{name}: {path}")
