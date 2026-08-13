"""Strict command protocol shared by gesture, voice, LLM, and ROS adapters."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

ACTIONS = {"forward", "backward", "left", "right", "stop"}
SOURCES = {"gesture", "voice", "llm", "keyboard", "test"}


class CommandValidationError(ValueError):
    """Raised when untrusted input violates the motion command protocol."""


@dataclass(frozen=True)
class SafetyLimits:
    max_distance_m: float = 2.0
    max_angle_deg: float = 360.0
    max_linear_mps: float = 0.22
    max_angular_rps: float = 1.5
    max_commands: int = 16
    watchdog_timeout_s: float = 0.5


@dataclass(frozen=True)
class MotionCommand:
    action: str
    value: float = 0.0


@dataclass(frozen=True)
class CommandPlan:
    source: str
    commands: tuple[MotionCommand, ...]


def _require_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CommandValidationError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise CommandValidationError(f"{field} must be finite")
    return result


def parse_command_payload(payload: str | bytes | dict, limits: SafetyLimits | None = None) -> CommandPlan:
    """Parse JSON-compatible untrusted input without evaluating source code."""
    limits = limits or SafetyLimits()
    if isinstance(payload, (str, bytes)):
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CommandValidationError("payload must be valid JSON") from error
    elif isinstance(payload, dict):
        data = payload
    else:
        raise CommandValidationError("payload must be JSON text or an object")
    if set(data) != {"source", "commands"}:
        raise CommandValidationError("payload fields must be exactly source and commands")
    source = data["source"]
    if source not in SOURCES:
        raise CommandValidationError(f"unsupported source: {source!r}")
    raw_commands = data["commands"]
    if not isinstance(raw_commands, list) or not raw_commands:
        raise CommandValidationError("commands must be a non-empty list")
    if len(raw_commands) > limits.max_commands:
        raise CommandValidationError("command sequence exceeds configured maximum")
    commands = []
    for index, raw in enumerate(raw_commands):
        if not isinstance(raw, dict) or "action" not in raw:
            raise CommandValidationError(f"commands[{index}] must contain action")
        action = raw["action"]
        if action not in ACTIONS:
            raise CommandValidationError(f"unsupported action: {action!r}")
        expected_fields = {"action"} if action == "stop" else {"action", "value"}
        if set(raw) != expected_fields:
            raise CommandValidationError(
                f"commands[{index}] fields do not match action {action!r}"
            )
        if action == "stop":
            commands.append(MotionCommand("stop"))
            continue
        value = _require_number(raw["value"], f"commands[{index}].value")
        if value <= 0:
            raise CommandValidationError("motion values must be positive")
        maximum = limits.max_distance_m if action in {"forward", "backward"} else limits.max_angle_deg
        if value > maximum:
            unit = "m" if action in {"forward", "backward"} else "deg"
            raise CommandValidationError(f"{action} exceeds {maximum:g} {unit}")
        commands.append(MotionCommand(action, value))
    return CommandPlan(source, tuple(commands))


def command_payload(source: str, commands: list[dict]) -> str:
    """Serialize adapter output through the same validator used by the robot."""
    plan = parse_command_payload({"source": source, "commands": commands})
    return json.dumps(
        {
            "source": plan.source,
            "commands": [
                {"action": command.action, **({"value": command.value} if command.action != "stop" else {})}
                for command in plan.commands
            ],
        },
        separators=(",", ":"),
    )
