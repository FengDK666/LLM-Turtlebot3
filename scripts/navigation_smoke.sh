#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
set +u
. /opt/ros/humble/setup.bash
if [[ -f "${ROS_NAV_OVERLAY_SETUP:-/nonexistent}" ]]; then
    . "$ROS_NAV_OVERLAY_SETUP"
fi
. install/setup.bash
set -u

# Gazebo's Python utilities depend on Ubuntu's system site packages (for lxml).
# Put system Python ahead of an accidentally activated virtual environment.
export PATH="/opt/ros/humble/bin:/usr/bin:$PATH"
tb3_gazebo_share="$(ros2 pkg prefix --share turtlebot3_gazebo)"
export GAZEBO_MODEL_PATH="$tb3_gazebo_share/models:${GAZEBO_MODEL_PATH:-}"
export TURTLEBOT3_MODEL=waffle
export LIBGL_ALWAYS_SOFTWARE=1
output_dir="${1:-/tmp/turtlebot3-navigation}"
rm -rf "$output_dir"
timeout 140 ros2 launch turtlebot3_multimodal navigation_sim.launch.py output_dir:="$output_dir"
test -s "$output_dir/navigation_trajectory.csv"
test -s "$output_dir/navigation_metrics.csv"
test -s "$output_dir/navigation_trajectory.png"
test -s "$output_dir/slam_map.png"
test -s "$output_dir/slam_map.yaml"
grep -q '^status,succeeded$' <(awk -F, 'NR>1 {print $1 "," $2}' "$output_dir/navigation_metrics.csv")
grep -q '^goal_within_tolerance,True$' "$output_dir/navigation_metrics.csv"
