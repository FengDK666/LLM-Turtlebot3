# Architecture

The package separates untrusted perception/model output from motion execution.
Adapters may recognize gestures, transcribe speech, or call an LLM, but their
only accepted output is the JSON command protocol in `commands.py`. The parser
has no code-evaluation path and owns all structural and numeric validation.

`MotionExecutor` is ROS-independent. It converts bounded distance or angle
commands to constant-velocity durations and advances through a timer-driven
state machine. It emits a simple linear/angular velocity record that can be
unit-tested without ROS. A watchdog gap or backward clock transition clears the
queue and latches emergency stop.

`SafeCommandNode` is a thin ROS 2 adapter. It accepts validated JSON on
`/turtlebot3/command`, publishes `geometry_msgs/Twist` on `/cmd_vel`, and exposes
Trigger services for emergency stop and reset. Safety limits come from ROS
parameters rather than source constants.

The offline evaluation runs the exact parser and executor used by the ROS node.
It records a kinematic trajectory, speed bounds, terminal stop state, and
rejection of representative code-injection and schema attacks.
