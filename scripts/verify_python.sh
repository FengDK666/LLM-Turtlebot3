#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ -f .venv/bin/activate ]]; then
    . .venv/bin/activate
fi
ruff check .
pytest -q
turtlebot-command-evaluation --output-dir /tmp/turtlebot3-command-evaluation
