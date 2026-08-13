#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
set +u
. /opt/ros/humble/setup.bash
set -u
rm -rf build install log
colcon build --symlink-install
colcon test
colcon test-result --verbose
scripts/ros_smoke.sh
