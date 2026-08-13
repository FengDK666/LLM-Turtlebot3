#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
set +u
. /opt/ros/humble/setup.bash
. install/setup.bash
set -u

setsid ros2 run turtlebot3_multimodal safe_controller --ros-args \
    --params-file config/safety.yaml > /tmp/turtlebot3-safe-node.log 2>&1 &
node_pid=$!
trap 'kill -- -"$node_pid" 2>/dev/null || true; wait "$node_pid" 2>/dev/null || true' EXIT

for _ in {1..30}; do
    if ros2 node list 2>/dev/null | grep --quiet safe_multimodal_controller; then
        break
    fi
    sleep 0.2
done
ros2 node list | grep --quiet safe_multimodal_controller
ros2 topic list | grep --quiet '^/turtlebot3/command$'
ros2 service list | grep --quiet '^/turtlebot3/emergency_stop$'

ros2 topic pub --once /turtlebot3/command std_msgs/msg/String \
    "{data: '{\"source\":\"test\",\"commands\":[{\"action\":\"forward\",\"value\":1.0}]}' }" \
    > /tmp/turtlebot3-command-pub.log
timeout 2 ros2 topic echo --once /cmd_vel > /tmp/turtlebot3-moving-twist.txt
grep --quiet 'x: 0.22' /tmp/turtlebot3-moving-twist.txt

ros2 service call /turtlebot3/emergency_stop std_srvs/srv/Trigger \
    > /tmp/turtlebot3-estop.txt
grep --quiet 'success=True' /tmp/turtlebot3-estop.txt
timeout 2 ros2 topic echo --once /cmd_vel > /tmp/turtlebot3-stopped-twist.txt
grep --quiet 'x: 0.0' /tmp/turtlebot3-stopped-twist.txt
grep --quiet 'z: 0.0' /tmp/turtlebot3-stopped-twist.txt

printf 'moving twist:\n'
cat /tmp/turtlebot3-moving-twist.txt
printf 'emergency stop:\n'
cat /tmp/turtlebot3-estop.txt
printf 'stopped twist:\n'
cat /tmp/turtlebot3-stopped-twist.txt
