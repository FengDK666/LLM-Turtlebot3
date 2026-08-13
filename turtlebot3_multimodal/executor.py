"""Non-blocking, bounded motion state machine independent of ROS."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from turtlebot3_multimodal.commands import CommandPlan, MotionCommand, SafetyLimits


@dataclass(frozen=True)
class Velocity:
    linear_x: float = 0.0
    angular_z: float = 0.0


class MotionExecutor:
    def __init__(self, limits: SafetyLimits | None = None):
        self.limits = limits or SafetyLimits()
        self._queue: deque[MotionCommand] = deque()
        self._active: MotionCommand | None = None
        self._active_until = 0.0
        self._last_tick: float | None = None
        self._emergency_stopped = False
        self.completed_commands = 0

    @property
    def emergency_stopped(self) -> bool:
        return self._emergency_stopped

    @property
    def idle(self) -> bool:
        return not self._queue and self._active is None

    def submit(self, plan: CommandPlan) -> None:
        if self._emergency_stopped:
            raise RuntimeError("executor is emergency-stopped")
        self._queue.extend(plan.commands)

    def emergency_stop(self) -> Velocity:
        self._emergency_stopped = True
        self._queue.clear()
        self._active = None
        return Velocity()

    def reset_emergency_stop(self) -> None:
        self._emergency_stopped = False
        self._last_tick = None

    def _duration(self, command: MotionCommand) -> float:
        if command.action in {"forward", "backward"}:
            return command.value / self.limits.max_linear_mps
        if command.action in {"left", "right"}:
            return math.radians(command.value) / self.limits.max_angular_rps
        return 0.0

    def _velocity(self, command: MotionCommand | None) -> Velocity:
        if command is None or command.action == "stop":
            return Velocity()
        if command.action == "forward":
            return Velocity(linear_x=self.limits.max_linear_mps)
        if command.action == "backward":
            return Velocity(linear_x=-self.limits.max_linear_mps)
        if command.action == "left":
            return Velocity(angular_z=self.limits.max_angular_rps)
        return Velocity(angular_z=-self.limits.max_angular_rps)

    def tick(self, now_s: float) -> Velocity:
        if not math.isfinite(now_s):
            raise ValueError("clock must be finite")
        if self._last_tick is not None and now_s < self._last_tick:
            return self.emergency_stop()
        if (
            self._last_tick is not None
            and now_s - self._last_tick > self.limits.watchdog_timeout_s
            and not self.idle
        ):
            return self.emergency_stop()
        self._last_tick = now_s
        if self._emergency_stopped:
            return Velocity()
        if self._active is not None and now_s >= self._active_until:
            self._active = None
            self.completed_commands += 1
        while self._active is None and self._queue:
            command = self._queue.popleft()
            if command.action == "stop":
                self._queue.clear()
                self.completed_commands += 1
                return Velocity()
            self._active = command
            self._active_until = now_s + self._duration(command)
        return self._velocity(self._active)
