# Safe Multimodal TurtleBot3

## Project timeline and provenance

| Milestone | Date | Scope |
|---|---|---|
| Original course-project context | Nov 2024 | TurtleBot3/ROS 2 coursework covering robot commands, model setup, and sensor-data processing. |
| Independent safety-focused reconstruction and extension | Aug 2026 | Rebuilt and extended the public repository with a constrained command protocol, safety controls, tests, and software-only Gazebo/Nav2 validation. |

These dates distinguish the original coursework from the later public portfolio build; the GitHub repository update date refers to the independent reconstruction and extension.

A ROS 2 Humble command layer for TurtleBot3 that converts gesture, voice, LLM,
keyboard, or test inputs into a strict JSON motion protocol. This upgrade keeps
the original course-project history while replacing arbitrary Python execution,
blocking motion loops, and hard-coded network addresses.

> Current validation is software-only. Gazebo, SLAM Toolbox, and Nav2 are tested
> headlessly; this branch does not claim current TurtleBot3 hardware, camera,
> microphone, gesture model, speech API, or cloud-LLM tests.

## Phase 1 scope

- JSON command protocol shared by gesture, voice, LLM, keyboard, and tests.
- Whitelisted forward/backward/left/right/stop actions with distance and angle limits.
- Non-blocking velocity state machine, watchdog, latched emergency stop, and stop-on-exit.
- ROS 2 topics/services and configurable safety parameters.
- Offline square replay and adversarial-input rejection metrics.
- Python and ROS 2 Humble tests plus GitHub Actions.

## Quantitative offline result

| Metric | Result |
|---|---:|
| Adversarial/invalid payloads rejected | **6 / 6** |
| Maximum commanded linear speed | 0.22 m/s |
| Maximum commanded angular speed | 1.5 rad/s |
| 0.5 m square closure error | **6.0 mm** |
| Final commanded speed | **0.0 m/s** |

![Offline square replay](results/figures/offline_square_trajectory.png)

The square replay is a deterministic kinematic software evaluation, not a
physical odometry measurement. ROS 2 Humble integration was exercised with a
real node graph: a valid command produced 0.22 m/s on `/cmd_vel`, the emergency
stop service succeeded, and the next observed command was zero linear and
angular velocity.

## Phase 2 navigation simulation

The official TurtleBot3 Waffle Gazebo model now runs with online SLAM Toolbox
mapping and Nav2 `NavigateToPose`. A reproducible headless evaluation records
odometry, action outcome, path length, speed limits, recoveries, endpoint error,
and a trajectory plot under `results/navigation/`.

```bash
scripts/navigation_smoke.sh results/navigation
```

See [the navigation evaluation](docs/navigation.md) for dependencies, launch
arguments, interpretation, and limitations.

| Representative headless run | Result |
|---|---:|
| Nav2 action outcome | **Succeeded** |
| Navigation + settling duration | 8.17 s |
| Odometry path length | 0.564 m |
| Final position error | **0.237 m** (inside 0.25 m tolerance) |
| Final linear speed | **0.00005 m/s** |
| SLAM map | 111 x 102 cells at 0.05 m/cell |
| Nav2 recoveries | 1 |

![Gazebo navigation trajectory](results/navigation/navigation_trajectory.png)

The table is one measured software-simulation run; small scheduling-dependent
variation is expected. Raw odometry, metrics, the occupancy map, and the figure
are committed under `results/navigation/`.

## Architecture

```mermaid
flowchart LR
    A[Gesture / Voice / LLM / Keyboard] --> B[Strict JSON parser]
    B --> C[Whitelist and numeric limits]
    C --> D[Non-blocking MotionExecutor]
    D --> E[ROS 2 /cmd_vel]
    G[Gazebo / SLAM Toolbox / Nav2] --> E
    F[Watchdog / emergency-stop service] --> D
```

## Command example

```json
{"source":"llm","commands":[{"action":"forward","value":0.5},{"action":"left","value":90},{"action":"stop"}]}
```

## Python verification

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
scripts/verify_python.sh
```

## ROS 2 Humble

```bash
scripts/verify_ros2.sh
source install/setup.bash
ros2 launch turtlebot3_multimodal safe_controller.launch.py
```

Publish a structured stop command or use the latched emergency-stop service:

```bash
ros2 topic pub --once /turtlebot3/command std_msgs/msg/String \
  "{data: '{\"source\":\"keyboard\",\"commands\":[{\"action\":\"stop\"}]}' }"
ros2 service call /turtlebot3/emergency_stop std_srvs/srv/Trigger
```

See [the safety model](docs/safety.md) and [legacy migration](docs/migration.md)
before using a physical robot.

## Current limits

- No current TurtleBot3 hardware or actuator validation.
- Gazebo, SLAM, Nav2, and obstacle avoidance are synthetic simulation only.
- Navigation results can vary slightly with simulator and executor scheduling.
- No camera, microphone, gesture model, speech API, or cloud LLM integration yet.
- Open-loop duration commands do not compensate for wheel slip or odometry error.
- The software protections are not a certified safety system.

## Original contributors

The initial course prototype was created by [@pgq18](https://github.com/pgq18)
and [@FengDK666](https://github.com/FengDK666). The repository history preserves
that work and attribution.
