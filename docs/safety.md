# Command safety model

The legacy prototype published Python fragments and executed incoming ROS text
with `exec`. The upgraded path never evaluates source code. All gesture, voice,
or LLM adapters must emit a JSON object with a declared source and a non-empty
list of whitelisted actions.

The parser rejects unknown fields, unknown sources, unsupported actions,
non-finite values, negative values, oversized distances or angles, and sequences
longer than 16 commands. The motion executor applies configured maximum linear
and angular speeds, runs as a timer-driven state machine, publishes zero velocity
after every sequence, and latches an emergency stop after clock regression or a
watchdog gap while moving.

This reduces software risk but is not a certified safety controller. A real
robot still requires physical emergency stop access, obstacle avoidance, safe
operating space, validated odometry, and an operator ready to intervene.
