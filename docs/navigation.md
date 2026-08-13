# Gazebo, SLAM Toolbox, and Nav2 evaluation

Phase 2 runs the official TurtleBot3 Waffle model in Gazebo Classic, builds an
occupancy grid online with SLAM Toolbox, and sends a `NavigateToPose` goal to
Nav2. The evaluator subscribes to `/odom`, captures action feedback, and writes
the raw trajectory, action outcome, map geometry/coverage, PNG/YAML occupancy
map, summary metrics, and a trajectory figure. After Nav2 reports success, it
records two additional seconds so the endpoint speed reflects settling rather
than the success callback.

The goal is sent only after Nav2 is active, odometry is flowing, and SLAM has
expanded beyond its initial placeholder grid (at least 50 x 50 cells and 200
known cells). This prevents the target being submitted off the global costmap
on slower CI runners.

## Dependencies

On Ubuntu 22.04 with ROS 2 Humble:

```bash
sudo apt update
sudo apt install \
  ros-humble-turtlebot3-gazebo \
  ros-humble-turtlebot3-navigation2 \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox
```

## Reproduce

```bash
scripts/verify_ros2.sh
scripts/navigation_smoke.sh results/navigation
```

The default run starts at the pose configured by Nav2's TurtleBot3 simulation
and targets `(-1.2, -0.5)` in the `map` frame. Override `goal_x` and `goal_y`
through the launch file for another reachable pose. The test is headless and
sets software OpenGL rendering for compatibility with CI and remote hosts.

Results are odometry-based and can vary slightly with simulator scheduling.
Nav2's success status uses its configured goal tolerance; therefore the final
position does not need to equal the requested coordinate exactly. The default
evaluation records and draws the standard 0.25 m tolerance used by this launch.
