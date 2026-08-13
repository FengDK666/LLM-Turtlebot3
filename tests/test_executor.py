from turtlebot3_multimodal.commands import parse_command_payload
from turtlebot3_multimodal.executor import MotionExecutor, Velocity


def test_executor_is_bounded_and_non_blocking() -> None:
    executor = MotionExecutor()
    executor.submit(
        parse_command_payload(
            {"source": "test", "commands": [{"action": "forward", "value": 0.22}, {"action": "stop"}]}
        )
    )
    assert executor.tick(0.0) == Velocity(linear_x=0.22)
    assert executor.tick(0.5) == Velocity(linear_x=0.22)
    assert executor.tick(1.0) == Velocity()
    assert executor.idle


def test_watchdog_latches_emergency_stop() -> None:
    executor = MotionExecutor()
    executor.submit(
        parse_command_payload(
            {"source": "test", "commands": [{"action": "forward", "value": 1.0}]}
        )
    )
    assert executor.tick(0.0).linear_x > 0
    assert executor.tick(0.6) == Velocity()
    assert executor.emergency_stopped


def test_clock_regression_and_manual_stop_are_safe() -> None:
    executor = MotionExecutor()
    executor.submit(
        parse_command_payload(
            {"source": "test", "commands": [{"action": "left", "value": 90}]}
        )
    )
    executor.tick(2.0)
    assert executor.tick(1.0) == Velocity()
    executor.reset_emergency_stop()
    assert executor.emergency_stop() == Velocity()
